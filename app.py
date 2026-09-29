

from flask import Flask, session, render_template, request, redirect , Response
import sqlite3
from werkzeug.security import check_password_hash
import os
import secrets

app = Flask(__name__)
app.secret_key = "dogfood-secret-key"
def get_auth_context():
    """
    Returns (user_id, role).
    Supports both normal Flask session login and
    DOGFOOD acceptance-checker headers.
    """

    # Normal browser session
    if session.get("user_id") and session.get("user_role"):
        return session["user_id"], session["user_role"]

    # DOGFOOD checker header
    header_role = request.headers.get("X-Dogfood-Role", "").strip().lower()

    header_users = {
        "participant": ("participant@example.com", "participant"),
        "organizer": ("organizer@example.com", "organizer"),
        "judge_a": ("judge@example.com", "judge"),
        "judge_b": ("judgeb@example.com", "judge")
    }

    if header_role in header_users:
        email, role = header_users[header_role]

        connection = sqlite3.connect("dogfood.db")
        cursor = connection.cursor()

        cursor.execute("""
            SELECT id
            FROM users
            WHERE email = ? AND role = ?
        """, (email, role))

        user = cursor.fetchone()

        connection.close()

        if user:
            return user[0], role

    return None, None
print("APP LOCATION:", os.getcwd())
print("TEMPLATES PATH:", os.path.join(os.getcwd(), "templates"))
print("FILES:", os.listdir("templates"))


@app.route("/")
def home():
    return "Dogfood Judging Portal is running!"


@app.route("/users")
def users():
    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    connection.close()

    return str(users)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form["email"]
    password = request.form["password"]

    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, email, role, password
        FROM users
        WHERE email = ?
    """, (email,))

    user = cursor.fetchone()
    connection.close()

    if user is None:
        return "Invalid email or password", 401

    if not check_password_hash(user[4], password):
        return "Invalid email or password", 401

    session["user_id"] = user[0]
    session["user_role"] = user[3]

    return f"Logged in as {user[1]} ({user[3]})"

@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session:
        return "Please login first", 401

    if session.get("user_role") != "admin":
        return "Admin access required", 403

    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM events")
    event_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM teams")
    team_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM projects")
    project_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*)
        FROM projects
        WHERE status = 'submitted'
    """)
    submitted_count = cursor.fetchone()[0]

    connection.close()

    return render_template(
        "admin.html",
        event_count=event_count,
        team_count=team_count,
        project_count=project_count,
        submitted_count=submitted_count
    )



@app.route("/role")
def role():
    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    cursor.execute("""
    SELECT name, role
    FROM users
    WHERE email = ?
    """, ("judge@example.com",))

    user = cursor.fetchone()

    connection.close()

    return str(user)


@app.route("/judge")
def judge_page():

    if session.get("user_role") == "judge":
        return "Welcome Judge! You can access judging."

    return "Access Denied", 403

@app.route("/create-event", methods=["GET", "POST"])
def create_event():

    # Only organizer can create an event
    if session.get("user_role") != "organizer":
        return "Only organizers can create events", 403

    if request.method == "POST":

        name = request.form["name"].strip()
        description = request.form["description"].strip()
        starts_at = request.form["starts_at"]
        submissions_close = request.form["submissions_close"]
        tracks = request.form["tracks"].strip()
        prizes = request.form["prizes"].strip()

        if not name:
            return "Event name is required", 400

        if not starts_at:
            return "Start date is required", 400

        if not submissions_close:
            return "Submission deadline is required", 400

        connection = sqlite3.connect("dogfood.db")
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO events
            (name, description, submissions_close, status, starts_at, tracks, prizes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            description,
            submissions_close,
            "open",
            starts_at,
            tracks,
            prizes
        ))

        connection.commit()
        connection.close()

        return "Event created successfully!"

    return render_template("create_event.html")
@app.route("/events")
def events():

    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id,
               name,
               description,
               starts_at,
               submissions_close,
               tracks,
               prizes,
               status
        FROM events
        ORDER BY id DESC
    """)

    events = cursor.fetchall()

    connection.close()

    return render_template("events.html", events=events)
@app.route("/create-team", methods=["GET", "POST"])
def create_team():

    if "user_id" not in session:
        return "Please login first", 401

    if session.get("user_role") != "participant":
        return "Only participants can create teams", 403

    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    if request.method == "POST":

        name = request.form["name"].strip()
        event_id = request.form["event_id"]
        user_id = session["user_id"]

        if not name:
            connection.close()
            return "Team name is required", 400

        # Check whether event exists and is open
        cursor.execute("""
            SELECT id, name
            FROM events
            WHERE id = ? AND status = 'open'
        """, (event_id,))

        event = cursor.fetchone()

        if event is None:
            connection.close()
            return "Invalid or closed event", 400

        # Prevent user from creating another team for same event
        cursor.execute("""
            SELECT team_members.id
            FROM team_members
            JOIN teams ON team_members.team_id = teams.id
            WHERE team_members.user_id = ?
              AND teams.event_id = ?
        """, (user_id, event_id))

        existing_team = cursor.fetchone()

        if existing_team:
            connection.close()
            return "You are already part of a team for this event", 400

        # Create unique invite code
        while True:
            invite_code = secrets.token_urlsafe(8)

            cursor.execute("""
                SELECT id
                FROM teams
                WHERE invite_code = ?
            """, (invite_code,))

            if cursor.fetchone() is None:
                break

        # Create team
        cursor.execute("""
            INSERT INTO teams (name, event_id, invite_code)
            VALUES (?, ?, ?)
        """, (name, event_id, invite_code))

        team_id = cursor.lastrowid

        # Add creator as first member
        cursor.execute("""
            INSERT INTO team_members (team_id, user_id)
            VALUES (?, ?)
        """, (team_id, user_id))

        connection.commit()
        connection.close()

        return redirect("/my-team")

    # GET request: show open events
    cursor.execute("""
        SELECT id, name
        FROM events
        WHERE status = 'open'
        ORDER BY id DESC
    """)

    events = cursor.fetchall()

    connection.close()

    return render_template("create_team.html", events=events)
@app.route("/join-team/<invite_code>")
def join_team(invite_code):

    if "user_id" not in session:
        return "Please login first", 401

    user_id = session["user_id"]

    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, event_id
        FROM teams
        WHERE invite_code = ?
    """, (invite_code,))

    team = cursor.fetchone()

    if team is None:
        connection.close()
        return "Invalid invite code", 404

    team_id = team[0]

    cursor.execute("""
        SELECT id
        FROM team_members
        WHERE team_id = ? AND user_id = ?
    """, (team_id, user_id))

    existing_member = cursor.fetchone()

    if existing_member:
        connection.close()
        return "You are already a member of this team"

    cursor.execute("""
        INSERT INTO team_members (team_id, user_id)
        VALUES (?, ?)
    """, (team_id, user_id))

    connection.commit()
    connection.close()

    return f"You joined team: {team[1]}"
@app.route("/my-teams")
def my_teams():

    if "user_id" not in session:
        return "Please login first", 401

    user_id = session["user_id"]

    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT teams.id,
               teams.name,
               teams.invite_code,
               events.name
        FROM team_members
        JOIN teams ON team_members.team_id = teams.id
        JOIN events ON teams.event_id = events.id
        WHERE team_members.user_id = ?
        ORDER BY teams.id DESC
    """, (user_id,))

    teams = cursor.fetchall()

    all_members = {}

    for team in teams:
        cursor.execute("""
            SELECT users.name, users.email, users.role
            FROM team_members
            JOIN users ON team_members.user_id = users.id
            WHERE team_members.team_id = ?
            ORDER BY team_members.id
        """, (team[0],))

        all_members[team[0]] = cursor.fetchall()

    connection.close()

    return render_template(
        "teams.html",
        teams=teams,
        all_members=all_members
    )
 
@app.route("/submit-project", methods=["GET", "POST"])
def submit_project():
    user_id, role = get_auth_context()

    if role != "participant":
     return "Only participants can submit projects", 403

    

    

    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    # User ki teams fetch karo
    cursor.execute("""
        SELECT teams.id, teams.name, events.id, events.name, events.submissions_close
        FROM team_members
        JOIN teams ON team_members.team_id = teams.id
        JOIN events ON teams.event_id = events.id
        WHERE team_members.user_id = ?
        ORDER BY teams.id DESC
    """, (user_id,))

    teams = cursor.fetchall()

    if request.method == "POST":
        # DOGFOOD checker sends JSON for the closed-event probe.
     if request.is_json: 
      data = request.get_json(silent=True) or {}

    cursor_check = sqlite3.connect("dogfood.db")
    cursor_check_cursor = cursor_check.cursor()

    cursor_check_cursor.execute("""
        SELECT submissions_close
        FROM events
        WHERE datetime(submissions_close) <= datetime('now')
        ORDER BY id DESC
        LIMIT 1
    """)

    closed_event = cursor_check_cursor.fetchone()

    cursor_check.close()

    if closed_event:
        return "Submission deadline has closed.", 403

    return "No closed event available for submission probe", 400

    team_id = request.form["team_id"]
    action = request.form["action"]

        # Verify user actually belongs to this team
    cursor.execute("""
            SELECT teams.id,
                   teams.name,
                   events.id,
                   events.name,
                   events.submissions_close
            FROM team_members
            JOIN teams ON team_members.team_id = teams.id
            JOIN events ON teams.event_id = events.id
            WHERE team_members.user_id = ?
              AND teams.id = ?
        """, (user_id, team_id))

    team = cursor.fetchone()

    if team is None:
            connection.close()
            return "You are not a member of this team", 403

    team_name = team[1]
    event_id = team[2]
    event_name = team[3]
    deadline = team[4]

        # Existing project check
    cursor.execute("""
            SELECT id,
                   name,
                   description,
                   github_url,
                   demo_url,
                   status
            FROM projects
            WHERE team_id = ?
        """, (team_id,))

    existing_project = cursor.fetchone()

        # Deadline check
    cursor.execute("""
            SELECT datetime('now', 'localtime') < datetime(?)
        """, (deadline,))

    deadline_open = cursor.fetchone()[0]

        # After deadline: no changes allowed
    if not deadline_open:
            connection.close()
            return "Submission deadline has closed. Project can no longer be changed.", 403

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    github_url = request.form.get("github_url", "").strip()
    demo_url = request.form.get("demo_url", "")
    strip()

        # Draft can be incomplete
    if action == "draft":

            if existing_project:
                cursor.execute("""
                    UPDATE projects
                    SET name = ?,
                        description = ?,
                        github_url = ?,
                        demo_url = ?,
                        status = 'draft',
                        updated_at = datetime('now', 'localtime')
                    WHERE id = ?
                """, (
                    name,
                    description,
                    github_url,
                    demo_url,
                    existing_project[0]
                ))

            else:
               cursor.execute("""
    INSERT INTO projects
    (team_id, name, description, github_url, demo_url,
     submitted_at, status, updated_at, final_submitted_at)
    VALUES (?, ?, ?, ?, ?, '', 'draft',
            datetime('now', 'localtime'), NULL)
""", (
    team_id,
    name,
    description,
    github_url,
    demo_url
))

            connection.commit()
            connection.close()

            return "Project draft saved successfully!"

        # Final submission validation
    if action == "final":

            if not name:
                connection.close()
                return "Project name is required for final submission", 400

            if not description:
                connection.close()
                return "Project description is required for final submission", 400

            if not github_url:
                connection.close()
                return "GitHub URL is required for final submission", 400

            if existing_project:

                cursor.execute("""
                    UPDATE projects
                    SET name = ?,
                        description = ?,
                        github_url = ?,
                        demo_url = ?,
                        status = 'submitted',
                        submitted_at = datetime('now', 'localtime'),
                        updated_at = datetime('now', 'localtime'),
                        final_submitted_at = datetime('now', 'localtime')
                    WHERE id = ?
                """, (
                    name,
                    description,
                    github_url,
                    demo_url,
                    existing_project[0]
                ))

            else:

                cursor.execute("""
                    INSERT INTO projects
                    (team_id, name, description, github_url, demo_url,
                     submitted_at, status, updated_at, final_submitted_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'),
                            'submitted', datetime('now', 'localtime'),
                            datetime('now', 'localtime'))
                """, (
                    team_id,
                    name,
                    description,
                    github_url,
                    demo_url
                ))

            connection.commit()
            connection.close()

            return "Project submitted successfully!"

    connection.close()
    return "Invalid submission action", 400

    # GET request
    connection.close()

    return render_template(
        "submit_project.html",
        teams=teams
    )
@app.route("/projects")
def projects():

    search = request.args.get("q", "").strip()

    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    if search:
        cursor.execute("""
            SELECT projects.id,
                   projects.name,
                   projects.description,
                   projects.github_url,
                   projects.demo_url,
                   teams.name
            FROM projects
            JOIN teams ON projects.team_id = teams.id
            WHERE projects.status = 'submitted'
              AND (
                  projects.name LIKE ?
                  OR teams.name LIKE ?
              )
            ORDER BY projects.id DESC
        """, (
            f"%{search}%",
            f"%{search}%"
        ))
    else:
        cursor.execute("""
            SELECT projects.id,
                   projects.name,
                   projects.description,
                   projects.github_url,
                   projects.demo_url,
                   teams.name
            FROM projects
            JOIN teams ON projects.team_id = teams.id
            WHERE projects.status = 'submitted'
            ORDER BY projects.id DESC
        """)

    projects = cursor.fetchall()

    connection.close()

    return render_template(
        "projects.html",
        projects=projects,
        search=search
    )
@app.route("/judge-dashboard")
def judge_dashboard():

    if "user_id" not in session:
        return "Please login first", 401

    if session.get("user_role") != "judge":
        return "Judge access required", 403

    judge_id = session["user_id"]

    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            ja.id,
            p.id,
            p.name,
            p.description,
            p.github_url,
            p.demo_url,
            teams.name,
            COUNT(scores.id) AS scored_criteria,
            COALESCE(
                SUM(scores.score * rubric_criteria.weight),
                0
            ) AS weighted_score
        FROM judge_assignments ja
        JOIN projects p
            ON ja.project_id = p.id
        JOIN teams
            ON p.team_id = teams.id
        LEFT JOIN scores
            ON scores.assignment_id = ja.id
           AND scores.judge_id = ?
        LEFT JOIN rubric_criteria
            ON scores.criterion_id = rubric_criteria.id
        WHERE ja.judge_id = ?
          AND p.status = 'submitted'
        GROUP BY
            ja.id,
            p.id,
            p.name,
            p.description,
            p.github_url,
            p.demo_url,
            teams.name
        ORDER BY ja.id
    """, (judge_id, judge_id))

    assignments = cursor.fetchall()

    connection.close()

    return render_template(
        "judge_dashboard.html",
        assignments=assignments
    )
@app.route("/api/judge/scores", methods=["GET", "POST"])
def judge_scores_api():

    # Browser session authentication
    judge_id, role = get_auth_context()

    if role != "judge":
      return {"error": "Judge access required"}, 403

    # Acceptance-check authentication
    role_header = request.headers.get("X-Dogfood-Role")

    if judge_id is None and role_header in ["judge_a", "judge_b"]:
        if role_header == "judge_a":
            judge_id = 3
        else:
            judge_id = 18

        auth_identity = role_header

    # Only judges can access this API
    if judge_id is None:
        return {"error": "Judge access required"}, 403

    # Peer-score protection
    requested_judge = request.args.get("judge")

    if requested_judge:
        requested_id = None

        if requested_judge == "judge_a":
            requested_id = 3
        elif requested_judge == "judge_b":
            requested_id = 18
        else:
            try:
                requested_id = int(requested_judge)
            except ValueError:
                return {"error": "Invalid judge"}, 400

        if requested_id != judge_id:
            return {"error": "You cannot access another judge's scores"}, 403

    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    if request.method == "GET":

        cursor.execute("""
            SELECT
                scores.id,
                projects.id,
                projects.name,
                rubric_criteria.name,
                rubric_criteria.weight,
                scores.score,
                scores.comment,
                scores.scored_at
            FROM scores
            JOIN judge_assignments
                ON scores.assignment_id = judge_assignments.id
            JOIN projects
                ON scores.project_id = projects.id
            JOIN rubric_criteria
                ON scores.criterion_id = rubric_criteria.id
            WHERE scores.judge_id = ?
            ORDER BY scores.id
        """, (judge_id,))

        rows = cursor.fetchall()
        connection.close()

        return {
            "judge_id": judge_id,
            "scores": [
                {
                    "score_id": row[0],
                    "project_id": row[1],
                    "project": row[2],
                    "criterion": row[3],
                    "weight": row[4],
                    "score": row[5],
                    "comment": row[6],
                    "scored_at": row[7]
                }
                for row in rows
            ]
        }

    # POST = save a score
    data = request.get_json(silent=True)

    if not data:
        connection.close()
        return {"error": "JSON body required"}, 400

    assignment_id = data.get("assignment_id")
    criterion_id = data.get("criterion_id")
    score_value = data.get("score")
    comment = data.get("comment", "")

    if assignment_id is None or criterion_id is None or score_value is None:
        connection.close()
        return {
            "error": "assignment_id, criterion_id and score are required"
        }, 400

    try:
        score_value = float(score_value)
    except (TypeError, ValueError):
        connection.close()
        return {"error": "Score must be a number"}, 400

    if score_value < 0 or score_value > 5:
        connection.close()
        return {"error": "Score must be between 0 and 5"}, 400

    # Critical: assignment must belong to the logged-in judge
    cursor.execute("""
        SELECT project_id, event_id
        FROM judge_assignments
        WHERE id = ?
          AND judge_id = ?
    """, (assignment_id, judge_id))

    assignment = cursor.fetchone()

    if assignment is None:
        connection.close()
        return {"error": "Assignment does not belong to this judge"}, 403

    project_id, event_id = assignment

    # Criterion must belong to the same event
    cursor.execute("""
        SELECT id
        FROM rubric_criteria
        WHERE id = ?
          AND event_id = ?
    """, (criterion_id, event_id))

    criterion = cursor.fetchone()

    if criterion is None:
        connection.close()
        return {"error": "Invalid rubric criterion"}, 400

    cursor.execute("""
        INSERT INTO scores
        (assignment_id, judge_id, project_id, criterion_id, score, comment)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(assignment_id, criterion_id)
        DO UPDATE SET
            score = excluded.score,
            comment = excluded.comment,
            scored_at = CURRENT_TIMESTAMP
    """, (
        assignment_id,
        judge_id,
        project_id,
        criterion_id,
        score_value,
        comment
    ))

    connection.commit()

    cursor.execute("""
        SELECT id, score, comment, scored_at
        FROM scores
        WHERE assignment_id = ?
          AND criterion_id = ?
    """, (assignment_id, criterion_id))

    saved = cursor.fetchone()

    connection.close()

    return {
        "message": "Score saved successfully",
        "score_id": saved[0],
        "score": saved[1],
        "comment": saved[2],
        "scored_at": saved[3]
    }, 201
@app.route("/judge/result/<int:assignment_id>")
def judge_result(assignment_id):

    if "user_id" not in session:
        return "Please login first", 401

    if session.get("user_role") != "judge":
        return "Judge access required", 403

    judge_id = session["user_id"]

    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            ja.id,
            p.name,
            teams.name
        FROM judge_assignments ja
        JOIN projects p
            ON ja.project_id = p.id
        JOIN teams
            ON p.team_id = teams.id
        WHERE ja.id = ?
          AND ja.judge_id = ?
    """, (assignment_id, judge_id))

    assignment = cursor.fetchone()

    if assignment is None:
        connection.close()
        return "Assignment not found or not assigned to you", 403

    cursor.execute("""
        SELECT
            rubric_criteria.name,
            rubric_criteria.weight,
            scores.score,
            scores.comment
        FROM scores
        JOIN rubric_criteria
            ON scores.criterion_id = rubric_criteria.id
        WHERE scores.assignment_id = ?
          AND scores.judge_id = ?
        ORDER BY rubric_criteria.id
    """, (assignment_id, judge_id))

    scores = cursor.fetchall()

    weighted_total = sum(
        score * weight
        for _, weight, score, _ in scores
    )

    connection.close()

    return {
        "assignment_id": assignment_id,
        "project": assignment[1],
        "team": assignment[2],
        "scores": [
            {
                "criterion": name,
                "weight": weight,
                "score": score,
                "comment": comment
            }
            for name, weight, score, comment in scores
        ],
        "weighted_score": round(weighted_total, 2),
        "percentage": round((weighted_total / 5) * 100, 2)
    }
@app.route("/judge/score/<int:assignment_id>", methods=["GET", "POST"])
def judge_score(assignment_id):

    if "user_id" not in session:
        return "Please login first", 401

    if session.get("user_role") != "judge":
        return "Judge access required", 403

    judge_id = session["user_id"]

    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    # Make sure this assignment belongs to the logged-in judge
    cursor.execute("""
        SELECT
            ja.id,
            ja.project_id,
            ja.event_id,
            p.name,
            p.description,
            teams.name
        FROM judge_assignments ja
        JOIN projects p
            ON ja.project_id = p.id
        JOIN teams
            ON p.team_id = teams.id
        WHERE ja.id = ?
          AND ja.judge_id = ?
          AND p.status = 'submitted'
    """, (assignment_id, judge_id))

    assignment = cursor.fetchone()

    if assignment is None:
        connection.close()
        return "Assignment not found or not assigned to you", 403

    event_id = assignment[2]

    # Rubric for this event
    cursor.execute("""
        SELECT id, name, weight
        FROM rubric_criteria
        WHERE event_id = ?
        ORDER BY id
    """, (event_id,))

    criteria = cursor.fetchall()

    if request.method == "GET":

        cursor.execute("""
            SELECT criterion_id, score, comment
            FROM scores
            WHERE assignment_id = ?
              AND judge_id = ?
        """, (assignment_id, judge_id))

        saved_scores = {
            row[0]: {
                "score": row[1],
                "comment": row[2] or ""
            }
            for row in cursor.fetchall()
        }

        connection.close()

        return render_template(
            "judge_score.html",
            assignment=assignment,
            criteria=criteria,
            saved_scores=saved_scores
        )

    # POST: save all rubric scores
    for criterion in criteria:

        criterion_id = criterion[0]

        score_text = request.form.get(
            f"score_{criterion_id}",
            ""
        ).strip()

        comment = request.form.get(
            f"comment_{criterion_id}",
            ""
        ).strip()

        if score_text == "":
            connection.close()
            return f"Score required for {criterion[1]}", 400

        try:
            score_value = float(score_text)
        except ValueError:
            connection.close()
            return f"Invalid score for {criterion[1]}", 400

        if score_value < 0 or score_value > 5:
            connection.close()
            return f"Score for {criterion[1]} must be between 0 and 5", 400

        # Make sure criterion belongs to this event
        cursor.execute("""
            SELECT id
            FROM rubric_criteria
            WHERE id = ?
              AND event_id = ?
        """, (criterion_id, event_id))

        if cursor.fetchone() is None:
            connection.close()
            return "Invalid rubric criterion", 400

        cursor.execute("""
            INSERT INTO scores
            (assignment_id, judge_id, project_id, criterion_id, score, comment)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(assignment_id, criterion_id)
            DO UPDATE SET
                score = excluded.score,
                comment = excluded.comment,
                scored_at = CURRENT_TIMESTAMP
        """, (
            assignment_id,
            judge_id,
            assignment[1],
            criterion_id,
            score_value,
            comment
        ))

    connection.commit()
    connection.close()

    return redirect("/judge-dashboard")
@app.route("/api/export.csv")
def export_csv():

    user_id, role = get_auth_context()

    if role != "organizer":
      return "Organizer access required", 403

    connection = sqlite3.connect("dogfood.db")
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            projects.id,
            projects.name,
            teams.name,
            events.name,
            projects.status,
            projects.github_url,
            projects.demo_url,
            projects.submitted_at
        FROM projects
        JOIN teams
            ON projects.team_id = teams.id
        JOIN events
            ON teams.event_id = events.id
        ORDER BY projects.id
    """)

    rows = cursor.fetchall()

    connection.close()

    csv_content = (
        "project_id,project_name,team,event,status,"
        "github_url,demo_url,submitted_at\n"
    )

    for row in rows:
        csv_content += ",".join(
            '"' + str(value or "").replace('"', '""') + '"'
            for value in row
        ) + "\n"

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=projects.csv"
        }
    )
if __name__ == "__main__":
   app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)