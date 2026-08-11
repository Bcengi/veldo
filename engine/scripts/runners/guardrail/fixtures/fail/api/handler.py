"""HTTP boundary: calls the service and returns a response (this file is clean;
only the service layer violates the invariant)."""
from service import user_service


def handle(request):
    return {"status": 200, "body": user_service.load_profile(request["user_id"])}
