# Roots

**Know where culture comes from.**

A provenance and attribution tool for cultural works, built by Team RA.1 for ART//CODE 2026 (challenge PS-03, Attribution & Ownership).

- Live demo: https://rootsra1.pythonanywhere.com
- Source code: https://github.com/AmeenaGitHub/roots

## 1. Project Overview

Roots helps people see where a cultural work comes from, who should be credited, and how it may be reused, before they reuse it. Each work has a record with its creator, source, region, cultural context, reuse permission and credit line. Every record gets a shareable credit card with a QR code, a downloadable provenance record, a flagging option and an audit trail. Reviewers can remove or restore records.

Roots records the credit and permissions **stated by the person who created the record**. It is an attribution and permission-management prototype. It is not an automated copyright detector and does not decide legal ownership.

## 2. Problem Statement

Cultural artwork, traditional patterns, photographs of heritage objects and community-created content are often reposted online without credit or without information about the people and communities behind them. Generative AI adds further questions about consent, cultural context and acceptable reuse.

Roots addresses this for challenge PS-03 (Attribution & Ownership): can a user identify the source of a cultural work and understand the stated permissions before reusing it?

## 3. Key Features

- **Records with provenance:** creator, art form, region, year, cultural context, source, reuse permission and a credit line, with an optional image.
- **Consent confirmation:** a record cannot be saved unless the person confirms they are the creator, or have the creator's or community's permission.
- **Catalogue search and filters:** search by title, creator or record ID, and filter by art form and by reuse permission.
- **Credit card:** a shareable page per record with a QR code, a printable view and a downloadable provenance record (JSON).
- **Check an image:** upload a picture to see whether it looks like an image already in the catalogue, and who it is credited to. The uploaded image is not saved.
- **Similarity notices:** when a new record's image resembles an existing one, both records get a neutral notice in their audit trail.
- **Flagging:** anyone can flag a record for missing attribution, possible unauthorised reuse or incorrect information.
- **Audit trail:** each record keeps a log of what has happened to it.
- **Reviewer dashboard:** a password-protected page where reviewers see flags and can remove or restore records with a reason. Removal hides a record but keeps its history.

## 4. Technology Stack


Language - Python 3 
Web framework - Flask, Jinja templates 
Database - SQLite 
Image check - OpenCV (SIFT feature matching) and NumPy 
QR codes and images - qrcode, Pillow 
Front end - HTML and plain CSS (responsive, no framework) 
Hosting - PythonAnywhere

## 5. System Architecture

```
Browser (desktop or phone)
        |
        v
Flask app (app.py)
   |-- Routes: catalogue, add record, record page, credit card,
   |           QR code, download, flag, check image, reviewer pages
   |-- SQLite database (roots.db): records, flags, audit_log
   |-- Image storage: static/uploads/
   |-- Image check: OpenCV SIFT features + consistency check (RANSAC)
   |-- QR codes: generated on request with qrcode
```

**How the image check works:** Roots finds distinctive points in an image and checks whether another image shows the same points in a consistent layout. It catches resized, recompressed, filtered, cropped and rotated copies. It does not catch mirrored copies or recreated versions. It gives a hint only, never proof of ownership.

**Permissions model:** each record carries one of four stated reuse permissions: free to reuse with credit, non-commercial reuse with credit, ask the creator before reuse, or do not reuse. Reviewers are authorised by a shared password stored as a server setting, never in the code.

**Data:**

- `records`: the work's details, reuse permission, credit line, image file name, status (active or removed) and removal reason.
- `flags`: reports made against a record, with a reason and a note.
- `audit_log`: a timeline of what happened to each record (created, flagged, similarity notice, removed, restored).

## 6. Installation & Setup Instructions

You need **Python 3.10 or newer** and **Git**.

```bash
git clone https://github.com/AmeenaGitHub/roots.git
cd roots
python -m venv venv
```

Activate the virtual environment:

- Windows: `venv\Scripts\activate`
- Mac or Linux: `source venv/bin/activate`

Install the dependencies, add the 12 demonstration records and start the app:

```bash
pip install -r requirements.txt
python seed.py
python app.py
```

Open http://127.0.0.1:5000 in your browser.

**Project structure**

```
roots/
├── app.py              Flask app: routes, database, image check
├── seed.py             Adds 12 demonstration records
├── requirements.txt    Python dependencies
├── LICENSE             MIT license
├── templates/          HTML pages
├── static/             CSS and uploaded images
└── docs/screenshots/   Screenshots used in this README
```

## 7. Environment Variables

No keys or passwords are stored in this repository. Both variables are optional for a local run.

| Variable | Purpose | If not set |
|---|---|---|
| `REVIEWER_PASSWORD` | Password for the reviewer dashboard | Reviewer login is disabled |
| `SECRET_KEY` | Signs the session cookie for reviewer login | A development-only key is used. Set a long random string for any public deployment |

Set them in the same terminal before starting the app:

- Windows PowerShell: `$env:REVIEWER_PASSWORD="choose-a-password"`
- Windows Command Prompt: `set REVIEWER_PASSWORD=choose-a-password`
- Mac or Linux: `export REVIEWER_PASSWORD="choose-a-password"`

Reviewer demo password for the live site: **[PASTE-YOUR-REVIEWER-PASSWORD-HERE]** (a throwaway password for this prototype only).

## 8. Usage Instructions

1. **Browse and search:** on the catalogue, search by title, creator or record ID (for example `RT-0003`), and use the art form and reuse permission filters.
2. **Read a record:** open a card to see the creator, region, cultural context, source, reuse permission and credit line.
3. **Add a record:** open **Add a record**, fill in the form, optionally add an image, tick the consent box and save.
4. **Share a credit card:** on a record, click **View credit card**. Scan the QR code, print the page, or download the provenance record as JSON.
5. **Check an image:** open **Check an image**, upload a picture, and see any similar records with their credit and reuse permission.
6. **Flag a problem:** on a record page, use **Flag this record** with a reason and a note. The flag appears in the audit trail.
7. **Review (reviewers only):** open **Reviewer login**, enter the reviewer password, review flags, and remove or restore a record with a reason.

## 9. Demonstration Screenshots

roots/docs/screenshots/

## 10. Team Members

Team RA.1

- Haripriya K S
- Ameena Sherin M

## 11. Limitations & Future Scope

**Limitations**

- Reviewers sign in with one shared password. There are no individual user accounts, so creators cannot yet edit or remove their own records.
- Anyone can flag any record, so a real version would need rate limits and a way for creators to respond.
- The image check misses mirrored copies and recreated or redrawn versions, and it only compares with records already in Roots.
- The prototype runs on a free host with a small database and limited storage.
- The starter records are demonstrations, not verified community data.

**Future scope**

- User accounts, so creators can prove who they are and manage their own records.
- Community review and a process for communities to respond to flags.
- Support for audio and video works and for more than one image per record.
- Machine-readable provenance records that follow an open metadata standard.

## 12. License & Attribution

Released under the **MIT License**. See [LICENSE](LICENSE).

**Attribution**

- Built with Flask, OpenCV, NumPy, qrcode and Pillow, all open-source libraries under their own licenses.
- The 12 starter records are demonstration records. Their creators are labelled "(demo)", they are not real people, and the cultural context was written by the team from general public knowledge.
- Images in the live demo were demo images.
- Roots records stated credit and permissions only. It does not establish legal ownership.