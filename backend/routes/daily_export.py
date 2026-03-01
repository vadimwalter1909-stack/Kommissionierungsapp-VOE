from fastapi import APIRouter
from backend.services.daily_export import export_and_send_email

router = APIRouter()

@router.get("/daily/export")
def trigger_daily_export():
    export_and_send_email()
    return {"status": "ok"}
