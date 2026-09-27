# Concept Classes LMS — Render Plug & Play

A Flask + PostgreSQL LMS and online test platform for Concept Classes.

## Render deployment (recommended)

1. Upload this folder to a GitHub repository.
2. In Render choose **New → Blueprint**.
3. Select the GitHub repository.
4. Render reads `render.yaml`, creates the web service and PostgreSQL database, and injects `DATABASE_URL` and `SECRET_KEY`.
5. Deploy.

No `npm` command is required.

### If creating a Web Service manually
- Runtime: Python 3
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

## Demo accounts
- Admin: `admin` / `admin123`
- Teacher: `teacher` / `teacher123`
- Student: `student` / `student123`

Change demo passwords before using the system publicly.

## Features
- Student database with hashed passwords
- Student, Teacher and Admin dashboards
- Courses
- Online tests and results
- Teacher question-paper upload stored in PostgreSQL
- Teacher test deletion
- Browser webcam/microphone permission and proctoring event logging
- Render PostgreSQL support
- SQLite fallback for local development

## Important production note
The browser proctoring layer flags observable events such as camera absence, multiple detected faces where implemented, tab changes, and voice activity. These signals are not proof of cheating and should be reviewed by a teacher.

The application stores uploaded question papers in the database to avoid relying on Render's ephemeral local filesystem.
