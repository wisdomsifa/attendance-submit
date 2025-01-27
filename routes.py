import uuid
from datetime import datetime, timedelta
from flask import render_template, session, redirect, url_for, make_response, request, abort
from functools import wraps
from app_init import app, db
from models.attendance import Lecture, Attendance
from models.models import User
import weasyprint

def with_sidebar(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        return render_template(f.__name__.replace('_route', '.html'), with_sidebar=True)
    return decorated_function

@app.route("/")
def landing_route():
    if 'user' in session:
        return redirect(url_for('dashboard_route'))
    return render_template("landing.html", with_sidebar=False)

@app.route("/dashboard")
def dashboard_route():
    if 'user' not in session:
        return redirect(url_for('landing_route'))
    
    user = User.query.filter_by(email=session['user']['user_email']).first()
    active_lectures = Lecture.query.filter_by(lecturer_id=user.id)\
        .filter(Lecture.expiry_time > datetime.utcnow())\
        .order_by(Lecture.created_at.desc())\
        .all()
    
    return render_template("dashboard.html", with_sidebar=True, active_lectures=active_lectures)

@app.route("/profile")
def profile_route():
    if 'user' not in session:
        return redirect(url_for('landing_route'))
    
    user = User.query.filter_by(email=session['user']['user_email']).first()
    return render_template("profile.html", with_sidebar=True, user=user)

@app.route("/generate-link", methods=['POST'])
def generate_attendance_link():
    if 'user' not in session:
        return redirect(url_for('landing_route'))
    
    title = request.form.get('title')
    course_name = request.form.get('course_name')
    expiry_minutes = int(request.form.get('expiry_minutes', 60))
    
    user = User.query.filter_by(email=session['user']['user_email']).first()
    
    # Calculate expiry time from current time
    current_time = datetime.utcnow()
    expiry_time = current_time + timedelta(minutes=expiry_minutes)
    
    # Create new lecture with current time as reference
    lecture = Lecture(
        lecturer_id=user.id,
        title=title,
        course_name=course_name,
        link_code=str(uuid.uuid4()),
        expiry_time=expiry_time,
        created_at=current_time,
        is_downloadable=False
    )
    
    db.session.add(lecture)
    db.session.commit()
    
    return redirect(url_for('dashboard_route'))

@app.route("/attendance/<link_code>")
def attendance_form(link_code):
    lecture = Lecture.query.filter_by(link_code=link_code).first_or_404()
    
    if datetime.utcnow() > lecture.expiry_time:
        return render_template("attendance_form.html", lecture=lecture, expired=True)
    
    return render_template("attendance_form.html", lecture=lecture)

@app.route("/submit-attendance/<link_code>", methods=['POST'])
def submit_attendance(link_code):
    lecture = Lecture.query.filter_by(link_code=link_code).first_or_404()
    
    if datetime.utcnow() > lecture.expiry_time:
        abort(400, description="This attendance link has expired")
    
    student_name = request.form.get('student_name')
    admission_number = request.form.get('admission_number')
    
    # Check if student already submitted attendance
    existing_attendance = Attendance.query.filter_by(
        lecture_id=lecture.id,
        admission_number=admission_number
    ).first()
    
    if existing_attendance:
        return "You have already submitted your attendance", 400
    
    attendance = Attendance(
        lecture_id=lecture.id,
        student_name=student_name,
        admission_number=admission_number
    )
    
    db.session.add(attendance)
    db.session.commit()
    
    # Update lecture downloadable status if expired
    if datetime.utcnow() > lecture.expiry_time:
        lecture.is_downloadable = True
        db.session.commit()
    
    return "Attendance recorded successfully", 200

@app.route("/download-attendance/<int:lecture_id>")
def download_attendance(lecture_id):
    if 'user' not in session:
        return redirect(url_for('landing_route'))
    
    lecture = Lecture.query.get_or_404(lecture_id)
    user = User.query.filter_by(email=session['user']['user_email']).first()
    
    if lecture.lecturer_id != user.id:
        abort(403)
    
    attendances = Attendance.query\
        .filter_by(lecture_id=lecture_id)\
        .order_by(Attendance.timestamp)\
        .all()
    
    html = render_template(
        'attendance_pdf.html',
        lecture=lecture,
        attendances=attendances
    )
    
    pdf = weasyprint.HTML(string=html).write_pdf()
    
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=attendance_{lecture.title}_{lecture.created_at.strftime("%Y%m%d")}.pdf'
    
    return response

@app.route("/logout", methods=['POST'])
def logout_route():
    session.clear()
    return redirect(url_for('landing_route'))