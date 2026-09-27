import os
import base64
import mimetypes
from datetime import datetime
from io import BytesIO

from flask import render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.utils import secure_filename
from openai import OpenAI

FILE_TYPES = {'pdf','png','jpg','jpeg','doc','docx','txt','md'}
IMAGE_TYPES = {'png','jpg','jpeg'}
AI_MODEL = os.environ.get('AI_MODEL', 'gpt-5.5')

AI_INSTRUCTIONS = """You are the Concept Classes AI Tutor.
Help students understand and solve academic questions across maths, science,
English, social science, computer science, programming, commerce and general
study skills. Give clear, age-appropriate explanations. For maths and science,
show steps and the final answer. For programming, explain the logic and give
correct code when useful. Read uploaded images and documents carefully.
If content is unreadable, say so and ask for a clearer upload.
If the user is taking a live proctored examination, do not provide direct
answers; provide concept guidance instead.
"""

def register_learning_features(app, db, User):
    class Note(db.Model):
        __tablename__ = 'notes'
        id = db.Column(db.Integer, primary_key=True)
        title = db.Column(db.String(200), nullable=False)
        subject = db.Column(db.String(100), nullable=False, default='General')
        class_name = db.Column(db.String(50))
        description = db.Column(db.Text)
        file_name = db.Column(db.String(255), nullable=False)
        file_data = db.Column(db.LargeBinary, nullable=False)
        mime_type = db.Column(db.String(150))
        teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
        created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    class AISolverHistory(db.Model):
        __tablename__ = 'ai_solver_history'
        id = db.Column(db.Integer, primary_key=True)
        student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
        question = db.Column(db.Text, nullable=False)
        answer = db.Column(db.Text, nullable=False)
        attachment_name = db.Column(db.String(255))
        created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    @app.route('/notes')
    def student_notes():
        if session.get('role') != 'student':
            return redirect(url_for('login'))
        subject = request.args.get('subject', '').strip()
        class_name = request.args.get('class_name', '').strip()
        query = Note.query
        if subject:
            query = query.filter(Note.subject.ilike(f'%{subject}%'))
        if class_name:
            query = query.filter((Note.class_name == class_name) | (Note.class_name.is_(None)))
        notes = query.order_by(Note.id.desc()).all()
        subjects = [x[0] for x in db.session.query(Note.subject).distinct().order_by(Note.subject).all() if x[0]]
        return render_template('student/notes.html', notes=notes, subjects=subjects,
                               selected_subject=subject, selected_class=class_name)

    @app.route('/notes/<int:note_id>/view')
    def view_note(note_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        note = Note.query.get_or_404(note_id)
        return send_file(BytesIO(note.file_data), download_name=note.file_name,
                         mimetype=note.mime_type or 'application/octet-stream',
                         as_attachment=False)

    @app.route('/teacher/notes')
    def teacher_notes():
        if session.get('role') != 'teacher':
            return redirect(url_for('login'))
        notes = Note.query.filter_by(teacher_id=session['user_id']).order_by(Note.id.desc()).all()
        return render_template('teacher/notes.html', notes=notes)

    @app.route('/teacher/note', methods=['POST'])
    def upload_note():
        if session.get('role') != 'teacher':
            return 'Unauthorized', 403
        file = request.files.get('note_file')
        title = request.form.get('title', '').strip()
        subject = request.form.get('subject', '').strip() or 'General'
        class_name = request.form.get('class_name', '').strip()
        description = request.form.get('description', '').strip()
        if not title or not file or not file.filename:
            flash('Enter a note title and choose a file.', 'error')
            return redirect(url_for('teacher_notes'))
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in FILE_TYPES:
            flash('Allowed: PDF, DOC, DOCX, JPG, JPEG, PNG, TXT, MD.', 'error')
            return redirect(url_for('teacher_notes'))
        safe_name = secure_filename(file.filename)
        data = file.read()
        if not data:
            flash('The selected file is empty.', 'error')
            return redirect(url_for('teacher_notes'))
        note = Note(title=title[:200], subject=subject[:100], class_name=class_name[:50] or None,
                    description=description[:2000], file_name=safe_name, file_data=data,
                    mime_type=mimetypes.guess_type(safe_name)[0] or 'application/octet-stream',
                    teacher_id=session['user_id'])
        db.session.add(note)
        db.session.commit()
        flash('Note uploaded successfully.', 'success')
        return redirect(url_for('teacher_notes'))

    @app.route('/teacher/note/<int:note_id>/delete', methods=['POST'])
    def delete_note(note_id):
        if session.get('role') != 'teacher':
            return 'Unauthorized', 403
        note = Note.query.filter_by(id=note_id, teacher_id=session['user_id']).first()
        if note:
            db.session.delete(note)
            db.session.commit()
            flash('Note deleted.', 'success')
        return redirect(url_for('teacher_notes'))

    @app.route('/ai-solver', methods=['GET', 'POST'])
    def ai_solver():
        if session.get('role') != 'student':
            return redirect(url_for('login'))
        history = AISolverHistory.query.filter_by(student_id=session['user_id']).order_by(
            AISolverHistory.id.desc()).limit(12).all()
        answer = None
        question = ''
        attachment_name = None

        if request.method == 'POST':
            question = request.form.get('question', '').strip()
            attachment = request.files.get('attachment')
            attachment_name = secure_filename(attachment.filename) if attachment and attachment.filename else None

            if not question and not attachment_name:
                flash('Type a question or upload a question image/document.', 'error')
                return render_template('student/ai_solver.html', history=history, answer=None, question=question)

            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                flash('AI Solver is ready, but OPENAI_API_KEY is not configured on Render.', 'error')
                return render_template('student/ai_solver.html', history=history, answer=None, question=question)

            content = []
            if question:
                content.append({'type': 'input_text', 'text': question})

            try:
                client = OpenAI(api_key=api_key)
                if attachment and attachment_name:
                    ext = attachment_name.rsplit('.', 1)[-1].lower() if '.' in attachment_name else ''
                    if ext not in FILE_TYPES:
                        flash('AI supports PDF, DOC, DOCX, TXT, MD, JPG, JPEG and PNG.', 'error')
                        return render_template('student/ai_solver.html', history=history, answer=None, question=question)
                    raw = attachment.read()
                    if not raw:
                        flash('The uploaded file is empty.', 'error')
                        return render_template('student/ai_solver.html', history=history, answer=None, question=question)
                    encoded = base64.b64encode(raw).decode('utf-8')
                    mime = mimetypes.guess_type(attachment_name)[0] or 'application/octet-stream'
                    if ext in IMAGE_TYPES:
                        content.append({'type': 'input_image',
                                        'image_url': f'data:{mime};base64,{encoded}',
                                        'detail': 'high'})
                    else:
                        content.append({'type': 'input_file',
                                        'filename': attachment_name,
                                        'file_data': f'data:{mime};base64,{encoded}'})

                response = client.responses.create(
                    model=AI_MODEL,
                    instructions=AI_INSTRUCTIONS,
                    input=[{'role': 'user', 'content': content}]
                )
                answer = response.output_text or 'I could not generate an answer. Please try again.'
                row = AISolverHistory(
                    student_id=session['user_id'],
                    question=question or f'Uploaded: {attachment_name}',
                    answer=answer,
                    attachment_name=attachment_name
                )
                db.session.add(row)
                db.session.commit()
                history = [row] + history
            except Exception as exc:
                db.session.rollback()
                app.logger.exception('AI Solver error')
                flash(f'AI Solver could not answer right now. ({type(exc).__name__})', 'error')

        return render_template('student/ai_solver.html', history=history, answer=answer,
                               question=question, attachment_name=attachment_name)

    return Note, AISolverHistory
