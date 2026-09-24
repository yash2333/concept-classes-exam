# Deploy Concept Classes Exam on Render

1. Upload this project to a GitHub repository.
2. In Render choose New -> Web Service.
3. Connect the GitHub repository.
4. Build Command: npm install
5. Start Command: npm start
6. Add environment variable SESSION_SECRET (or let Render generate it).
7. Deploy.

The app listens on the PORT supplied by Render and binds to 0.0.0.0.

IMPORTANT:
This development build stores data.json and uploaded notebook images in the local filesystem.
Render web services have an ephemeral filesystem by default. For a real exam platform, use persistent storage (Postgres for relational data and object storage for uploaded images), or attach a persistent disk on a paid Render service.
