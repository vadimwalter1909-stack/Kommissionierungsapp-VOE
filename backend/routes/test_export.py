from fastapi import APIRouter
from backend.services.daily_export import export_and_send_email

test_router = APIRouter()

@test_router.get("/test/export-email")
def test_export_email():
    export_and_send_email()
    return {"status": "OK", "message": "Test-E-Mail wurde ausgelöst"}
