import sqlite3

connection = sqlite3.connect("dogfood.db")
cursor = connection.cursor()


# USERS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL
)
""")


# USERS
users = [
    ("Organizer User", "organizer@example.com", "organizer"),
    ("Judge User", "judge@example.com", "judge"),
    ("Participant User", "participant@example.com", "participant")
]

for user in users:
    cursor.execute("""
    INSERT OR IGNORE INTO users (name, email, role)
    VALUES (?, ?, ?)
    """, user)


# EVENTS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    submissions_close TEXT NOT NULL,
    status TEXT NOT NULL
)
""")


# TEST EVENT
cursor.execute("""
INSERT OR IGNORE INTO events
(name, description, submissions_close, status)
VALUES (?, ?, ?, ?)
""", (
    "Dogfood Demo Hackathon",
    "A test hackathon event",
    "2026-09-29 18:00",
    "open"
))


# SAVE CHANGES
connection.commit()


# CHECK USERS
cursor.execute("SELECT * FROM users")
all_users = cursor.fetchall()

print("Users:")
print(all_users)


# CHECK EVENTS
cursor.execute("SELECT * FROM events")
events = cursor.fetchall()

print("Events:")
print(events)

# TEAMS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    event_id INTEGER NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id)
)
""")
# PROJECTS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    github_url TEXT,
    demo_url TEXT,
    submitted_at TEXT NOT NULL,
    FOREIGN KEY (team_id) REFERENCES teams(id)
)
""")


connection.commit()

connection.close()

print("Database setup complete!")