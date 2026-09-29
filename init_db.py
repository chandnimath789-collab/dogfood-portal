import sqlite3

DB = "dogfood.db"

connection = sqlite3.connect(DB)
cursor = connection.cursor()

# USERS
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL,
    password TEXT
)
""")

# EVENTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    submissions_close TEXT NOT NULL,
    status TEXT NOT NULL,
    starts_at TEXT,
    tracks TEXT,
    prizes TEXT
)
""")

# TEAMS
cursor.execute("""
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    event_id INTEGER NOT NULL,
    invite_code TEXT UNIQUE,
    FOREIGN KEY (event_id) REFERENCES events(id)
)
""")

# TEAM MEMBERS
cursor.execute("""
CREATE TABLE IF NOT EXISTS team_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(team_id, user_id),
    FOREIGN KEY (team_id) REFERENCES teams(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

# PROJECTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    github_url TEXT,
    demo_url TEXT,
    submitted_at TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'submitted',
    updated_at TEXT,
    final_submitted_at TEXT,
    FOREIGN KEY (team_id) REFERENCES teams(id)
)
""")

# RUBRIC
cursor.execute("""
CREATE TABLE IF NOT EXISTS rubric_criteria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    weight REAL NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id)
)
""")

# JUDGE ASSIGNMENTS
cursor.execute("""
CREATE TABLE IF NOT EXISTS judge_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    judge_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'assigned',
    assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, project_id, judge_id),
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (judge_id) REFERENCES users(id)
)
""")

# SCORES
cursor.execute("""
CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL,
    judge_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    criterion_id INTEGER NOT NULL,
    score REAL NOT NULL,
    comment TEXT,
    scored_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(assignment_id, criterion_id),
    FOREIGN KEY (assignment_id) REFERENCES judge_assignments(id),
    FOREIGN KEY (judge_id) REFERENCES users(id),
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (criterion_id) REFERENCES rubric_criteria(id)
)
""")

connection.commit()
connection.close()

print("Database initialized successfully!")