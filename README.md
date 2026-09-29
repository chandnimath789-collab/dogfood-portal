# Dogfood Hackathon Portal

A self-hostable hackathon submission and judging portal built with Flask and SQLite.

## Features

- Role-based authentication
- Participant, Organizer, Judge and Admin roles
- Hackathon event management
- Team creation and invite links
- Team member management
- Project draft and final submission
- Submission deadline enforcement
- Public searchable project gallery
- Judge assignments
- Weighted rubric scoring
- Judge score isolation
- Organizer CSV export
- Official DOGFOOD fixture seeding

## Tech Stack

- Python
- Flask
- SQLite
- Jinja2
- HTML/CSS
- Docker

## Run Locally

```bash
python init_db.py
python seed_fixtures.py
python app.py