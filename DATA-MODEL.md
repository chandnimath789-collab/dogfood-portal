# Data Model

Dogfood Portal uses SQLite for persistent application data.

## Main Tables

### users
Stores account information and roles.

Fields include:
- id
- name
- email
- password
- role

Roles include participant, organizer, judge and admin.

### events
Stores hackathon events.

Fields include:
- id
- name
- description
- starts_at
- submissions_close
- tracks
- prizes
- status

### teams
Stores teams created for events.

Fields include:
- id
- name
- event_id
- invite_code

### team_members
Connects users with teams.

### projects
Stores project submissions.

Fields include:
- id
- team_id
- name
- description
- github_url
- demo_url
- submitted_at
- status
- updated_at
- final_submitted_at

Project status supports draft and submitted states.

### rubric_criteria
Stores judging criteria and their weights for an event.

### judge_assignments
Connects judges with projects assigned for evaluation.

### scores
Stores judge scores and comments for rubric criteria.

## Relationships

users ? team_members ? teams ? events

teams ? projects

events ? rubric_criteria

projects ? judge_assignments ? scores

This structure keeps participants, teams, submissions and judging data separated while preserving their relationships.
