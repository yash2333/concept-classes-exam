# Concept Classes Professional Examination Portal

A browser-based online examination portal for Concept Classes.

## Current features
- Student and Teacher login portals
- Teacher creates student accounts and examinations
- MCQ and written/math questions
- Timed examinations
- Webcam/face-detection proctoring signals
- Tab/focus violation tracking and auto-submit after repeated violations
- Written solution image upload with deadline
- Student sees a "Result will be declared soon" message after submission
- Teacher paper-review workspace
- Teacher awards marks and adds feedback to written answers
- Teacher publishes results only after review
- Student has a dedicated **My Results** section
- Student can view published marks and teacher comments
- Student can download a result report as PDF
- Professional responsive Concept Classes UI

## Demo teacher account
Username: `admin`
Password: `admin123`

Do not expose demo credentials to students. For production, replace this with hashed passwords and proper account management.

## Production note
The current educational MVP stores application data in `data.json` and uploaded images in `uploads/`. Render's ordinary filesystem is not suitable for durable production storage. For important exams, migrate to PostgreSQL and object storage or a persistent disk, and add password hashing, secure session storage, CSRF protection, file scanning, stronger authorization, privacy/consent flows, and robust audit logging.


## Branding
- Concept Classes logo and poster are included in `public/`.
- Footer and result PDF include **Designed & Developed by Yash Pandey**.
