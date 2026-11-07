import os
import sqlite3
import uuid
from datetime import datetime, timezone

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, url_for)

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


@app.route("/")
def index():
    records = get_db().execute(
        "SELECT * FROM records ORDER BY id DESC").fetchall()
    return render_template("index.html", records=records)


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
                record_id = create_record(get_db(), form, image)
                flash(f"Record {record_id} created.", "success")
                return redirect(url_for("record_detail", record_id=record_id))
    return render_template("new.html", form=form, reuse_options=REUSE_OPTIONS)


@app.route("/record/<record_id>")
def record_detail(record_id):
    record = get_db().execute(
        "SELECT * FROM records WHERE record_id = ?", (record_id,)).fetchone()
    if record is None:
        abort(404)
    return render_template("record.html", record=record)


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True)