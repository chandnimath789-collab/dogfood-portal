# Architecture

## Overview

Dogfood Portal is a Flask-based self-hostable hackathon submission
and judging platform using SQLite for local persistence.

## Application

The main application is implemented in `app.py`.

Flask routes provide:

- Authentication and sessions
- Role-based access
- Event management
- Team creation and invitations
- Project submission
- Public project gallery
- Judge assignments and scoring
- Admin dashboard
- CSV export

## Authentication

Browser authentication uses Flask sessions.

The DOGFOOD acceptance checker can authenticate through the
`X-Dogfood-Role` request header.

Supported checker identities:

- participant
- organizer
- judge_a
- judge_b

## Database

SQLite is used as the application database.

The schema is initialized by:

```text
init_db.py
