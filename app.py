import os
import re
import sqlite3
import secrets
from functools import wraps
from flask import Flask, request, redirect, url_for, session, flash, jsonify, abort, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash

# Single-file Campus Skill Exchange demo.
# A separate database filename avoids conflicts with older project schemas.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "campus_skill_exchange_final.db")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-key-before-deployment")


def db():
    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        bio TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        kind TEXT NOT NULL CHECK(kind IN ('Teach','Learn')),
        category TEXT NOT NULL DEFAULT 'Programming',
        description TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS exchange_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        learner_id INTEGER NOT NULL REFERENCES students(id),
        mentor_id INTEGER NOT NULL REFERENCES students(id),
        skill_id INTEGER NOT NULL REFERENCES skills(id),
        note TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'Pending',
        room_code TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(learner_id, skill_id)
    );
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER NOT NULL REFERENCES exchange_requests(id) ON DELETE CASCADE,
        sender_id INTEGER NOT NULL REFERENCES students(id),
        body TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    con.commit()
    con.close()


def seed_demo():
    con = db()
    demos = [
        ("Aadhya Raman", "python_mentor@demo.com", "I enjoy Python, debugging and building beginner projects."),
        ("Kavin Raj", "web_mentor@demo.com", "I enjoy building websites with HTML, CSS, JavaScript and Flask."),
        ("Arjun Kumar", "java_mentor@demo.com", "I can help with Java fundamentals and object-oriented programming."),
        ("Nila Priya", "design_mentor@demo.com", "I like designing interfaces and practising UI/UX with Figma."),
        ("Rithik S", "database_mentor@demo.com", "I can help with SQL, SQLite and database design."),
        ("Meera Krish", "data_mentor@demo.com", "I am interested in data analysis and beginner machine learning."),
        ("Monica Demo", "monica.demo@demo.com", "Student account for testing requests, messaging and video calls.")
    ]
    for name, email, bio in demos:
        con.execute("""
            INSERT INTO students(name, email, password, bio)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                name = excluded.name,
                bio = excluded.bio
        """, (name, email, generate_password_hash("Demo123!"), bio))
    con.commit()
    ids = {r["email"]: r["id"] for r in con.execute(
        "SELECT id,email FROM students WHERE email LIKE '%@demo.com'"
    ).fetchall()}
    skills = [
        ("python_mentor@demo.com","Python","Teach","Programming","Python basics, loops, functions and mini projects."),
        ("python_mentor@demo.com","Problem Solving","Teach","Programming","Practise coding problems and logical thinking."),
        ("web_mentor@demo.com","Web Development","Teach","Web Development","Build responsive websites with HTML, CSS and JavaScript."),
        ("web_mentor@demo.com","Flask","Teach","Web Development","Create simple Python web applications."),
        ("java_mentor@demo.com","Java","Teach","Programming","Classes, objects, inheritance and Java basics."),
        ("design_mentor@demo.com","UI/UX Design","Teach","Design","Learn interface design and user experience basics."),
        ("database_mentor@demo.com","SQL","Teach","Database","Queries, joins, grouping and database concepts."),
        ("data_mentor@demo.com","Data Science","Teach","Data Science","Intro to data analysis and beginner ML concepts."),
        ("database_mentor@demo.com","Python","Learn","Programming","Wants to learn Python automation.")
    ]
    for email, name, kind, category, description in skills:
        con.execute("""INSERT INTO skills(student_id,name,kind,category,description)
                       SELECT ?,?,?,?,?
                       WHERE NOT EXISTS(SELECT 1 FROM skills WHERE student_id=? AND name=?)""",
                    (ids[email], name, kind, category, description, ids[email], name))
    con.commit()

    # A ready-to-use student account with an accepted Python chat
    # and a pending Java request, so features can be tested immediately.
    learner_id = ids["monica.demo@demo.com"]
    python_mentor_id = ids["python_mentor@demo.com"]
    java_mentor_id = ids["java_mentor@demo.com"]

    python_skill = con.execute(
        "SELECT id FROM skills WHERE student_id=? AND name='Python'",
        (python_mentor_id,)
    ).fetchone()
    java_skill = con.execute(
        "SELECT id FROM skills WHERE student_id=? AND name='Java'",
        (java_mentor_id,)
    ).fetchone()

    if python_skill:
        con.execute("""
            INSERT OR IGNORE INTO exchange_requests
                (learner_id, mentor_id, skill_id, note, status, room_code)
            VALUES (?, ?, ?, ?, 'Accepted', ?)
        """, (
            learner_id, python_mentor_id, python_skill["id"],
            "Hi Aadhya! I'd like to practise Python.",
            "skillbridge-python-demo-room"
        ))

        accepted = con.execute("""
            SELECT id FROM exchange_requests
            WHERE learner_id=? AND skill_id=?
        """, (learner_id, python_skill["id"])).fetchone()

        if accepted:
            con.execute("""
                INSERT INTO messages(request_id, sender_id, body)
                SELECT ?, ?, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM messages WHERE request_id=? AND body=?
                )
            """, (
                accepted["id"], python_mentor_id,
                "Hi Monica! Welcome. We can practise Python together.",
                accepted["id"], "Hi Monica! Welcome. We can practise Python together."
            ))
            con.execute("""
                INSERT INTO messages(request_id, sender_id, body)
                SELECT ?, ?, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM messages WHERE request_id=? AND body=?
                )
            """, (
                accepted["id"], learner_id,
                "Thank you! I want to practise Python basics.",
                accepted["id"], "Thank you! I want to practise Python basics."
            ))

    if java_skill:
        con.execute("""
            INSERT OR IGNORE INTO exchange_requests
                (learner_id, mentor_id, skill_id, note, status, room_code)
            VALUES (?, ?, ?, ?, 'Pending', ?)
        """, (
            learner_id, java_mentor_id, java_skill["id"],
            "Hi Arjun! I'd like to learn Java.",
            "skillbridge-java-demo-room"
        ))

    con.commit()
    con.close()


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("uid"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped


def current_user(con=None):
    own = con is None
    con = con or db()
    user = con.execute("SELECT * FROM students WHERE id=?", (session.get("uid"),)).fetchone()
    if own:
        con.close()
    return user


def get_exchange(con, rid, uid):
    return con.execute("""SELECT * FROM exchange_requests
        WHERE id=? AND (learner_id=? OR mentor_id=?)""", (rid, uid, uid)).fetchone()


BASE = r"""
<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title or 'Campus Skill Exchange' }}</title>
<style>
:root{--purple:#6543c5;--ink:#202044;--muted:#77758c;--bg:#f7f6fc;--line:#e7e2f4;--white:#fff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);font:16px/1.5 Arial,sans-serif;color:var(--ink)}
a{color:var(--purple);text-decoration:none}button,.btn{border:0;background:var(--purple);color:#fff;border-radius:10px;padding:11px 16px;cursor:pointer;font-weight:700;display:inline-block}
.btn.secondary,button.secondary{background:#eee9fb;color:var(--purple)}button.danger{background:#c83e55}
input,textarea,select{width:100%;padding:12px;border:1px solid #dcd5f0;border-radius:10px;font:inherit;background:#fff;color:var(--ink)}
textarea{min-height:95px;resize:vertical}label{display:block;font-weight:700;margin:12px 0 6px}
header{height:68px;background:#fff;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 5%;position:sticky;top:0;z-index:2}
.brand{font-weight:800;font-size:21px;color:var(--ink)}nav{display:flex;gap:18px;align-items:center;flex-wrap:wrap}
.layout{display:grid;grid-template-columns:225px minmax(0,1fr);gap:24px;max-width:1280px;margin:25px auto;padding:0 20px}
aside,.panel,.card{background:#fff;border:1px solid var(--line);border-radius:18px}
aside{padding:18px;height:max-content;position:sticky;top:88px}aside a{display:block;padding:10px 12px;border-radius:9px;color:var(--ink);margin:4px 0}aside a:hover{background:#f0ebff;color:var(--purple)}
main{min-width:0}.panel{padding:26px;margin-bottom:20px}.hero{padding:36px;background:linear-gradient(120deg,#fff,#f0eaff)}
h1{font-size:32px;line-height:1.2;margin:0 0 12px}h2{font-size:23px;margin:0 0 16px}h3{margin:0 0 8px}.muted{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:15px}
.card{padding:19px}.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}.row>*{flex:1}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.tag{display:inline-block;background:#f0ebff;color:#6543c5;border-radius:20px;padding:4px 10px;font-size:13px;font-weight:700}.status{font-weight:700}.flash{padding:12px 15px;border-radius:10px;background:#eee9fb;margin-bottom:12px}.flash.error{background:#ffe9ed;color:#9b1c35}.flash.success{background:#e7f8ee;color:#176c3b}
.list{display:grid;gap:12px}.split{display:grid;grid-template-columns:1fr 1fr;gap:18px}.message{padding:11px 14px;border-radius:14px;background:#f0edfa;max-width:85%;margin:8px 0}.message.mine{background:#dfd4ff;margin-left:auto}.small{font-size:13px}.empty{padding:25px;text-align:center;color:var(--muted)}
footer{text-align:center;color:var(--muted);padding:30px}
@media(max-width:780px){.layout{grid-template-columns:1fr;margin-top:12px}aside{position:static}.split{grid-template-columns:1fr}header{height:auto;padding:14px 5%;gap:12px;align-items:flex-start;flex-direction:column}nav{gap:10px}.panel{padding:18px}h1{font-size:27px}}
</style></head><body>
<header><a class="brand" href="{{ url_for('home') }}">🎓 SkillBridge</a>
<nav><a href="{{ url_for('skills') }}">Find Mentors</a><a href="{{ url_for('directory') }}">Students</a>
{% if session.get('uid') %}<a href="{{ url_for('dashboard') }}">Dashboard</a><a href="{{ url_for('messages') }}">Messages</a>
<form method="post" action="{{ url_for('logout') }}" style="margin:0"><button class="secondary" type="submit">Log out</button></form>
{% else %}<a href="{{ url_for('login') }}">Log in</a><a class="btn" href="{{ url_for('register') }}">Join now</a>{% endif %}</nav></header>
<div class="layout"><aside><h3>Menu</h3><a href="{{ url_for('dashboard') }}">🏠 Dashboard</a><a href="{{ url_for('skills') }}">🔎 Find mentors</a><a href="{{ url_for('my_skills') }}">✨ My skills</a><a href="{{ url_for('requests_page') }}">📨 Exchange requests</a><a href="{{ url_for('messages') }}">💬 Messages</a><a href="{{ url_for('profile') }}">👤 My profile</a><hr style="border:0;border-top:1px solid var(--line)"><p class="small muted">Demo accounts use password <b>Demo123!</b></p></aside>
<main>{% for category,message in get_flashed_messages(with_categories=true) %}<div class="flash {{ category }}">{{ message }}</div>{% endfor %}{{ body|safe }}</main></div><footer>SkillBridge · Learn together, grow together</footer></body></html>
"""


def page(body, title="Campus Skill Exchange", **context):
    inner = render_template_string(body, **context)
    return render_template_string(BASE, body=inner, title=title)


HOME = r"""
<section class="panel hero"><span class="tag">STUDENT-TO-STUDENT LEARNING</span><h1>Share what you know.<br>Learn what you love.</h1>
<p class="muted">Find classmates who can teach a skill you want to learn, exchange knowledge, chat and meet online.</p>
<div class="actions"><a class="btn" href="{{ url_for('skills') }}">Explore mentors</a><a class="btn secondary" href="{{ url_for('register') }}">Create free account</a></div></section>
<section class="panel"><h2>Popular skills</h2><div class="grid">{% for s in skills %}<article class="card"><span class="tag">{{ s['category'] }}</span><h3 style="margin-top:10px">{{ s['name'] }}</h3><p class="muted">{{ s['description'] }}</p><p>Mentor: <b>{{ s['student_name'] }}</b></p><a class="btn" href="{{ url_for('skills') }}">View mentor</a></article>{% endfor %}</div></section>
<section class="panel"><h2>How it works</h2><div class="grid"><div class="card"><h3>1. Discover</h3><p>Search for a skill and find a student mentor.</p></div><div class="card"><h3>2. Connect</h3><p>Send a request and chat once it is accepted.</p></div><div class="card"><h3>3. Learn</h3><p>Schedule a video call and practise together.</p></div></div></section>
"""

REGISTER = r"""
<section class="panel" style="max-width:600px;margin:auto"><h1>Create your account</h1><p class="muted">Join the student learning community.</p>
<form method="post"><label>Full name</label><input name="name" required maxlength="80"><label>Email</label><input name="email" type="email" required><label>Password</label><input name="password" type="password" minlength="6" required><button style="margin-top:18px">Register</button></form><p>Already registered? <a href="{{ url_for('login') }}">Log in</a></p></section>
"""
LOGIN = r"""
<section class="panel" style="max-width:600px;margin:auto"><h1>Welcome back</h1><p class="muted">Log in to continue learning.</p>
<form method="post"><label>Email</label><input name="email" type="email" required><label>Password</label><input name="password" type="password" required><button style="margin-top:18px">Log in</button></form><p>New here? <a href="{{ url_for('register') }}">Create an account</a></p>
<div class="card"><b>Demo logins (password: Demo123!)</b><p class="small">Student: monica.demo@demo.com</p><p class="small">Python mentor: python_mentor@demo.com</p><p class="small">Java mentor: java_mentor@demo.com</p></div></section>
"""
DASH = r"""
<section class="panel hero"><p class="muted">YOUR LEARNING SPACE</p><h1>Hello, {{ user['name'] }} 👋</h1><p>Discover mentors, share your skills, and keep your learning conversations together.</p><div class="actions"><a class="btn" href="{{ url_for('skills') }}">Find a mentor</a><a class="btn secondary" href="{{ url_for('my_skills') }}">Manage my skills</a></div></section>
<div class="grid"><div class="card"><p class="muted">Students</p><h2>{{ student_count }}</h2></div><div class="card"><p class="muted">My skills</p><h2>{{ skill_count }}</h2></div><div class="card"><p class="muted">My requests</p><h2>{{ request_count }}</h2></div></div>
<section class="panel" style="margin-top:20px"><h2>Quick start</h2><p>Demo mentors are already available. Search <b>Python</b>, <b>Web Development</b>, <b>Java</b>, <b>UI/UX</b>, or <b>SQL</b>.</p></section>
"""
SKILLS = r"""
<section class="panel"><h1>Find a student mentor</h1><p class="muted">Search real skill listings from the shared database.</p>
<form method="get" class="row"><input name="q" placeholder="Search Python, Java, design..." value="{{ q }}"><select name="category"><option value="All">All categories</option>{% for c in categories %}<option value="{{ c }}" {% if cat==c %}selected{% endif %}>{{ c }}</option>{% endfor %}</select><button>Search</button></form></section>
<section class="panel"><div class="grid">{% for s in skills %}<article class="card"><span class="tag">{{ s['category'] }}</span><h2 style="margin-top:10px">{{ s['name'] }}</h2><p>{{ s['description'] }}</p><p>Mentor: <b>{{ s['student_name'] }}</b></p><p class="muted small">{{ s['bio'] or 'Student mentor' }}</p>
{% if session.get('uid') and s['student_id'] != session.get('uid') %}<form method="post" action="{{ url_for('send_request', sid=s['id']) }}"><label>Message to mentor</label><textarea name="note" placeholder="Hi! I would like to learn this skill." maxlength="500"></textarea><button style="margin-top:10px">Request to learn</button></form>{% endif %}</article>{% else %}<div class="empty">No mentors found. Try another search or choose All categories.</div>{% endfor %}</div></section>
"""
MY_SKILLS = r"""
<section class="panel"><h1>My skills</h1><p class="muted">Add skills you can teach and skills you want to learn.</p>
<form method="post"><div class="row"><div><label>Skill name</label><input name="name" required placeholder="e.g. Python"></div><div><label>Type</label><select name="kind"><option>Teach</option><option>Learn</option></select></div><div><label>Category</label><select name="category">{% for c in categories %}<option>{{ c }}</option>{% endfor %}</select></div></div><label>Description</label><textarea name="description" placeholder="What can you teach or what do you want to learn?"></textarea><button style="margin-top:12px">Add skill</button></form></section>
<section class="panel"><h2>Your listed skills</h2><div class="grid">{% for s in skills %}<article class="card"><span class="tag">{{ s['kind'] }} · {{ s['category'] }}</span><h3 style="margin-top:8px">{{ s['name'] }}</h3><p>{{ s['description'] }}</p><form method="post" action="{{ url_for('delete_skill', sid=s['id']) }}"><button class="danger">Delete</button></form></article>{% else %}<p class="muted">You haven't added any skills yet.</p>{% endfor %}</div></section>
"""
REQUESTS = r"""
<section class="panel"><h1>Exchange requests</h1><p class="muted">Accept or reject incoming requests. Accepted requests unlock chat and video.</p><h2>Incoming</h2><div class="list">{% for r in incoming %}<article class="card"><h3>{{ r['skill_name'] }} · {{ r['learner_name'] }}</h3><p>{{ r['note'] }}</p><p class="status">Status: {{ r['status'] }}</p>{% if r['status']=='Pending' %}<div class="actions"><form method="post" action="{{ url_for('update_request', rid=r['id']) }}"><input type="hidden" name="status" value="Accepted"><button>Accept</button></form><form method="post" action="{{ url_for('update_request', rid=r['id']) }}"><input type="hidden" name="status" value="Rejected"><button class="danger">Reject</button></form></div>{% endif %}</article>{% else %}<p class="muted">No incoming requests.</p>{% endfor %}</div>
<hr style="border:0;border-top:1px solid var(--line);margin:24px 0"><h2>Sent by me</h2><div class="list">{% for r in outgoing %}<article class="card"><h3>{{ r['skill_name'] }} · {{ r['mentor_name'] }}</h3><p>{{ r['note'] }}</p><p class="status">Status: {{ r['status'] }}</p>{% if r['status']=='Accepted' %}<a class="btn" href="{{ url_for('chat', rid=r['id']) }}">Open chat</a><a class="btn secondary" href="{{ url_for('video', rid=r['id']) }}">Video call</a>{% endif %}</article>{% else %}<p class="muted">You haven't sent requests.</p>{% endfor %}</div></section>
"""
MESSAGES = r"""
<section class="panel"><h1>Messages</h1><p class="muted">Conversations are available after a mentor accepts your request.</p><div class="list">{% for r in chats %}<article class="card"><h3>{{ r['skill_name'] }} · {{ r['other_name'] }}</h3><p class="status">Accepted</p><div class="actions"><a class="btn" href="{{ url_for('chat', rid=r['id']) }}">Open chat</a><a class="btn secondary" href="{{ url_for('video', rid=r['id']) }}">Video call</a></div></article>{% else %}<div class="empty">No accepted conversations yet. Try the Python demo conversation or send a mentor request.</div>{% endfor %}</div></section>
"""
CHAT = r"""
<section class="panel"><div class="row"><div><h1>Chat with {{ other['name'] }}</h1><p class="muted">{{ exchange['skill_name'] }} · Accepted</p></div><div style="text-align:right"><a class="btn secondary" href="{{ url_for('video', rid=exchange['id']) }}">Start video call</a></div></div>
<div id="chatbox" style="background:#faf9ff;border:1px solid var(--line);border-radius:14px;padding:15px;min-height:250px;max-height:430px;overflow-y:auto">{% for m in messages %}<div class="message {% if m['sender_id']==session.get('uid') %}mine{% endif %}"><b>{{ m['sender_name'] }}</b><div>{{ m['body'] }}</div><div class="small muted">{{ m['created_at'] }}</div></div>{% endfor %}</div>
<form method="post" style="margin-top:14px"><label>Your message</label><div class="row"><input name="body" required maxlength="2000" placeholder="Type a message..."><button>Send</button></div></form></section>
<script>const box=document.getElementById('chatbox');box.scrollTop=box.scrollHeight;</script>
"""
PROFILE = r"""
<section class="panel" style="max-width:700px"><h1>My profile</h1><form method="post"><label>Name</label><input name="name" value="{{ user['name'] }}" required><label>Email</label><input value="{{ user['email'] }}" disabled><label>About me</label><textarea name="bio" maxlength="800">{{ user['bio'] }}</textarea><button style="margin-top:14px">Save profile</button></form></section>
"""
DIRECTORY = r"""
<section class="panel"><h1>Student directory</h1><div class="grid">{% for u in students %}<article class="card"><h3>{{ u['name'] }}</h3><p class="muted">{{ u['bio'] or 'Student community member' }}</p><p class="small">{{ u['skill_names'] or 'No skills listed yet' }}</p></article>{% endfor %}</div></section>
"""
VIDEO = r"""
<section class="panel"><h1>Video call</h1><p class="muted">Room for {{ exchange['skill_name'] }} with {{ other['name'] }}. Share the same room link with your partner.</p>
<div class="card"><p><b>Room link</b></p><input id="roomlink" readonly value="{{ meeting_url }}"><div class="actions"><button onclick="navigator.clipboard.writeText(document.getElementById('roomlink').value)">Copy room link</button><a class="btn secondary" target="_blank" rel="noopener" href="{{ meeting_url }}">Open video room</a></div></div>
<p class="muted small">Video calling uses Jitsi Meet, which requires internet access and camera/microphone permissions. For a real session, both people must open the same room link.</p></section>
"""
ERROR = r"""<section class="panel"><h1>Page not found</h1><p>{{ message }}</p><a class="btn" href="{{ url_for('home') }}">Return home</a></section>"""


@app.route("/")
def home():
    con = db()
    skills = con.execute("""SELECT s.*,u.name AS student_name FROM skills s
        JOIN students u ON u.id=s.student_id WHERE s.kind='Teach'
        ORDER BY s.id DESC LIMIT 8""").fetchall()
    con.close()
    return page(HOME, "Welcome · SkillBridge", skills=skills)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or len(password) < 6:
            flash("Enter your name, a valid email, and a password of at least 6 characters.", "error")
            return redirect(url_for("register"))
        con = db()
        try:
            con.execute("INSERT INTO students(name,email,password) VALUES(?,?,?)",
                        (name, email, generate_password_hash(password)))
            con.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "error")
        finally:
            con.close()
    return page(REGISTER, "Register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        con = db()
        user = con.execute("SELECT * FROM students WHERE email=?", (email,)).fetchone()
        con.close()
        if user and check_password_hash(user["password"], password):
            session.clear()
            session["uid"] = user["id"]
            session["name"] = user["name"]
            return redirect(url_for("dashboard"))
        flash("Incorrect email or password.", "error")
    return page(LOGIN, "Log in")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    con = db()
    user = current_user(con)
    student_count = con.execute("SELECT COUNT(*) n FROM students").fetchone()["n"]
    skill_count = con.execute("SELECT COUNT(*) n FROM skills WHERE student_id=?", (user["id"],)).fetchone()["n"]
    request_count = con.execute("SELECT COUNT(*) n FROM exchange_requests WHERE learner_id=? OR mentor_id=?", (user["id"], user["id"])).fetchone()["n"]
    con.close()
    return page(DASH, "Dashboard", user=user, student_count=student_count, skill_count=skill_count, request_count=request_count)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    con = db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        bio = request.form.get("bio", "").strip()
        if not name:
            con.close()
            flash("Name is required.", "error")
            return redirect(url_for("profile"))
        con.execute("UPDATE students SET name=?,bio=? WHERE id=?", (name, bio, session["uid"]))
        con.commit()
        session["name"] = name
        flash("Profile updated.", "success")
        return redirect(url_for("profile"))
    user = current_user(con)
    con.close()
    return page(PROFILE, "My profile", user=user)


CATEGORIES = ["Programming", "Web Development", "Design", "Database", "Data Science", "Other"]


@app.route("/skills")
@login_required
def skills():
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", "All")
    con = db()
    sql = """SELECT s.*,u.name AS student_name,u.bio FROM skills s
             JOIN students u ON u.id=s.student_id
             WHERE s.kind='Teach' AND s.student_id != ?"""
    args = [session["uid"]]
    if q:
        sql += " AND (s.name LIKE ? OR s.description LIKE ? OR u.name LIKE ?)"
        args.extend([f"%{q}%"] * 3)
    if cat in CATEGORIES:
        sql += " AND s.category=?"
        args.append(cat)
    sql += " ORDER BY s.id DESC"
    rows = con.execute(sql, args).fetchall()
    con.close()
    return page(SKILLS, "Find mentors", skills=rows, q=q, cat=cat, categories=CATEGORIES)


@app.route("/my-skills", methods=["GET", "POST"])
@login_required
def my_skills():
    con = db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        kind = request.form.get("kind", "Teach")
        category = request.form.get("category", "Programming")
        description = request.form.get("description", "").strip()
        if not name:
            con.close()
            flash("Skill name is required.", "error")
            return redirect(url_for("my_skills"))
        if kind not in ("Teach", "Learn"):
            kind = "Teach"
        if category not in CATEGORIES:
            category = "Other"
        con.execute("INSERT INTO skills(student_id,name,kind,category,description) VALUES(?,?,?,?,?)",
                    (session["uid"], name, kind, category, description))
        con.commit()
        con.close()
        flash("Skill added.", "success")
        return redirect(url_for("my_skills"))
    rows = con.execute("SELECT * FROM skills WHERE student_id=? ORDER BY id DESC", (session["uid"],)).fetchall()
    con.close()
    return page(MY_SKILLS, "My skills", skills=rows, categories=CATEGORIES)


@app.route("/my-skills/delete/<int:sid>", methods=["POST"])
@login_required
def delete_skill(sid):
    con = db()
    con.execute("DELETE FROM skills WHERE id=? AND student_id=?", (sid, session["uid"]))
    con.commit()
    con.close()
    flash("Skill deleted.", "success")
    return redirect(url_for("my_skills"))


@app.route("/directory")
def directory():
    con = db()
    students = con.execute("""SELECT u.id,u.name,u.bio,
        (SELECT GROUP_CONCAT(name, ', ') FROM skills WHERE student_id=u.id) AS skill_names
        FROM students u ORDER BY u.name""").fetchall()
    con.close()
    return page(DIRECTORY, "Students", students=students)


@app.route("/request/<int:sid>", methods=["POST"])
@login_required
def send_request(sid):
    note = request.form.get("note", "").strip()
    con = db()
    skill = con.execute("SELECT * FROM skills WHERE id=? AND kind='Teach'", (sid,)).fetchone()
    if not skill or skill["student_id"] == session["uid"]:
        con.close()
        flash("That mentor skill is unavailable.", "error")
        return redirect(url_for("skills"))
    existing = con.execute("""SELECT id FROM exchange_requests
        WHERE learner_id=? AND skill_id=? AND status IN ('Pending','Accepted')""",
        (session["uid"], sid)).fetchone()
    if existing:
        con.close()
        flash("You already have an active request for this skill.", "error")
        return redirect(url_for("requests_page"))
    con.execute("""INSERT INTO exchange_requests(learner_id,mentor_id,skill_id,note,status,room_code)
        VALUES(?,?,?,?,'Pending',?)""",
        (session["uid"], skill["student_id"], sid, note, "skillbridge-" + secrets.token_hex(8)))
    con.commit()
    con.close()
    flash("Request sent. The mentor can accept it from Exchange requests.", "success")
    return redirect(url_for("requests_page"))


@app.route("/requests")
@login_required
def requests_page():
    uid = session["uid"]
    con = db()
    incoming = con.execute("""SELECT r.*,s.name AS skill_name,u.name AS learner_name
        FROM exchange_requests r JOIN skills s ON s.id=r.skill_id
        JOIN students u ON u.id=r.learner_id WHERE r.mentor_id=? ORDER BY r.id DESC""", (uid,)).fetchall()
    outgoing = con.execute("""SELECT r.*,s.name AS skill_name,u.name AS mentor_name
        FROM exchange_requests r JOIN skills s ON s.id=r.skill_id
        JOIN students u ON u.id=r.mentor_id WHERE r.learner_id=? ORDER BY r.id DESC""", (uid,)).fetchall()
    con.close()
    return page(REQUESTS, "Exchange requests", incoming=incoming, outgoing=outgoing)


@app.route("/requests/<int:rid>/status", methods=["POST"])
@login_required
def update_request(rid):
    status = request.form.get("status")
    if status not in ("Accepted", "Rejected"):
        abort(400)
    con = db()
    item = con.execute("SELECT * FROM exchange_requests WHERE id=? AND mentor_id=? AND status='Pending'",
                       (rid, session["uid"])).fetchone()
    if not item:
        con.close()
        flash("Request not found or already handled.", "error")
        return redirect(url_for("requests_page"))
    con.execute("UPDATE exchange_requests SET status=? WHERE id=?", (status, rid))
    con.commit()
    con.close()
    flash("Request " + status.lower() + ".", "success")
    return redirect(url_for("requests_page"))


@app.route("/messages")
@login_required
def messages():
    uid = session["uid"]
    con = db()
    chats = con.execute("""SELECT r.*,s.name AS skill_name,
        CASE WHEN r.learner_id=? THEN mentor.name ELSE learner.name END AS other_name
        FROM exchange_requests r JOIN skills s ON s.id=r.skill_id
        JOIN students learner ON learner.id=r.learner_id
        JOIN students mentor ON mentor.id=r.mentor_id
        WHERE (r.learner_id=? OR r.mentor_id=?) AND r.status='Accepted'
        ORDER BY r.id DESC""", (uid, uid, uid)).fetchall()
    con.close()
    return page(MESSAGES, "Messages", chats=chats)


@app.route("/chat/<int:rid>", methods=["GET", "POST"])
@login_required
def chat(rid):
    uid = session["uid"]
    con = db()
    exchange = con.execute("""SELECT r.*,s.name AS skill_name FROM exchange_requests r
        JOIN skills s ON s.id=r.skill_id
        WHERE r.id=? AND (r.learner_id=? OR r.mentor_id=?) AND r.status='Accepted'""",
        (rid, uid, uid)).fetchone()
    if not exchange:
        con.close()
        abort(404)
    if request.method == "POST":
        body = request.form.get("body", "").strip()
        if body:
            con.execute("INSERT INTO messages(request_id,sender_id,body) VALUES(?,?,?)", (rid, uid, body[:2000]))
            con.commit()
        con.close()
        return redirect(url_for("chat", rid=rid))
    other_id = exchange["mentor_id"] if exchange["learner_id"] == uid else exchange["learner_id"]
    other = con.execute("SELECT * FROM students WHERE id=?", (other_id,)).fetchone()
    rows = con.execute("""SELECT m.*,u.name AS sender_name FROM messages m
        JOIN students u ON u.id=m.sender_id WHERE m.request_id=? ORDER BY m.id""", (rid,)).fetchall()
    con.close()
    return page(CHAT, "Chat", exchange=exchange, other=other, messages=rows)


@app.route("/video/<int:rid>")
@login_required
def video(rid):
    uid = session["uid"]
    con = db()
    exchange = con.execute("""SELECT r.*,s.name AS skill_name FROM exchange_requests r
        JOIN skills s ON s.id=r.skill_id WHERE r.id=?
        AND (r.learner_id=? OR r.mentor_id=?) AND r.status='Accepted'""", (rid, uid, uid)).fetchone()
    if not exchange:
        con.close()
        abort(404)
    other_id = exchange["mentor_id"] if exchange["learner_id"] == uid else exchange["learner_id"]
    other = con.execute("SELECT * FROM students WHERE id=?", (other_id,)).fetchone()
    room = exchange["room_code"]
    con.close()
    meeting_url = "https://meet.jit.si/" + room
    return page(VIDEO, "Video call", exchange=exchange, other=other, meeting_url=meeting_url)


@app.errorhandler(404)
def not_found(error):
    return page(ERROR, "Not found", message="That page or conversation could not be found."), 404


init_db()
seed_demo()

if __name__ == "__main__":
    app.run(debug=True)
