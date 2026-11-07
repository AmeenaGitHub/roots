import hmac
from functools import wraps

import cv2
import numpy as np

import io
import json
import qrcode

import os
import sqlite3
import uuid
from datetime import datetime, timezone

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, url_for, Response, send_file, session)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "roots.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

REUSE_OPTIONS = [
    "Free to reuse with credit",
    "Non-commercial reuse with credit",
    "Ask the creator before reuse",
    "Do not reuse",
]

FLAG_REASONS = [
    "Missing attribution",
    "Possible unauthorised reuse",
    "Incorrect or outdated information",
]

MATCH_MIN_INLIERS = 25  # higher = stricter matching

REVIEWER_PASSWORD = os.environ.get("REVIEWER_PASSWORD")

REQUIRED = ["title", "creator", "art_form", "region", "cultural_context",
            "source", "reuse_permission", "attribution_text"]
FIELDS = REQUIRED + ["year"]

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-key")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB uploads

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT UNIQUE,
    title TEXT NOT NULL,
    creator TEXT NOT NULL,
    art_form TEXT NOT NULL,
    region TEXT NOT NULL,
    year TEXT,
    cultural_context TEXT NOT NULL,
    source TEXT NOT NULL,
    reuse_permission TEXT NOT NULL,
    attribution_text TEXT NOT NULL,
    image_filename TEXT,
    image_hash TEXT,
    is_sample INTEGER NOT NULL DEFAULT 0,
    consent_confirmed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    note TEXT,
    created_at TEXT NOT NULL
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    columns = [row["name"] for row in db.execute("PRAGMA table_info(records)")]
    if "image_hash" not in columns:
        db.execute("ALTER TABLE records ADD COLUMN image_hash TEXT")
    if "status" not in columns:
        db.execute("ALTER TABLE records ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    if "removed_reason" not in columns:
        db.execute("ALTER TABLE records ADD COLUMN removed_reason TEXT")
    db.commit()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_record(db, data, image_filename=None, is_sample=False):
    cur = db.execute(
        """INSERT INTO records
           (title, creator, art_form, region, year, cultural_context, source,
            reuse_permission, attribution_text, image_filename, is_sample,
            consent_confirmed, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data["title"], data["creator"], data["art_form"], data["region"],
         data.get("year", ""), data["cultural_context"], data["source"],
         data["reuse_permission"], data["attribution_text"], image_filename,
         1 if is_sample else 0, 0 if is_sample else 1, now()),
    )
    record_id = f"RT-{cur.lastrowid:04d}"
    db.execute("UPDATE records SET record_id = ? WHERE id = ?",
               (record_id, cur.lastrowid))
    db.execute(
        "INSERT INTO audit_log (record_id, action, details, created_at) "
        "VALUES (?, ?, ?, ?)",
        (record_id, "created", "Record created", now()),
    )
    db.commit()
    return record_id


def save_image(file):
    if not file or not file.filename:
        return None
    ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Image must be a PNG, JPG or WEBP file.")
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    name = uuid.uuid4().hex + "." + ext
    file.save(os.path.join(UPLOAD_FOLDER, name))
    return name


_feature_cache = {}


def image_features(data):
    """Find distinctive points in an image. Returns None if unreadable."""
    array = np.frombuffer(data, dtype=np.uint8)
    gray = cv2.imdecode(array, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        return None
    height, width = gray.shape
    scale = 800 / max(height, width)
    if scale < 1:
        gray = cv2.resize(gray, (int(width * scale), int(height * scale)),
                          interpolation=cv2.INTER_AREA)
    keypoints, descriptors = cv2.SIFT_create(nfeatures=800).detectAndCompute(
        gray, None)
    if descriptors is None or len(keypoints) < 8:
        return None
    points = np.float32([k.pt for k in keypoints])
    return points, descriptors


def count_matches(first, second):
    """Count details that appear in both images in a consistent layout."""
    points1, desc1 = first
    points2, desc2 = second
    pairs = cv2.BFMatcher(cv2.NORM_L2).knnMatch(desc1, desc2, k=2)
    good = [p[0] for p in pairs
            if len(p) == 2 and p[0].distance < 0.75 * p[1].distance]
    if len(good) < 8:
        return 0
    src = points1[[m.queryIdx for m in good]].reshape(-1, 1, 2)
    dst = points2[[m.trainIdx for m in good]].reshape(-1, 1, 2)
    matrix, mask = cv2.estimateAffinePartial2D(
        src, dst, method=cv2.RANSAC, ransacReprojThreshold=5.0)
    return int(mask.sum()) if mask is not None else 0


def stored_features(filename):
    if filename not in _feature_cache:
        path = os.path.join(UPLOAD_FOLDER, filename)
        features = None
        if os.path.exists(path):
            with open(path, "rb") as f:
                features = image_features(f.read())
        _feature_cache[filename] = features
    return _feature_cache[filename]


def find_similar(db, data, min_inliers=MATCH_MIN_INLIERS):
    """Return catalogue records whose image looks like this image."""
    query = image_features(data)
    if query is None:
        return []
    matches = []
    rows = db.execute(
        "SELECT * FROM records WHERE image_filename IS NOT NULL "
        "AND status = 'active'").fetchall()
    for row in rows:
        features = stored_features(row["image_filename"])
        if features is None:
            continue
        inliers = count_matches(query, features)
        if inliers >= min_inliers:
            matches.append({
                "record": row,
                "inliers": inliers,
                "label": "Strong match" if inliers >= 100 else "Possible match",
            })
    matches.sort(key=lambda m: m["inliers"], reverse=True)
    return matches


@app.route("/")
def index():
    db = get_db()
    q = request.args.get("q", "").strip()
    art_form = request.args.get("art_form", "").strip()
    reuse = request.args.get("reuse", "").strip()

    sql = "SELECT * FROM records WHERE status = 'active'"
    params = []
    if q:
        sql += " AND (title LIKE ? OR creator LIKE ? OR record_id LIKE ?)"
        like = f"%{q}%"
        params += [like, like, like]
    if art_form:
        sql += " AND art_form = ?"
        params.append(art_form)
    if reuse:
        sql += " AND reuse_permission = ?"
        params.append(reuse)
    sql += " ORDER BY id DESC"

    records = db.execute(sql, params).fetchall()
    art_forms = [row["art_form"] for row in db.execute(
        "SELECT DISTINCT art_form FROM records WHERE status = 'active' "
        "ORDER BY art_form")]
    return render_template(
        "index.html", records=records, art_forms=art_forms,
        reuse_options=REUSE_OPTIONS, q=q, art_form=art_form, reuse=reuse)


@app.route("/new", methods=["GET", "POST"])
def new_record():
    form = {}
    if request.method == "POST":
        form = {key: request.form.get(key, "").strip() for key in FIELDS}
        if any(not form[k] for k in REQUIRED):
            flash("Please fill in all required fields.", "error")
        elif form["reuse_permission"] not in REUSE_OPTIONS:
            flash("Please choose a valid reuse permission.", "error")
        elif not request.form.get("consent"):
            flash("Please confirm you have the right to record this work.",
                  "error")
        else:
            try:
                image = save_image(request.files.get("image"))
            except ValueError as err:
                flash(str(err), "error")
            else:
                db = get_db()
                similar = []
                if image:
                    with open(os.path.join(UPLOAD_FOLDER, image), "rb") as f:
                        similar = find_similar(db, f.read())
                record_id = create_record(db, form, image)
                flash(f"Record {record_id} created.", "success")
                if similar:
                    for m in similar[:3]:
                        orig = m["record"]
                        db.execute(
                            "INSERT INTO audit_log (record_id, action, details, created_at) "
                            "VALUES (?, ?, ?, ?)",
                            (record_id, "similarity_notice",
                             f"At creation, the image was a {m['label'].lower()} "
                             f"for {orig['record_id']} (credited to "
                             f"{orig['creator']}).", now()))
                        db.execute(
                            "INSERT INTO audit_log (record_id, action, details, created_at) "
                            "VALUES (?, ?, ?, ?)",
                            (orig["record_id"], "similarity_notice",
                             f"A record with a similar image was added: "
                             f"{record_id} ({m['label'].lower()}).", now()))
                    db.commit()
                    top = similar[0]
                    flash(
                        f"Heads up: this image looks similar to "
                        f"{top['record']['record_id']} "
                        f"({top['record']['title']}, credited to "
                        f"{top['record']['creator']}). This has been noted on "
                        f"both records. It is only a hint, so please check "
                        f"that your record is accurate.", "info")
                return redirect(url_for("record_detail", record_id=record_id))
    return render_template("new.html", form=form, reuse_options=REUSE_OPTIONS)

def get_record_or_404(record_id):
    record = get_db().execute(
        "SELECT * FROM records WHERE record_id = ?", (record_id,)).fetchone()
    if record is None:
        abort(404)
    if record["status"] == "removed":
        abort(410)
    return record

@app.route("/record/<record_id>")
def record_detail(record_id):
    db = get_db()
    record = get_record_or_404(record_id)
    audit = db.execute(
        "SELECT * FROM audit_log WHERE record_id = ? ORDER BY id DESC",
        (record_id,)).fetchall()
    flag_count = db.execute(
        "SELECT COUNT(*) FROM flags WHERE record_id = ?",
        (record_id,)).fetchone()[0]
    return render_template("record.html", record=record, audit=audit,
                           flag_count=flag_count, flag_reasons=FLAG_REASONS)


@app.route("/credit/<record_id>")
def credit_page(record_id):
    record = get_record_or_404(record_id)
    return render_template("credit.html", record=record)


@app.route("/qr/<record_id>.png")
def qr_code(record_id):
    get_record_or_404(record_id)
    link = url_for("credit_page", record_id=record_id, _external=True)
    img = qrcode.make(link)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png")


@app.route("/record/<record_id>/download")
def download_record(record_id):
    record = get_record_or_404(record_id)
    data = {
        "roots_provenance_record": {
            "record_id": record["record_id"],
            "title": record["title"],
            "creator": record["creator"],
            "art_form": record["art_form"],
            "region": record["region"],
            "year": record["year"],
            "cultural_context": record["cultural_context"],
            "source": record["source"],
            "reuse_permission": record["reuse_permission"],
            "credit_line": record["attribution_text"],
            "demonstration_record": bool(record["is_sample"]),
            "created_at": record["created_at"],
            "credit_page": url_for("credit_page", record_id=record_id,
                                   _external=True),
        },
        "disclaimer": ("This file records the credit and permissions stated "
                       "by the person who created the record. It is not a "
                       "legal proof of ownership."),
    }
    body = json.dumps(data, indent=2, ensure_ascii=False)
    return Response(
        body, mimetype="application/json",
        headers={"Content-Disposition":
                 f'attachment; filename="{record_id}-provenance.json"'})

@app.route("/record/<record_id>/flag", methods=["POST"])
def flag_record(record_id):
    get_record_or_404(record_id)
    reason = request.form.get("reason", "").strip()
    note = request.form.get("note", "").strip()[:500]
    if reason not in FLAG_REASONS:
        flash("Please choose a reason for the flag.", "error")
    elif not note:
        flash("Please say where you saw the work or what is wrong.", "error")
    else:
        db = get_db()
        db.execute(
            "INSERT INTO flags (record_id, reason, note, created_at) "
            "VALUES (?, ?, ?, ?)", (record_id, reason, note, now()))
        db.execute(
            "INSERT INTO audit_log (record_id, action, details, created_at) "
            "VALUES (?, ?, ?, ?)",
            (record_id, "flagged", f"Flag submitted: {reason}", now()))
        db.commit()
        flash("Thank you. Your flag has been recorded for review.", "success")
    return redirect(url_for("record_detail", record_id=record_id) + "#flag")

@app.route("/check", methods=["GET", "POST"])
def check_image():
    matches = None
    closest = None
    if request.method == "POST":
        file = request.files.get("image")
        if not file or not file.filename:
            flash("Please choose an image to check.", "error")
        else:
            ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
            if ext not in ALLOWED_EXTENSIONS:
                flash("Image must be a PNG, JPG or WEBP file.", "error")
            else:
                data = file.read()
                if image_features(data) is None:
                    flash("That file could not be read as an image with "
                          "enough detail to compare.", "error")
                else:
                    db = get_db()
                    matches = find_similar(db, data)
                    if not matches and app.debug:
                        nearest = find_similar(db, data, min_inliers=0)
                        closest = nearest[0] if nearest else None
    return render_template("check.html", matches=matches, closest=closest,
                           min_inliers=MATCH_MIN_INLIERS)


@app.errorhandler(410)
def record_removed(error):
    return render_template("removed.html"), 410


@app.context_processor
def inject_reviewer():
    return {"is_reviewer": bool(session.get("reviewer"))}


def reviewer_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("reviewer"):
            return redirect(url_for("reviewer_login"))
        return view(*args, **kwargs)
    return wrapped


@app.route("/reviewer/login", methods=["GET", "POST"])
def reviewer_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if REVIEWER_PASSWORD and hmac.compare_digest(
                password.encode(), REVIEWER_PASSWORD.encode()):
            session["reviewer"] = True
            return redirect(url_for("reviewer_dashboard"))
        flash("Incorrect password, or reviewer access is not set up.", "error")
    return render_template("reviewer_login.html")


@app.route("/reviewer/logout")
def reviewer_logout():
    session.pop("reviewer", None)
    return redirect(url_for("index"))


@app.route("/reviewer")
@reviewer_required
def reviewer_dashboard():
    db = get_db()
    records = db.execute(
        "SELECT r.*, (SELECT COUNT(*) FROM flags f "
        "WHERE f.record_id = r.record_id) AS flag_count "
        "FROM records r ORDER BY flag_count DESC, r.id DESC").fetchall()
    flags_by_record = {}
    for f in db.execute("SELECT * FROM flags ORDER BY id DESC").fetchall():
        flags_by_record.setdefault(f["record_id"], []).append(f)
    return render_template("reviewer.html", records=records,
                           flags_by_record=flags_by_record)


@app.route("/reviewer/record/<record_id>/remove", methods=["POST"])
@reviewer_required
def reviewer_remove(record_id):
    reason = request.form.get("reason", "").strip()[:300]
    if not reason:
        flash("Please give a reason for removing the record.", "error")
    else:
        db = get_db()
        cur = db.execute(
            "UPDATE records SET status = 'removed', removed_reason = ? "
            "WHERE record_id = ?", (reason, record_id))
        if cur.rowcount:
            db.execute(
                "INSERT INTO audit_log (record_id, action, details, created_at) "
                "VALUES (?, ?, ?, ?)",
                (record_id, "removed", f"Removed by reviewer: {reason}", now()))
            db.commit()
            flash(f"{record_id} removed.", "success")
    return redirect(url_for("reviewer_dashboard"))


@app.route("/reviewer/record/<record_id>/restore", methods=["POST"])
@reviewer_required
def reviewer_restore(record_id):
    db = get_db()
    cur = db.execute(
        "UPDATE records SET status = 'active', removed_reason = NULL "
        "WHERE record_id = ?", (record_id,))
    if cur.rowcount:
        db.execute(
            "INSERT INTO audit_log (record_id, action, details, created_at) "
            "VALUES (?, ?, ?, ?)",
            (record_id, "restored", "Restored by reviewer", now()))
        db.commit()
        flash(f"{record_id} restored.", "success")
    return redirect(url_for("reviewer_dashboard"))


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)