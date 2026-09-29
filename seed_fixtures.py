import json
import sqlite3
from werkzeug.security import generate_password_hash


DB = "dogfood.db"
FIXTURES = "fixtures.json"


def get_or_create_user(cursor, name, email, role):
    cursor.execute(
        "SELECT id FROM users WHERE email = ? LIMIT 1",
        (email,)
    )

    row = cursor.fetchone()

    if row:
        return row[0]

    password_hash = generate_password_hash("fixture123")

    cursor.execute("""
        INSERT INTO users (name, email, role, password)
        VALUES (?, ?, ?, ?)
    """, (
        name,
        email,
        role,
        password_hash
    ))

    return cursor.lastrowid


with open(FIXTURES, "r", encoding="utf-8") as file:
    data = json.load(file)


connection = sqlite3.connect(DB)
cursor = connection.cursor()

# ---------------------------------------------------------
# Prevent duplicate fixture seeding
# ---------------------------------------------------------

cursor.execute("""
    SELECT id
    FROM events
    WHERE name = ?
    LIMIT 1
""", (data["event"]["name"],))

existing_event = cursor.fetchone()

if existing_event:
    print("Fixture event already exists. Nothing to seed.")
    connection.close()
    raise SystemExit


# ---------------------------------------------------------
# EVENT
# ---------------------------------------------------------

track_names = "\n".join(
    track["name"]
    for track in data["tracks"]
)

cursor.execute("""
    INSERT INTO events
    (name, description, submissions_close, status,
     starts_at, tracks, prizes)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (
    data["event"]["name"],
    "Official DOGFOOD fixture event",
    data["event"]["submissions_close"],
    "closed",
    "",
    track_names,
    ""
))

event_db_id = cursor.lastrowid


# ---------------------------------------------------------
# JUDGES
# ---------------------------------------------------------

judge_map = {}

for judge in data["judges"]:

    user_id = get_or_create_user(
        cursor,
        judge["name"],
        judge["email"],
        "judge"
    )

    judge_map[judge["id"]] = user_id


# ---------------------------------------------------------
# TEAMS + TEAM MEMBERS
# ---------------------------------------------------------

team_map = {}

for team in data["teams"]:

    invite_code = "fixture-" + team["id"]

    cursor.execute("""
        INSERT INTO teams
        (name, event_id, invite_code)
        VALUES (?, ?, ?)
    """, (
        team["name"],
        event_db_id,
        invite_code
    ))

    team_db_id = cursor.lastrowid

    team_map[team["id"]] = team_db_id

    for email in team["members"]:

        user_id = get_or_create_user(
            cursor,
            email.split("@")[0],
            email,
            "participant"
        )

        cursor.execute("""
            INSERT OR IGNORE INTO team_members
            (team_id, user_id)
            VALUES (?, ?)
        """, (
            team_db_id,
            user_id
        ))


# ---------------------------------------------------------
# RUBRIC
# ---------------------------------------------------------

rubric_map = {}

criteria = [
    ("functionality", "Functionality", 0.40),
    ("quality", "Quality", 0.30),
    ("innovation", "Innovation", 0.30)
]

for key, name, weight in criteria:

    cursor.execute("""
        INSERT INTO rubric_criteria
        (event_id, name, weight)
        VALUES (?, ?, ?)
    """, (
        event_db_id,
        name,
        weight
    ))

    rubric_map[key] = cursor.lastrowid


# ---------------------------------------------------------
# PROJECTS
# ---------------------------------------------------------

project_map = {}

for project in data["projects"]:

    team_db_id = team_map[project["team"]]

    cursor.execute("""
        INSERT INTO projects
        (team_id,
         name,
         description,
         github_url,
         demo_url,
         submitted_at,
         status,
         updated_at,
         final_submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, 'submitted', ?, ?)
    """, (
        team_db_id,
        project["title"],
        project["summary"],
        project["repo_url"],
        "",
        project["submitted_at"],
        project["submitted_at"],
        project["submitted_at"]
    ))

    project_db_id = cursor.lastrowid

    project_map[project["id"]] = project_db_id


# ---------------------------------------------------------
# SCORES + JUDGE ASSIGNMENTS
# ---------------------------------------------------------

assignment_map = {}

for score_entry in data["scores"]:

    judge_db_id = judge_map[score_entry["judge"]]
    project_db_id = project_map[score_entry["project"]]

    assignment_key = (
        score_entry["judge"],
        score_entry["project"]
    )

    if assignment_key not in assignment_map:

        cursor.execute("""
            INSERT OR IGNORE INTO judge_assignments
            (event_id, project_id, judge_id, status)
            VALUES (?, ?, ?, 'assigned')
        """, (
            event_db_id,
            project_db_id,
            judge_db_id
        ))

        cursor.execute("""
            SELECT id
            FROM judge_assignments
            WHERE event_id = ?
              AND project_id = ?
              AND judge_id = ?
        """, (
            event_db_id,
            project_db_id,
            judge_db_id
        ))

        assignment_map[assignment_key] = cursor.fetchone()[0]


    assignment_id = assignment_map[assignment_key]

    for criterion_key, score_value in score_entry["criteria"].items():

        criterion_id = rubric_map[criterion_key]

        cursor.execute("""
            INSERT OR IGNORE INTO scores
            (assignment_id,
             judge_id,
             project_id,
             criterion_id,
             score,
             comment)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            assignment_id,
            judge_db_id,
            project_db_id,
            criterion_id,
            score_value,
            score_entry.get("comment", "")
        ))


connection.commit()


print("Official fixtures seeded successfully!")
print("Event:", data["event"]["name"])
print("Tracks:", len(data["tracks"]))
print("Judges:", len(data["judges"]))
print("Teams:", len(data["teams"]))
print("Projects:", len(data["projects"]))
print("Scores:", len(data["scores"]))


connection.close()