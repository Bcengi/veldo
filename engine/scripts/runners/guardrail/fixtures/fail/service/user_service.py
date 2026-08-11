"""Business logic that reaches past the repository straight into the db module.

This is the deliberate invariant violation: the service layer imports db
directly instead of going through the repository, so the guardrail runner
must flag this line and exit 1.
"""
import db


def load_profile(user_id):
    row = db.query("select id, name from users where id = ?", user_id)
    return {"id": user_id, "name": row["name"]}
