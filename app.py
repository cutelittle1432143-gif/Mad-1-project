from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash,
)
from werkzeug.security import generate_password_hash, check_password_hash

from database import db_session, init_db
from models import User, RecruiterProfile, StudentProfile, JobDrive, DriveApplication


app = Flask(__name__)
app.secret_key = "mad1-project-secret-key-2026"


@app.teardown_appcontext
def close_db_session(exception=None):
    db_session.remove()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                flash("Access denied.", "danger")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/")
def index():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        entered_email = request.form.get("email", "").strip()
        entered_pass = request.form.get("password", "")

        found_user = db_session.query(User).filter_by(email=entered_email).first()

        if found_user is None or not check_password_hash(found_user.password, entered_pass):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("login"))

        if found_user.status == "blacklisted":
            flash("Your account has been blacklisted. Contact placement cell.", "danger")
            return redirect(url_for("login"))

        session["user_id"] = found_user.id
        session["user_name"] = found_user.name
        session["role"] = found_user.role

        if found_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        elif found_user.role == "company":
            return redirect(url_for("company_dashboard"))
        else:
            return redirect(url_for("student_dashboard"))

    return render_template("login.html")


@app.route("/register/student", methods=["GET", "POST"])
def register_student():
    if request.method == "POST":
        stu_name = request.form.get("name", "").strip()
        stu_email = request.form.get("email", "").strip()
        stu_pass = request.form.get("password", "")
        stu_cgpa = request.form.get("cgpa", 0.0)
        stu_resume = request.form.get("resume", "")

        if db_session.query(User).filter_by(email=stu_email).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("register_student"))

        new_user = User(
            name=stu_name,
            email=stu_email,
            password=generate_password_hash(stu_pass),
            role="student",
            status="active",
        )
        db_session.add(new_user)
        db_session.flush()

        stu_profile = StudentProfile(
            user_id=new_user.id,
            name=stu_name,
            email=stu_email,
            cgpa=float(stu_cgpa),
            resume=stu_resume,
        )
        db_session.add(stu_profile)
        db_session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register_student.html")


@app.route("/register/company", methods=["GET", "POST"])
def register_company():
    if request.method == "POST":
        rep_name = request.form.get("name", "").strip()
        rep_email = request.form.get("email", "").strip()
        rep_pass = request.form.get("password", "")
        comp_name = request.form.get("company_name", "").strip()
        hr_phone = request.form.get("hr_contact", "").strip()
        comp_website = request.form.get("website", "").strip()

        if db_session.query(User).filter_by(email=rep_email).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("register_company"))

        new_user = User(
            name=rep_name,
            email=rep_email,
            password=generate_password_hash(rep_pass),
            role="company",
            status="active",
        )
        db_session.add(new_user)
        db_session.flush()

        rec_profile = RecruiterProfile(
            user_id=new_user.id,
            company_name=comp_name,
            hr_contact=hr_phone,
            website=comp_website,
            approval_status="pending",
        )
        db_session.add(rec_profile)
        db_session.commit()

        flash("Company registered! Waiting for admin approval.", "success")
        return redirect(url_for("login"))

    return render_template("register_company.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))


@app.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
    num_students = db_session.query(StudentProfile).count()
    num_companies = db_session.query(RecruiterProfile).count()
    num_drives = db_session.query(JobDrive).count()
    num_applications = db_session.query(DriveApplication).count()

    pending_companies = (
        db_session.query(RecruiterProfile)
        .filter_by(approval_status="pending")
        .all()
    )
    pending_drives = (
        db_session.query(JobDrive)
        .filter_by(status="pending")
        .all()
    )

    approved_drives = (
        db_session.query(JobDrive)
        .filter_by(status="approved")
        .all()
    )

    search_q = request.args.get("q", "").strip()
    search_type = request.args.get("type", "")
    search_results = []

    if search_q:
        if search_type == "student":
            search_results = (
                db_session.query(StudentProfile)
                .filter(
                    (StudentProfile.name.ilike(f"%{search_q}%"))
                    | (StudentProfile.id == search_q if search_q.isdigit() else False)
                )
                .all()
            )
        elif search_type == "company":
            search_results = (
                db_session.query(RecruiterProfile)
                .filter(RecruiterProfile.company_name.ilike(f"%{search_q}%"))
                .all()
            )

    eligibility_filter = request.args.get("eligibility", "").strip()
    filtered_drives = []
    if eligibility_filter:
        filtered_drives = (
            db_session.query(JobDrive)
            .filter(JobDrive.eligibility.ilike(f"%{eligibility_filter}%"))
            .all()
        )

    all_students = db_session.query(StudentProfile).all()
    all_companies = db_session.query(RecruiterProfile).all()

    return render_template(
        "admin_dashboard.html",
        num_students=num_students,
        num_companies=num_companies,
        num_drives=num_drives,
        num_applications=num_applications,
        pending_companies=pending_companies,
        pending_drives=pending_drives,
        approved_drives=approved_drives,
        search_results=search_results,
        search_q=search_q,
        search_type=search_type,
        eligibility_filter=eligibility_filter,
        filtered_drives=filtered_drives,
        all_students=all_students,
        all_companies=all_companies,
    )


@app.route("/admin/approve-company/<int:cid>")
@login_required
@role_required("admin")
def approve_company(cid):
    rec = db_session.query(RecruiterProfile).get(cid)
    if rec:
        rec.approval_status = "approved"
        db_session.commit()
        flash(f"Company '{rec.company_name}' approved.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/reject-company/<int:cid>")
@login_required
@role_required("admin")
def reject_company(cid):
    rec = db_session.query(RecruiterProfile).get(cid)
    if rec:
        rec.approval_status = "rejected"
        db_session.commit()
        flash(f"Company '{rec.company_name}' rejected.", "warning")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/approve-drive/<int:did>")
@login_required
@role_required("admin")
def approve_drive(did):
    drv = db_session.query(JobDrive).get(did)
    if drv:
        drv.status = "approved"
        db_session.commit()
        flash(f"Drive '{drv.job_title}' approved.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/reject-drive/<int:did>")
@login_required
@role_required("admin")
def reject_drive(did):
    drv = db_session.query(JobDrive).get(did)
    if drv:
        drv.status = "closed"
        db_session.commit()
        flash(f"Drive '{drv.job_title}' rejected.", "warning")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/blacklist/<int:uid>")
@login_required
@role_required("admin")
def blacklist_user(uid):
    usr = db_session.query(User).get(uid)
    if usr and usr.role != "admin":
        usr.status = "blacklisted"
        db_session.commit()
        flash(f"User '{usr.name}' blacklisted.", "warning")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/activate/<int:uid>")
@login_required
@role_required("admin")
def activate_user(uid):
    usr = db_session.query(User).get(uid)
    if usr:
        usr.status = "active"
        db_session.commit()
        flash(f"User '{usr.name}' activated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/drive-details/<int:did>")
@login_required
@role_required("admin")
def admin_drive_details(did):
    drv = db_session.query(JobDrive).get(did)
    if not drv:
        flash("Drive not found.", "danger")
        return redirect(url_for("admin_dashboard"))

    apps = db_session.query(DriveApplication).filter_by(drive_id=drv.id).all()

    return render_template(
        "admin_drive_details.html",
        drive=drv,
        applications=apps,
    )


@app.route("/admin/students")
@login_required
@role_required("admin")
def admin_students():
    students = db_session.query(StudentProfile).all()
    return render_template("admin_dashboard.html",
                           num_students=db_session.query(StudentProfile).count(),
                           num_companies=db_session.query(RecruiterProfile).count(),
                           num_drives=db_session.query(JobDrive).count(),
                           num_applications=db_session.query(DriveApplication).count(),
                           pending_companies=[], pending_drives=[],
                           approved_drives=[],
                           search_results=[], search_q="", search_type="",
                           eligibility_filter="", filtered_drives=[],
                           all_students=students, all_companies=[])


@app.route("/admin/companies")
@login_required
@role_required("admin")
def admin_companies():
    companies = db_session.query(RecruiterProfile).all()
    return render_template("admin_dashboard.html",
                           num_students=db_session.query(StudentProfile).count(),
                           num_companies=db_session.query(RecruiterProfile).count(),
                           num_drives=db_session.query(JobDrive).count(),
                           num_applications=db_session.query(DriveApplication).count(),
                           pending_companies=[], pending_drives=[],
                           approved_drives=[],
                           search_results=[], search_q="", search_type="",
                           eligibility_filter="", filtered_drives=[],
                           all_students=[], all_companies=companies)


@app.route("/company/dashboard")
@login_required
@role_required("company")
def company_dashboard():
    curr_user = db_session.query(User).get(session["user_id"])
    profile = curr_user.recruiter_profile

    if not profile:
        flash("Recruiter profile not found.", "danger")
        return redirect(url_for("logout"))

    my_drives = (
        db_session.query(JobDrive)
        .filter_by(company_id=profile.id)
        .all()
    )

    return render_template(
        "company_dashboard.html",
        profile=profile, my_drives=my_drives,
    )


@app.route("/company/create-drive", methods=["GET", "POST"])
@login_required
@role_required("company")
def create_drive():
    curr_user = db_session.query(User).get(session["user_id"])
    profile = curr_user.recruiter_profile

    if not profile or profile.approval_status != "approved":
        flash("Your company must be approved by placement cell before creating drives.", "warning")
        return redirect(url_for("company_dashboard"))

    if request.method == "POST":
        title = request.form.get("job_title", "").strip()
        desc = request.form.get("job_description", "").strip()
        elig = request.form.get("eligibility", "").strip()
        deadline_str = request.form.get("deadline", "")

        dl = None
        if deadline_str:
            try:
                dl = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        new_drive = JobDrive(
            company_id=profile.id,
            job_title=title,
            job_description=desc,
            eligibility=elig,
            deadline=dl,
            status="pending",
        )
        db_session.add(new_drive)
        db_session.commit()

        flash("Drive created! Waiting for admin approval.", "success")
        return redirect(url_for("company_dashboard"))

    return render_template("create_drive.html")


@app.route("/company/edit-drive/<int:did>", methods=["GET", "POST"])
@login_required
@role_required("company")
def edit_drive(did):
    curr_user = db_session.query(User).get(session["user_id"])
    profile = curr_user.recruiter_profile
    drv = db_session.query(JobDrive).get(did)

    if not drv or drv.company_id != profile.id:
        flash("Drive not found or not yours.", "danger")
        return redirect(url_for("company_dashboard"))

    if request.method == "POST":
        drv.job_title = request.form.get("job_title", drv.job_title).strip()
        drv.job_description = request.form.get("job_description", drv.job_description).strip()
        drv.eligibility = request.form.get("eligibility", drv.eligibility).strip()
        deadline_str = request.form.get("deadline", "")
        if deadline_str:
            try:
                drv.deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            except ValueError:
                pass
        db_session.commit()
        flash("Drive updated.", "success")
        return redirect(url_for("company_dashboard"))

    return render_template("create_drive.html", drive=drv, edit=True)


@app.route("/company/delete-drive/<int:did>")
@login_required
@role_required("company")
def delete_drive(did):
    curr_user = db_session.query(User).get(session["user_id"])
    profile = curr_user.recruiter_profile
    drv = db_session.query(JobDrive).get(did)

    if not drv or drv.company_id != profile.id:
        flash("Drive not found or not yours.", "danger")
        return redirect(url_for("company_dashboard"))

    db_session.query(DriveApplication).filter_by(drive_id=drv.id).delete()
    db_session.delete(drv)
    db_session.commit()
    flash("Drive deleted.", "info")
    return redirect(url_for("company_dashboard"))


@app.route("/company/applications/<int:did>")
@login_required
@role_required("company")
def view_drive_applicants(did):
    curr_user = db_session.query(User).get(session["user_id"])
    profile = curr_user.recruiter_profile
    drv = db_session.query(JobDrive).get(did)

    if not drv or drv.company_id != profile.id:
        flash("Drive not found or not yours.", "danger")
        return redirect(url_for("company_dashboard"))

    apps = db_session.query(DriveApplication).filter_by(drive_id=drv.id).all()

    return render_template(
        "view_applications.html",
        drive=drv, applications=apps,
    )


@app.route("/company/update-application/<int:app_id>", methods=["POST"])
@login_required
@role_required("company")
def update_app_status(app_id):
    app_record = db_session.query(DriveApplication).get(app_id)

    if not app_record:
        flash("Application not found.", "danger")
        return redirect(url_for("company_dashboard"))

    new_status = request.form.get("status", "applied")
    app_record.status = new_status
    db_session.commit()
    flash(f"Application status changed to '{new_status}'.", "success")
    return redirect(url_for("view_drive_applicants", did=app_record.drive_id))


@app.route("/student/dashboard")
@login_required
@role_required("student")
def student_dashboard():
    curr_user = db_session.query(User).get(session["user_id"])
    profile = curr_user.student_profile

    available_drives = (
        db_session.query(JobDrive)
        .filter_by(status="approved")
        .all()
    )

    my_recent_apps = (
        db_session.query(DriveApplication)
        .filter_by(student_id=profile.id)
        .order_by(DriveApplication.application_date.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "student_dashboard.html",
        profile=profile, available_drives=available_drives,
        my_recent_apps=my_recent_apps,
    )


@app.route("/student/drives")
@login_required
@role_required("student")
def student_drives():
    all_approved = (
        db_session.query(JobDrive)
        .filter_by(status="approved")
        .all()
    )

    eligibility_filter = request.args.get("eligibility", "").strip()
    if eligibility_filter:
        all_approved = (
            db_session.query(JobDrive)
            .filter_by(status="approved")
            .filter(JobDrive.eligibility.ilike(f"%{eligibility_filter}%"))
            .all()
        )

    return render_template("apply_drive.html", drives=all_approved, eligibility_filter=eligibility_filter)


@app.route("/student/apply/<int:did>", methods=["POST"])
@login_required
@role_required("student")
def apply_for_drive(did):
    curr_user = db_session.query(User).get(session["user_id"])
    profile = curr_user.student_profile
    drv = db_session.query(JobDrive).get(did)

    if not drv or drv.status != "approved":
        flash("This drive is not available.", "warning")
        return redirect(url_for("student_drives"))

    already_applied = (
        db_session.query(DriveApplication)
        .filter_by(student_id=profile.id, drive_id=drv.id)
        .first()
    )
    if already_applied:
        flash("You already applied for this drive.", "warning")
        return redirect(url_for("student_drives"))

    new_app = DriveApplication(
        student_id=profile.id,
        drive_id=drv.id,
        application_date=datetime.utcnow(),
        status="applied",
    )
    db_session.add(new_app)
    db_session.commit()
    flash("Application submitted!", "success")
    return redirect(url_for("student_applications"))


@app.route("/student/applications")
@login_required
@role_required("student")
def student_applications():
    curr_user = db_session.query(User).get(session["user_id"])
    profile = curr_user.student_profile

    my_apps = (
        db_session.query(DriveApplication)
        .filter_by(student_id=profile.id)
        .order_by(DriveApplication.application_date.desc())
        .all()
    )

    return render_template(
        "apply_drive.html",
        drives=None, applications=my_apps, history=True,
    )


@app.route("/student/profile", methods=["GET", "POST"])
@login_required
@role_required("student")
def student_profile():
    curr_user = db_session.query(User).get(session["user_id"])
    profile = curr_user.student_profile

    if request.method == "POST":
        profile.name = request.form.get("name", profile.name).strip()
        profile.email = request.form.get("email", profile.email).strip()
        profile.cgpa = float(request.form.get("cgpa", profile.cgpa))
        profile.resume = request.form.get("resume", profile.resume)

        curr_user.name = profile.name
        curr_user.email = profile.email

        db_session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("student_dashboard"))

    return render_template("register_student.html", profile=profile, edit=True)


if __name__ == "__main__":
    init_db()
    print("Starting Campus Recruitment Manager on http://127.0.0.1:5000")
    app.run(debug=True)
