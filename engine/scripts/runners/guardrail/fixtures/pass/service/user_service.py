"""Business logic: goes through the repository, never touches db directly."""
from repository import user_repo


def load_profile(user_id):
    user = user_repo.get_user(user_id)
    return {"id": user_id, "name": user["name"]}
