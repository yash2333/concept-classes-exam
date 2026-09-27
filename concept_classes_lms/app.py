import os
from datetime import datetime
from functools import wraps
from io import BytesIO

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-in-production')
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

# Render PostgreSQL: set DATABASE_URL on the Web Service.
# Local fallback: SQLite for easy development.
database_url = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(BASE, 'concept_classes.db')}")
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql+psycopg2://', 1)
elif database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
ALLOWED = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    class_name = db.Column(db.String(50))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Material(db.Model):
    __tablename__ = 'materials'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    title = db.Column(db.String(200), nullable=False)
    file_name = db.Column(db.String(255))
    video_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Test(db.Model):
    __tablename__ = 'tests'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    duration_minutes = db.Column(db.Integer, default=30)
    question_paper = db.Column(db.String(255))
    question_paper_data = db.Column(db.LargeBinary)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id', ondelete='CASCADE'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.Text)
    option_b = db.Column(db.Text)
    option_c = db.Column(db.Text)
    option_d = db.Column(db.Text)
    correct_answer = db.Column(db.String(1))


class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'))
    score = db.Column(db.Integer)
    total = db.Column(db.Integer)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class ProctorEvent(db.Model):
    __tablename__ = 'proctor_events'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    test_id = db.Column(db.Integer, db.ForeignKey('tests.id'))
    event_type = db.Column(db.String(100))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            db.session.add(User(name='Concept Classes Admin', username='admin', password_hash=generate_password_hash('admin123'), role='admin'))
        if not User.query.filter_by(username='teacher').first():
            db.session.add(User(name='Demo Teacher', username='teacher', password_hash=generate_password_hash('teacher123'), role='teacher'))
        if not User.query.filter_by(username='student').first():
            db.session.add(User(name='Demo Student', username='student', password_hash=generate_password_hash('student123'), role='student', class_name='10'))
        db.session.commit()


def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                return 'Unauthorized', 403
            return fn(*args, **kwargs)
        return wrapper
    return deco


@app.context_processor
def common():
    return {'user': session}


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username, status='active').first()
        if user and check_password_hash(user.password_hash, password):
            session.update(user_id=user.id, name=user.name, role=user.role, username=user.username)
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required()
def dashboard():
    if session['role'] == 'student':
        return redirect(url_for('student_dashboard'))
    if session['role'] == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    return redirect(url_for('admin_dashboard'))


@app.route('/student')
@login_required('student')
def student_dashboard():
    courses = Course.query.order_by(Course.id.desc()).all()
    tests = db.session.execute(text('''SELECT t.id,t.title,t.duration_minutes,t.question_paper,c.name AS course FROM tests t LEFT JOIN courses c ON c.id=t.course_id ORDER BY t.id DESC''')).mappings().all()
    results = db.session.execute(text('''SELECT r.score,r.total,r.submitted_at,t.title FROM results r JOIN tests t ON t.id=r.test_id WHERE r.student_id=:sid ORDER BY r.id DESC'''), {'sid': session['user_id']}).mappings().all()
    return render_template('student/dashboard.html', courses=courses, tests=tests, results=results)


@app.route('/test/<int:test_id>', methods=['GET', 'POST'])
@login_required('student')
def take_test(test_id):
    test = Test.query.get(test_id)
    questions = Question.query.filter_by(test_id=test_id).all()
    if not test:
        return 'Test not found', 404
    if request.method == 'POST':
        score = sum(1 for q in questions if request.form.get(f'q{q.id}') == q.correct_answer)
        db.session.add(Result(student_id=session['user_id'], test_id=test_id, score=score, total=len(questions)))
        db.session.commit()
        return render_template('student/result.html', test=test, score=score, total=len(questions))
    return render_template('student/test.html', test=test, questions=questions)


@app.route('/api/proctor-event', methods=['POST'])
@login_required('student')
def proctor_event():
    data = request.get_json(silent=True) or {}
    event = ProctorEvent(student_id=session['user_id'], test_id=data.get('test_id'), event_type=data.get('event_type', 'unknown'), details=str(data.get('details', ''))[:1000])
    db.session.add(event)
    db.session.commit()
    return jsonify(ok=True)


@app.route('/teacher')
@login_required('teacher')
def teacher_dashboard():
    tests = db.session.execute(text('''SELECT t.id,t.title,t.duration_minutes,t.question_paper,c.name AS course FROM tests t LEFT JOIN courses c ON c.id=t.course_id WHERE t.teacher_id=:tid ORDER BY t.id DESC'''), {'tid': session['user_id']}).mappings().all()
    courses = Course.query.filter((Course.teacher_id == session['user_id']) | (Course.teacher_id.is_(None))).order_by(Course.id.desc()).all()
    students = db.session.execute(text("SELECT id,name,username,class_name,status FROM users WHERE role='student' ORDER BY id DESC")).mappings().all()
    events = db.session.execute(text('''SELECT p.*,u.name AS student,t.title FROM proctor_events p JOIN users u ON u.id=p.student_id LEFT JOIN tests t ON t.id=p.test_id ORDER BY p.id DESC LIMIT 30''')).mappings().all()
    return render_template('teacher/dashboard.html', tests=tests, courses=courses, students=students, events=events)


@app.route('/teacher/course', methods=['POST'])
@login_required('teacher')
def create_course():
    db.session.add(Course(name=request.form['name'], description=request.form.get('description', ''), teacher_id=session['user_id']))
    db.session.commit()
    flash('Course created.', 'success')
    return redirect(url_for('teacher_dashboard'))


@app.route('/teacher/student', methods=['POST'])
@login_required('teacher')
def create_student():
    name = request.form['name'].strip()
    username = request.form['username'].strip()
    password = request.form['password']
    try:
        db.session.add(User(name=name, username=username, password_hash=generate_password_hash(password), role='student', class_name=request.form.get('class_name', ''), status='active'))
        db.session.commit()
        flash('Student account created.', 'success')
    except Exception:
        db.session.rollback()
        flash('Username already exists or account could not be created.', 'error')
    return redirect(url_for('teacher_dashboard'))


@app.route('/teacher/test', methods=['POST'])
@login_required('teacher')
def create_test():
    test = Test(title=request.form['title'], course_id=(int(request.form['course_id']) if request.form.get('course_id') else None), teacher_id=session['user_id'], duration_minutes=int(request.form.get('duration', 30)))
    db.session.add(test)
    db.session.flush()
    for line in request.form.get('questions', '').splitlines():
        parts = [x.strip() for x in line.split('|')]
        if len(parts) >= 6:
            db.session.add(Question(test_id=test.id, question=parts[0], option_a=parts[1], option_b=parts[2], option_c=parts[3], option_d=parts[4], correct_answer=parts[5].upper()))
    db.session.commit()
    flash('Test created. Use the upload button to attach a paper.', 'success')
    return redirect(url_for('teacher_dashboard'))


@app.route('/teacher/test/<int:test_id>/upload', methods=['POST'])
@login_required('teacher')
def upload_paper(test_id):
    test = Test.query.filter_by(id=test_id, teacher_id=session['user_id']).first()
    file = request.files.get('paper')
    if not test:
        return 'Test not found', 404
    if not file or not file.filename:
        flash('Choose a file.', 'error')
        return redirect(url_for('teacher_dashboard'))
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED:
        flash('Allowed: PDF, DOC, DOCX, JPG, JPEG, PNG.', 'error')
        return redirect(url_for('teacher_dashboard'))
    test.question_paper = secure_filename(file.filename)
    test.question_paper_data = file.read()
    db.session.commit()
    flash('Question paper uploaded and stored in PostgreSQL.', 'success')
    return redirect(url_for('teacher_dashboard'))


@app.route('/test/<int:test_id>/paper')
@login_required()
def question_paper(test_id):
    test = Test.query.get_or_404(test_id)
    if not test.question_paper_data:
        return 'No question paper uploaded.', 404
    ext = (test.question_paper or '').rsplit('.', 1)[-1].lower()
    mimetypes = {'pdf':'application/pdf','png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','doc':'application/msword','docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
    return send_file(BytesIO(test.question_paper_data), download_name=test.question_paper or 'question-paper', mimetype=mimetypes.get(ext, 'application/octet-stream'), as_attachment=False)


@app.route('/teacher/test/<int:test_id>/delete', methods=['POST'])
@login_required('teacher')
def delete_test(test_id):
    test = Test.query.filter_by(id=test_id, teacher_id=session['user_id']).first()
    if test:
        Question.query.filter_by(test_id=test_id).delete()
        Result.query.filter_by(test_id=test_id).delete()
        ProctorEvent.query.filter_by(test_id=test_id).delete()
        db.session.delete(test)
        db.session.commit()
        flash('Test deleted.', 'success')
    return redirect(url_for('teacher_dashboard'))


@app.route('/admin')
@login_required('admin')
def admin_dashboard():
    users = User.query.order_by(User.id.desc()).all()
    return render_template('admin/dashboard.html', users=users)


init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
