from datetime import datetime, timedelta
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, jsonify, g)
from flask_login import (LoginManager, UserMixin, login_user,
                         login_required, logout_user, current_user)
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector, os
import click
from werkzeug.security import generate_password_hash
import os, pathlib
from flask import send_from_directory

BASE_DIR = pathlib.Path(__file__).resolve().parent
REC_DIR = BASE_DIR / 'static' / 'recordings'
REC_DIR.mkdir(parents=True, exist_ok=True)
# ─── app / db config ────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-key'

DB_CFG = dict(
    host = 'localhost',
    user = 'root',
    password = 'Siraj@2003',
    database = 'experiment_db',
)

# ─── connection helpers ─────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = mysql.connector.connect(**DB_CFG)
    return g.db

@app.teardown_appcontext
def close_db(exc):
    if db := g.pop('db', None):
        db.close()

def q(sql, params=(), one=False, commit=False):
    """helper → fetch list[dict]  |  single dict if one=True  |  commit only"""
    cur = get_db().cursor(dictionary=True)
    cur.execute(sql, params)
    if commit:
        get_db().commit()
        cur.close()
        return
    res = cur.fetchone() if one else cur.fetchall()
    cur.close()
    return res

# ─── lightweight User object for Flask-Login ────────────────────
class User(UserMixin):
    def __init__(self, row):   # row is a dict from DB
        self.id = row['id']
        self.name = row['name']
        self.email = row['email']
        self.role = row['role']
        self.teacher_id = row['teacher_id']
        self.time_limit = row['time_limit']

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(uid):
    row = q("SELECT * FROM users WHERE id=%s", (uid,), one=True)
    return User(row) if row else None

# ─── role checks ────────────────────────────────────────────────
def is_admin():   return current_user.is_authenticated and current_user.role == 'admin'
def is_teacher(): return current_user.is_authenticated and current_user.role == 'teacher'
def is_student(): return current_user.is_authenticated and current_user.role == 'student'

# ─── AUTH routes ────────────────────────────────────────────────
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, pwd = request.form['email'], request.form['password']
        row = q("SELECT * FROM users WHERE email=%s", (email,), one=True)
        if row and check_password_hash(row['password'], pwd):
            login_user(User(row))
            if is_admin():   return redirect(url_for('admin_dashboard'))
            if is_teacher(): return redirect(url_for('teacher_dashboard'))
            # student: open a session
            limit = q("SELECT time_limit FROM users WHERE id=%s",
                      (row['teacher_id'],), one=True)['time_limit'] \
                    if row['teacher_id'] else 60
            q("""INSERT INTO sessions(student_id, time_limit) VALUES (%s,%s)""",
              (row['id'], limit), commit=True)
            sid = q("SELECT LAST_INSERT_ID() id", one=True)['id']
            return redirect(url_for('student_dashboard', sid=sid))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/upload_chunk/<int:sid>', methods=['POST'])
@login_required
def upload_chunk(sid):
    """
    Receives multipart/form-data with one field named 'chunk'.
    Appends to   static/recordings/session_<sid>.webm
    """
    # Only the session owner may upload blobs
    sess = q("SELECT student_id, active FROM sessions WHERE id=%s", (sid,), one=True)
    if not sess or sess['student_id'] != current_user.id or not sess['active']:
        return "Forbidden", 403

    file = request.files.get('chunk')
    if not file:
        return "No chunk", 400

    rec_path = REC_DIR / f"session_{sid}.webm"
    # open(...,'ab') = append-binary
    with open(rec_path, 'ab') as f:
        f.write(file.read())

    return {"ok": True}

@app.route('/recordings/<int:sid>')
@login_required
def recordings(sid):
    # teachers OR the student who owns it:
    row = q("SELECT student_id FROM sessions WHERE id=%s", (sid,), one=True)
    if not row:
        return "Not found", 404
    if current_user.role not in ('teacher', 'admin') and current_user.id != row['student_id']:
        return "Forbidden", 403
    return send_from_directory(REC_DIR, f"session_{sid}.webm")

@app.context_processor
def inject_util():
    def recording_exists(sid):
        return (REC_DIR / f"session_{sid}.webm").exists()
    return dict(recording_exists=recording_exists)

@app.route('/logout', endpoint='logout')
@login_required
def logout():
    """
    Works for admin & teacher dashboards.
    Students are still logged out through the
    existing  POST  /logout/<sid>  form (they must
    submit their summary), so we leave that flow intact.
    """
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/logout/<int:sid>', methods=['POST'])
@login_required
def logout_(sid):
    # verify session belongs to student & is active
    sess = q("SELECT * FROM sessions WHERE id=%s AND student_id=%s AND active=1",
             (sid, current_user.id), one=True)
    if not sess:  return "Forbidden", 403
    q("""UPDATE sessions SET logout_at=%s, summary=%s, active=0
         WHERE id=%s""",
      (datetime.utcnow(), request.form['summary'], sid), commit=True)
    logout_user()
    flash('Logged out. Good job!', 'success')
    return redirect(url_for('login'))

@app.route('/auto_logout/<int:sid>', methods=['POST'])
@login_required
def auto_logout(sid):
    q("""UPDATE sessions SET logout_at=%s, summary=%s, active=0
         WHERE id=%s AND student_id=%s AND active=1""",
      (datetime.utcnow(), '(auto logout – no summary)', sid, current_user.id),
      commit=True)
    logout_user()
    return jsonify(ok=True)

# ─── STUDENT ────────────────────────────────────────────────────
@app.route('/student/<int:sid>')
@login_required
def student_dashboard(sid):
    if not is_student(): return "Forbidden", 403
    sess = q("SELECT * FROM sessions WHERE id=%s", (sid,), one=True)
    if not sess or sess['student_id'] != current_user.id: return "Forbidden", 403
    deadline = sess['login_at'] + timedelta(minutes=sess['time_limit'])
    return render_template('student_dashboard.html',
                           user=current_user, sess=sess, deadline=deadline)

# ─── TEACHER ────────────────────────────────────────────────────
@app.route('/teacher')
@login_required
def teacher_dashboard():
    if not is_teacher(): return "Forbidden", 403
    students = q("SELECT * FROM users WHERE teacher_id=%s", (current_user.id,))
    sid_list = [str(s['id']) for s in students] or ['0']
    sessions = q(f"""SELECT * FROM sessions
                     WHERE student_id IN ({','.join(sid_list)})
                     ORDER BY login_at DESC""")
    return render_template('teacher_dashboard.html',
                           students=students, sessions=sessions)

@app.route('/teacher/set_time', methods=['POST'])
@login_required
def set_time():
    if not is_teacher(): return "Forbidden", 403
    new = int(request.form['limit'])
    q("UPDATE users SET time_limit=%s WHERE id=%s", (new, current_user.id), commit=True)
    flash('Default session time updated.', 'success')
    return redirect(url_for('teacher_dashboard'))

# ─── ADMIN  ────────────────────────────────────────────────────
@app.route('/admin')
@login_required
def admin_dashboard():
    if not is_admin(): return "Forbidden", 403
    users = q("SELECT * FROM users")
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/add', methods=['GET', 'POST'])
@login_required
def admin_add():
    if not is_admin(): return "Forbidden", 403
    if request.method == 'POST':
        h = generate_password_hash(request.form['password'])
        vals = (request.form['name'], request.form['email'],
                h, request.form['role'],
                request.form.get('teacher_id') or None)
        q("""INSERT INTO users(name,email,password,role,teacher_id)
             VALUES(%s,%s,%s,%s,%s)""", vals, commit=True)
        flash('User added.', 'success')
        return redirect(url_for('admin_dashboard'))
    teachers = q("SELECT id,name FROM users WHERE role='teacher'")
    return render_template('admin_add.html', teachers=teachers)

@app.route('/admin/delete/<int:uid>', methods=['POST'])
@login_required
def admin_delete(uid):
    if not is_admin() or uid == current_user.id: return "Forbidden", 403
    q("DELETE FROM users WHERE id=%s", (uid,), commit=True)
    flash('User deleted.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/assign', methods=['POST'])
@login_required
def admin_assign():
    if not is_admin(): return "Forbidden", 403
    q("UPDATE users SET teacher_id=%s WHERE id=%s",
      (request.form['teacher'], request.form['student']), commit=True)
    flash('Student assigned.', 'success')
    return redirect(url_for('admin_dashboard'))

# ─── CLI: initialise schema  ───────────────────────────────────
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users(
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(80) NOT NULL,
  email VARCHAR(120) NOT NULL UNIQUE,
  password VARCHAR(256) NOT NULL,
  role ENUM('admin','teacher','student') DEFAULT 'student',
  teacher_id INT NULL,
  time_limit INT DEFAULT 60,
  FOREIGN KEY (teacher_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS sessions(
  id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  login_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  logout_at DATETIME NULL,
  summary TEXT,
  time_limit INT,
  active TINYINT(1) DEFAULT 1,
  FOREIGN KEY (student_id) REFERENCES users(id)
);
"""

@app.cli.command('initdb')
def initdb():
    """flask --app app.py initdb"""
    for stmt in SCHEMA_SQL.strip().split(';')[:-1]:
        q(stmt, commit=True)
    print('✔ Tables created (or already present)')

@app.cli.command('create-admin')
@click.option('--name',     prompt='Admin name',
              help='Full name for the admin account')
@click.option('--email',    prompt='Email',
              help='Login email (must be unique)')
@click.option('--password', prompt=True, hide_input=True,
              confirmation_prompt=True,
              help='Password (will be hashed)')
def create_admin(name, email, password):
    """flask --app app.py create-admin --name ... --email ..."""
    # Does the email already exist?
    if q("SELECT 1 FROM users WHERE email=%s", (email,), one=True):
        click.echo(f'✖ A user with email {email} already exists.')
        return

    h = generate_password_hash(password)
    q("""INSERT INTO users(name,email,password,role)
         VALUES(%s,%s,%s,'admin')""",
      (name, email, h), commit=True)
    uid = q("SELECT LAST_INSERT_ID() id", one=True)['id']
    click.echo(f'✔ Admin #{uid} created: {name} <{email}>')
# ─── main ──────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True)
