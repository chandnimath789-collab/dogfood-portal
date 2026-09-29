# Judging

Dogfood Portal provides a role-based judging workflow.

## Judge Workflow

1. A judge logs in.
2. The judge opens the assigned projects dashboard.
3. The judge selects an assigned project.
4. Scores are entered for each rubric criterion.
5. Optional comments can be added.
6. Scores are stored in the database.
7. A weighted result is calculated.

## Rubric

The current example rubric uses:

- Functionality — 40%
- Quality — 30%
- Innovation — 30%

Each criterion is scored from 0 to 5.

## Weighted Score

The weighted score is calculated from the criterion scores and
their configured weights.

For example:

weighted score =
(Functionality × 0.40) +
(Quality × 0.30) +
(Innovation × 0.30)

The final result is also displayed as a percentage.

## Access Control

A judge can access only their own scoring data and assigned projects.

Participant access to judge APIs is blocked.

A judge cannot request another judge's private scoring data.
