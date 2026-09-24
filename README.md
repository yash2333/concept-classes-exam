# Concept Classes Exam System v2.1

This version removes `better-sqlite3`, so Windows does NOT need Visual Studio Build Tools just to install the project.

Data is stored in `data.json`. Uploaded notebook images are stored in `uploads/`.

Features:
- Admin/student login
- Create tests and questions
- MCQ and written/math questions
- Notebook solution image upload
- Configurable upload deadline
- Webcam face detection
- Tab/focus monitoring
- Timed exam
- Automatic submission after repeated proctoring violations
- Marks and negative marking

Run:
1. Open this folder in Command Prompt.
2. `npm install`
3. `npm start`
4. Open http://localhost:3000

Admin: admin / admin123

Important: For production, replace plain-text passwords with bcrypt/argon2, use HTTPS, secure sessions, file scanning, access controls and proper persistent database storage.