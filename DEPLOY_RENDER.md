# Deploy on Render

1. Upload the contents of this project to the root of your GitHub repository.
2. Render -> New -> Web Service.
3. Connect the GitHub repository.
4. Build command: `npm install`
5. Start command: `npm start`
6. Add environment variable `SESSION_SECRET` with a long random value.
7. Deploy.

The server binds to `0.0.0.0` and uses Render's `PORT` environment variable.

After deployment, verify:
- Student and Teacher login selection
- Teacher creates a student
- Teacher creates an exam and questions
- Student submits an exam
- Teacher opens Check Student Papers
- Teacher saves written marks/comments
- Teacher publishes the result
- Student sees the result under My Results and can download the PDF
