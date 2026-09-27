# Concept Classes LMS — Render-ready v2

A Flask LMS + online test platform with PostgreSQL support.

## Features
- Student / Teacher / Admin login
- PostgreSQL database on Render (SQLite fallback locally)
- Passwords stored as secure hashes
- Teacher creates students, courses and tests
- Question paper upload stored in PostgreSQL (no Render local-disk dependency)
- Delete test with related questions/results/proctor-event cleanup
- Student online test + timer + results
- Browser camera/microphone monitoring and proctor-event logging
- Voice activity and tab-switch event detection

## Deploy on Render

### Option A — Blueprint (recommended)
1. Push this folder to GitHub.
2. In Render choose **New → Blueprint** and select the repository.
3. Render reads `render.yaml`, creates the web service and PostgreSQL database, and connects `DATABASE_URL` automatically.
4. Wait for deployment and open the generated `onrender.com` URL.

### Option B — Manual
Create a PostgreSQL database first, then a Web Service.

**Build Command**
```text
pip install -r requirements.txt
```

**Start Command**
```text
gunicorn app:app
```

Add these environment variables to the Web Service:
- `DATABASE_URL` = your Render PostgreSQL connection string
- `SECRET_KEY` = a long random secret

## Demo accounts
- Admin: `admin` / `admin123`
- Teacher: `teacher` / `teacher123`
- Student: `student` / `student123`

Change these demo passwords before using the system publicly.

## Local run
```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```
Open `http://127.0.0.1:5000`.

## Important production notes
- Browser camera/microphone access requires HTTPS; Render provides HTTPS on the deployed URL.
- The current proctoring layer records signals/events. It does not prove that a student cheated and should be reviewed by a teacher.
- Question papers are stored as database binary data to avoid depending on Render's ephemeral web-service filesystem.
- For larger video/learning-material files, use object storage rather than PostgreSQL.
- Add CSRF protection, rate limiting, password reset, stronger role permissions, privacy/consent notices and tested computer-vision models before high-stakes exams.
