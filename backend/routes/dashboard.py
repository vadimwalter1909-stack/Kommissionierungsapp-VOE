from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, StreamingResponse
import pandas as pd
from datetime import date
from io import BytesIO

from backend.database_base import SessionLocal
from backend.database import CompletedToday

router = APIRouter()


# ---------------------------------------------------------
# Dashboard – Tagesübersicht
# ---------------------------------------------------------
@router.get("/")
def dashboard(request: Request):
    db = SessionLocal()
    entries = db.query(CompletedToday).order_by(CompletedToday.timestamp.desc()).all() or []
    db.close()

    # Sortierung: Kürzel → Start-BFT → Timestamp
    entries = sorted(entries, key=lambda e: (e.kuerzel, e.start_bft or "", e.timestamp))

    return request.app.state.templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "entries": entries
        }
    )


# ---------------------------------------------------------
# Alias-Route für /dashboard
# ---------------------------------------------------------
@router.get("/dashboard")
def dashboard_alias(request: Request):
    return RedirectResponse(url="/", status_code=307)


# ---------------------------------------------------------
# Excel-Export der Tagesübersicht (staging-sicher, RAM-basiert)
# ---------------------------------------------------------
@router.get("/dashboard/export")
def dashboard_export(request: Request):
    db = SessionLocal()
    entries = db.query(CompletedToday).all()
    db.close()

    if not entries:
        return RedirectResponse("/", status_code=303)

    # Alle Spalten exportieren
    rows = []
    for e in entries:
        d = e.__dict__.copy()
        d.pop("_sa_instance_state", None)
        rows.append(d)

    df = pd.DataFrame(rows)

    # Excel in Memory erzeugen
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dashboard")

    output.seek(0)

    filename = f"tagesabschluss_{date.today().isoformat()}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ---------------------------------------------------------
# Tagesübersicht manuell leeren (optional)
# ---------------------------------------------------------
@router.post("/dashboard/reset")
def dashboard_reset(request: Request):
    db = SessionLocal()
    db.query(CompletedToday).delete()
    db.commit()
    db.close()

    return RedirectResponse("/", status_code=303)
