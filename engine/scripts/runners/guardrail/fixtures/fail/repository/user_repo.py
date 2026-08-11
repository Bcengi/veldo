"""Data-access layer: the only layer allowed to import the db module."""
import db


def get_user(user_id):
    return db.query("select id, name from users where id = ?", user_id)
