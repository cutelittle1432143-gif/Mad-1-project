# Campus Recruitment Manager — Complete Project Explanation

This document explains every file in the project line by line — what each line does, how
the files connect, and how the full application works end to end.

---

## Project Structure

```
placement_portal/
├── app.py                  ← Main Flask application (routes + logic)
├── models.py               ← SQLAlchemy database models (tables)
├── database.py             ← Database engine + session + init function
├── placement.db            ← SQLite database file (auto-created)
├── templates/
│   ├── base.html           ← Shared layout (navbar, sidebar, footer)
│   ├── login.html          ← Login page
│   ├── register_student.html ← Student registration + profile edit
│   ├── register_company.html ← Company registration
│   ├── admin_dashboard.html  ← Admin panel (Placement Cell Panel)
│   ├── admin_drive_details.html ← Admin view of a single drive + applicants
│   ├── student_dashboard.html   ← Student home page (Student Portal)
│   ├── company_dashboard.html   ← Company home page (Recruiter Panel)
│   ├── create_drive.html        ← Create / edit a placement drive
│   ├── apply_drive.html         ← Browse drives + application history
│   └── view_applications.html   ← Company view of applicants for a drive
└── static/
    └── style.css           ← Custom CSS (sidebar, footer styling)
```

---

## 1. database.py — Database Setup

This is the first file that runs. It creates the database engine and provides a
function to initialise all tables.

```
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
```
- `create_engine` — creates a connection to the SQLite file
- `scoped_session` — gives each web request its own database session so they
  don't interfere with each other
- `sessionmaker` — factory that creates new sessions
- `declarative_base` — base class that all our models inherit from

```
db_engine = create_engine("sqlite:///placement.db", echo=False)
```
- Creates an engine pointing to `placement.db` in the project folder
- `echo=False` means SQLAlchemy will not print raw SQL queries to the console

```
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
)
```
- `autocommit=False` — we manually call `commit()` when we want to save
- `autoflush=False` — we control when data is flushed to the database
- `bind=db_engine` — links the session to our SQLite engine
- `scoped_session` wraps it so Flask can safely use it across threads

```
Base = declarative_base()
Base.query = db_session.query_property()
```
- `Base` — every model class inherits from this
- `Base.query` — lets us write `User.query.filter_by(...)` as a shortcut

```
def init_db():
    import models
    Base.metadata.create_all(bind=db_engine)
```
- `import models` — forces Python to load all models so `Base.metadata` knows
  about all the tables
- `create_all` — creates the actual tables in the SQLite file if they don't exist

```
    from models import User
    from werkzeug.security import generate_password_hash

    admin_user = db_session.query(User).filter_by(email="placement_admin@college.edu").first()
    if admin_user is None:
        admin_user = User(
            name="Placement Admin",
            email="placement_admin@college.edu",
            password=generate_password_hash("admin123"),
            role="admin",
            status="active",
        )
        db_session.add(admin_user)
        db_session.commit()
```
- Checks if an admin user already exists by email
- If not, creates one with a **hashed** password (never stored in plain text)
- `db_session.add()` stages it, `db_session.commit()` saves to database
- This runs every time you start the app, but only creates the admin once

---

## 2. models.py — Database Tables

Each class here becomes a table in SQLite. SQLAlchemy maps Python objects to
database rows automatically.

### User table
```
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password = Column(String(256), nullable=False)
    role = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="active")
```
- `__tablename__` — name of the actual SQL table
- `id` — auto-incrementing primary key, each user gets a unique number
- `email` — `unique=True` prevents two users having the same email
- `password` — stores the hashed password (256 chars is enough for hash)
- `role` — one of: `"admin"`, `"student"`, or `"company"`
- `status` — `"active"` or `"blacklisted"`

```
    recruiter_profile = relationship("RecruiterProfile", backref="user", uselist=False)
    student_profile = relationship("StudentProfile", backref="user", uselist=False)
```
- These are **relationships** — not actual columns, but links to related tables
- `uselist=False` means it's a one-to-one relationship (one user = one profile)
- `backref="user"` means from a RecruiterProfile you can access `.user` to get
  the parent User object

### RecruiterProfile table (was CompanyProfile)
```
class RecruiterProfile(Base):
    __tablename__ = "recruiter_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_name = Column(String(200), nullable=False)
    hr_contact = Column(String(120))
    website = Column(String(200))
    approval_status = Column(String(20), nullable=False, default="pending")

    drives = relationship("JobDrive", backref="recruiter", lazy=True)
```
- `user_id` — foreign key linking this profile to a specific User
- `ForeignKey("users.id")` — tells SQLAlchemy which column to reference
- `approval_status` — starts as `"pending"`, admin changes it to `"approved"` or
  `"rejected"`
- `drives` — one company can create many job drives. `backref="recruiter"` means
  from a JobDrive you can access `.recruiter` to get the company

### StudentProfile table
```
class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=False)
    cgpa = Column(Float, default=0.0)
    resume = Column(Text, default="")

    applications = relationship("DriveApplication", backref="student", lazy=True)
```
- `cgpa` — Float type, stores the student's grade
- `resume` — Text field, stores plain text or a link to a resume
- `applications` — one student can apply to many drives. `backref="student"`
  means from a DriveApplication you can access `.student`

### JobDrive table (was PlacementDrive)
```
class JobDrive(Base):
    __tablename__ = "job_drives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("recruiter_profiles.id"), nullable=False)
    job_title = Column(String(200), nullable=False)
    job_description = Column(Text, nullable=True)
    eligibility = Column(String(200), nullable=True)
    deadline = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="pending")

    applications = relationship("DriveApplication", backref="drive", lazy=True)
```
- `company_id` — links to RecruiterProfile (which company created this drive)
- `status` — `"pending"` (waiting for admin), `"approved"` (visible to students),
  or `"closed"` (rejected or expired)
- `applications` — all student applications for this drive

### DriveApplication table (was Application)
```
class DriveApplication(Base):
    __tablename__ = "drive_applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id"), nullable=False)
    drive_id = Column(Integer, ForeignKey("job_drives.id"), nullable=False)
    application_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), nullable=False, default="applied")
```
- `student_id` + `drive_id` — links the application to a specific student and drive
- `application_date` — auto-set to current time when created
- `status` — `"applied"`, `"shortlisted"`, `"selected"`, or `"rejected"`

### How the tables connect (relationships)

```
User ──1:1──> RecruiterProfile ──1:many──> JobDrive ──1:many──> DriveApplication
User ──1:1──> StudentProfile ──1:many──> DriveApplication
```

---

## 3. app.py — Flask Routes and Logic

This is the main file. It handles all HTTP requests, processes forms, queries the
database, and renders HTML templates.

### App setup (lines 1–17)

```
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import db_session, init_db
from models import User, RecruiterProfile, StudentProfile, JobDrive, DriveApplication
```
- `wraps` — used to create decorators that preserve function names
- `session` — Flask's built-in session storage (saved in browser cookies)
- `flash` — shows one-time messages to the user (success, error, etc.)
- `generate_password_hash` / `check_password_hash` — for secure password handling
- We import `db_session` from database.py and all models from models.py

```
app = Flask(__name__)
app.secret_key = "mad1-project-secret-key-2026"
```
- Creates the Flask application
- `secret_key` is required for sessions to work (signs the session cookie)

```
@app.teardown_appcontext
def close_db_session(exception=None):
    db_session.remove()
```
- After every request, this removes the database session for that request
- Prevents database connection leaks

### Decorators (lines 22–38)

```
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper
```
- This is a **decorator**. Putting `@login_required` above a route function means
  that route will first check if the user is logged in
- `session["user_id"]` is set during login. If it's missing, the user gets
  redirected to the login page

```
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
```
- Similar, but checks the user's **role**
- `@role_required("admin")` means only admin users can access that route
- If a student tries to visit an admin page, they get redirected

### Login route (lines 41–68)

```
@app.route("/login", methods=["GET", "POST"])
def login():
```
- `GET` — shows the login form
- `POST` — processes the form submission

```
    if request.method == "POST":
        entered_email = request.form.get("email", "").strip()
        entered_pass = request.form.get("password", "")
```
- `request.form.get()` reads the value from the HTML form
- `.strip()` removes accidental whitespace

```
        found_user = db_session.query(User).filter_by(email=entered_email).first()
```
- Searches the User table for a row with matching email
- `.first()` returns the first match or `None` if no match

```
        if found_user is None or not check_password_hash(found_user.password, entered_pass):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("login"))
```
- If no user found OR the password hash doesn't match, show error
- `check_password_hash` compares the entered password against the stored hash

```
        if found_user.status == "blacklisted":
            flash("Your account has been blacklisted. Contact placement cell.", "danger")
            return redirect(url_for("login"))
```
- Blacklisted users can't log in even with correct credentials

```
        session["user_id"] = found_user.id
        session["user_name"] = found_user.name
        session["role"] = found_user.role
```
- Store user info in the session — this is how we "remember" who's logged in
- The session persists across page loads until logout

```
        if found_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        elif found_user.role == "company":
            return redirect(url_for("company_dashboard"))
        else:
            return redirect(url_for("student_dashboard"))
```
- After login, redirect to the appropriate dashboard based on role

### Student registration route (lines 71–101)

```
@app.route("/register/student", methods=["GET", "POST"])
def register_student():
```
- Handles both showing the registration form (GET) and processing it (POST)

```
        if db_session.query(User).filter_by(email=stu_email).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("register_student"))
```
- Duplicate check — prevents two accounts with the same email

```
        new_user = User(name=stu_name, email=stu_email, ...)
        db_session.add(new_user)
        db_session.flush()
```
- `flush()` sends the INSERT to the database but doesn't commit yet
- This gives us `new_user.id` which we need for creating the profile

```
        stu_profile = StudentProfile(user_id=new_user.id, ...)
        db_session.add(stu_profile)
        db_session.commit()
```
- Creates the linked StudentProfile record
- `commit()` saves both the User and StudentProfile together

### Company registration route (lines 104–140)

Works the same way as student registration but creates a `RecruiterProfile` with
`approval_status="pending"`. The company has to wait for admin approval before
they can create drives.

### Logout route (lines 143–147)

```
@app.route("/logout")
def logout():
    session.clear()
```
- `session.clear()` removes all stored session data (user_id, role, etc.)
- The user is no longer logged in

### Admin dashboard route (lines 150–210)

```
@app.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_dashboard():
```
- Protected by two decorators — must be logged in AND must be admin

```
    num_students = db_session.query(StudentProfile).count()
    num_companies = db_session.query(RecruiterProfile).count()
```
- `.count()` returns the total number of rows in each table
- These numbers are shown on the summary cards

```
    pending_companies = db_session.query(RecruiterProfile).filter_by(approval_status="pending").all()
    pending_drives = db_session.query(JobDrive).filter_by(status="pending").all()
    approved_drives = db_session.query(JobDrive).filter_by(status="approved").all()
```
- Three separate queries to get pending companies, pending drives, and approved drives
- `filter_by()` adds a WHERE clause
- `.all()` returns a list of all matching rows

```
    search_q = request.args.get("q", "").strip()
    search_type = request.args.get("type", "")
```
- `request.args` reads query parameters from the URL (e.g. `?q=John&type=student`)
- This is for the search feature on the admin dashboard

```
    if search_q:
        if search_type == "student":
            search_results = db_session.query(StudentProfile).filter(
                StudentProfile.name.ilike(f"%{search_q}%") | ...
            ).all()
```
- `ilike` — case-insensitive LIKE query, `%` is a wildcard
- `%John%` matches "John", "john doe", "Ajohnson", etc.

```
    eligibility_filter = request.args.get("eligibility", "").strip()
    if eligibility_filter:
        filtered_drives = db_session.query(JobDrive).filter(
            JobDrive.eligibility.ilike(f"%{eligibility_filter}%")
        ).all()
```
- Filters drives by eligibility text (e.g. "CGPA >= 7")

### Admin approval routes (lines 213–258)

```
@app.route("/admin/approve-company/<int:cid>")
def approve_company(cid):
    rec = db_session.query(RecruiterProfile).get(cid)
    if rec:
        rec.approval_status = "approved"
        db_session.commit()
```
- `<int:cid>` — Flask extracts the company ID from the URL
- `.get(cid)` fetches a row by primary key
- Changes `approval_status` to `"approved"` and saves

The reject, blacklist, and activate routes work the same way — they change
a status field and commit.

### Admin drive details route (lines 272–284)

```
@app.route("/admin/drive-details/<int:did>")
def admin_drive_details(did):
    drv = db_session.query(JobDrive).get(did)
    apps = db_session.query(DriveApplication).filter_by(drive_id=drv.id).all()
```
- Fetches a specific drive and all its applications
- Admin can see every applicant, their CGPA, and current status
- This lets admin monitor the full recruitment process

### Company routes (lines 302–390)

**Dashboard** — Shows all drives created by the logged-in company:
```
    curr_user = db_session.query(User).get(session["user_id"])
    profile = curr_user.recruiter_profile
    my_drives = db_session.query(JobDrive).filter_by(company_id=profile.id).all()
```
- Gets the current user from session, then their recruiter profile, then their drives

**Create drive** — Only works if the company is approved:
```
    if not profile or profile.approval_status != "approved":
        flash("Your company must be approved...", "warning")
        return redirect(url_for("company_dashboard"))
```
- This enforces the rule: only approved companies can create drives

**Edit / Delete drive** — Checks ownership:
```
    if not drv or drv.company_id != profile.id:
        flash("Drive not found or not yours.", "danger")
```
- A company can only edit/delete their own drives

**View applicants** — Shows all students who applied to a specific drive

**Update application status** — Changes an application from "applied" to
"shortlisted", "selected", or "rejected":
```
    new_status = request.form.get("status", "applied")
    app_record.status = new_status
    db_session.commit()
```

### Student routes (lines 393–465)

**Dashboard** — Shows approved drives and recent applications:
```
    available_drives = db_session.query(JobDrive).filter_by(status="approved").all()
```
- Only drives with `status="approved"` are shown to students

**Apply for drive** — Creates a new application with duplicate check:
```
    already_applied = db_session.query(DriveApplication).filter_by(
        student_id=profile.id, drive_id=drv.id
    ).first()
    if already_applied:
        flash("You already applied for this drive.", "warning")
```
- Checks if this student already applied to this drive
- If yes, shows a warning and doesn't create a duplicate

```
    new_app = DriveApplication(
        student_id=profile.id,
        drive_id=drv.id,
        application_date=datetime.utcnow(),
        status="applied",
    )
    db_session.add(new_app)
    db_session.commit()
```
- Creates the application record and saves it

**Profile update** — Student can change name, CGPA, and resume:
```
    profile.name = request.form.get("name", profile.name).strip()
    curr_user.name = profile.name
    curr_user.email = profile.email
    db_session.commit()
```
- Updates both the StudentProfile and the User record

### App entry point (lines 468–471)

```
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
```
- `__name__ == "__main__"` runs only when you execute `python app.py` directly
- `init_db()` creates tables and seeds admin user
- `debug=True` enables auto-reload (code changes restart the server) and
  shows detailed error pages

---

## 4. Templates — How the HTML Works

### base.html — Shared Layout

Every other template extends this file using `{% extends "base.html" %}`.

Key parts:
- **Navbar** — dark background, shows different links based on `session.role`
- **Sidebar** — only visible when logged in, shows role-specific quick links
- **Flash messages** — `get_flashed_messages(with_categories=true)` shows
  success/error messages from Flask's `flash()` function
- **Content block** — `{% block content %}{% endblock %}` is where each page
  inserts its own content
- **Footer** — "Developed as part of MAD-1 Project"

### login.html

- Simple form with email and password fields
- Uses `col-md-5 mx-auto` for alignment (not perfectly centered)
- POST to `/login` — Flask's login route processes it

### register_student.html

- Dual-purpose: used for registration AND profile editing
- `{% if edit %}` checks if we're editing (passed from the route)
- When editing, email field is `readonly` and password field is hidden
- POST goes to either `/register/student` or `/student/profile`

### register_company.html

- Fields: contact person, email, password, company name, HR contact, website
- POST to `/register/company`

### admin_dashboard.html

- **Summary cards** — uses Bootstrap card component with `text-bg-dark`
- **Search form** — sends GET request to same URL with `?q=...&type=...`
- **Eligibility filter** — separate form for filtering drives by eligibility text
- **Pending tables** — show companies and drives waiting for approval with
  Approve/Reject buttons (these are just links to the approve/reject routes)
- **Approved drives table** — shows applicant count using `d.applications|length`
  and a "View" link to the drive details page
- **All students/companies** — tables with blacklist/activate actions

### admin_drive_details.html

- Shows full info about one drive (title, company, eligibility, deadline)
- Lists all applicants with their name, email, CGPA, and application status
- Admin can monitor but not change statuses (that's the company's job)

### student_dashboard.html (Student Portal)

- Shows profile info (name, CGPA, email)
- Table of available drives with "Apply" button (POST form)
- Table of recent applications with status badges (color-coded)

### company_dashboard.html (Recruiter Panel)

- Shows company profile info and approval status
- Alert message if pending/rejected
- "Post New Drive" button (only visible if approved)
- Table of all drives with Edit, Delete, and View Applicants buttons

### create_drive.html

- Dual-purpose: create or edit a drive
- `{% if edit %}` fills in existing values
- Date picker for deadline
- POST to either `/company/create-drive` or `/company/edit-drive/<id>`

### apply_drive.html

- Dual-purpose template:
  1. When `drives` is passed — shows browse/apply view with eligibility filter
  2. When `history=True` — shows application history
- Each drive shows applicant count using `d.applications|length`
- Apply button is a POST form (prevents accidental double-clicks)

### view_applications.html

- Company view of applicants for a specific drive
- Shows student name, email, CGPA, applied date, current status
- Inline form with dropdown to update status (Applied → Shortlisted → Selected/Rejected)

---

## 5. style.css — Custom Styles

```
body { background-color: #f8f9fa; }
```
- Light grey background (Bootstrap's grey-100)

```
.sidebar {
    background-color: #e9ecef;
    min-height: calc(100vh - 120px);
    border-right: 1px solid #ccc;
}
```
- Sidebar takes up the left side, stretches to near-full viewport height
- Slightly darker grey than the body

```
.main-content { padding: 20px 30px; }
.table { font-size: 0.9rem; }
```
- Main content area has padding
- Tables use slightly smaller text for readability

---

## 6. How to Run the Application

### Prerequisites
```
pip install flask sqlalchemy werkzeug
```

### Starting the app
```
cd placement_portal
python app.py
```
This will:
1. Create the `placement.db` SQLite database file
2. Create all tables (users, recruiter_profiles, student_profiles, job_drives, drive_applications)
3. Create the default admin user: `placement_admin@college.edu` / `admin123`
4. Start the Flask development server on `http://127.0.0.1:5000`

### Testing the full flow
1. Open `http://127.0.0.1:5000` in browser
2. Log in as admin → approve companies and drives
3. Register a company → create a drive → wait for admin approval
4. Register a student → browse approved drives → apply
5. Log in as company → view applicants → update statuses
6. Log in as admin → view drive details with applicant counts

---

## 7. Key Rules Enforced by the Code

| Rule | Where it's enforced |
|------|-------------------|
| No duplicate applications | `apply_for_drive()` checks existing application before creating |
| Only approved companies create drives | `create_drive()` checks `profile.approval_status` |
| Only approved drives visible to students | Queries filter by `status="approved"` |
| Application history stored | DriveApplication records are never deleted (except when drive is deleted) |
| Blacklisted users can't log in | `login()` checks `found_user.status` |
| Companies can only edit own drives | `edit_drive()` checks `drv.company_id != profile.id` |
| Admin can't blacklist other admins | `blacklist_user()` checks `usr.role != "admin"` |

---

## 8. Extra Features (Bonus)

1. **Applicant count per drive** — shown in student dashboard, browse drives, company dashboard, and admin approved drives table
2. **Eligibility filter** — students and admin can filter drives by eligibility text
3. **Admin drive detail view** — admin can click into any approved drive to see full applicant list with CGPAs and statuses
4. **Left sidebar navigation** — role-specific quick links for easy navigation
5. **Search** — admin can search students by name/ID and companies by name
