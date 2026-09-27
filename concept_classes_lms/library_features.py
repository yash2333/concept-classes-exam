from flask import render_template, request, redirect, url_for, session
from library_data import get_library

BOARD_SUBJECTS = [
    ("Mathematics", "Algebra, geometry, trigonometry, mensuration, statistics and probability"),
    ("Physics", "Numericals, definitions, laws, diagrams and application-based questions"),
    ("Chemistry", "Equations, reactions, periodic properties, organic chemistry and numericals"),
    ("Biology", "Diagrams, processes, terminology, reasoning and structured answers"),
    ("History & Civics", "Dates, causes, effects, constitutional topics and structured explanations"),
    ("Geography", "Maps, resources, climate, agriculture, industries and data interpretation"),
    ("Computer Applications", "Java programming, arrays, strings, methods, inheritance and output questions"),
    ("English Language", "Composition, letters, notice/email, comprehension and grammar")
]

def register_library(app):
    @app.route('/library')
    def library():
        if session.get('role') != 'student':
            return redirect(url_for('login'))
        class_name = request.args.get('class_name', '10').strip()
        if class_name not in get_library():
            class_name = '10'
        q = request.args.get('q', '').strip().lower()
        groups = []
        for subject, chapters in get_library()[class_name].items():
            filtered = []
            for chapter, summary in chapters:
                if not q or q in subject.lower() or q in chapter.lower() or q in summary.lower():
                    filtered.append((chapter, summary))
            if filtered:
                groups.append((subject, filtered))
        return render_template('student/library.html', subjects=groups, selected_class=class_name, q=q)

    @app.route('/library/<class_name>/<subject>/<chapter>')
    def library_chapter(class_name, subject, chapter):
        if session.get('role') != 'student':
            return redirect(url_for('login'))
        chapters = get_library().get(class_name, {}).get(subject, [])
        match = None
        for name, summary in chapters:
            if name == chapter:
                match = (name, summary)
                break
        if not match:
            return 'Chapter not found', 404
        return render_template('student/library_chapter.html', class_name=class_name, subject=subject, chapter=match[0], summary=match[1])

    @app.route('/board-preparation')
    def board_preparation():
        if session.get('role') != 'student':
            return redirect(url_for('login'))
        return render_template('student/board_preparation.html', subjects=BOARD_SUBJECTS)
