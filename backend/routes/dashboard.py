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

    # Heutige abgeschlossene Kürzel
    entries = (
        db.query(CompletedToday)
        .order_by(CompletedToday.timestamp.desc())
        .all()
        or []
    )

    # ⭐ Fertige Aufträge aus der Produktion (typ = produktion oder beides)
    fertige_raw = (
        db.query(CompletedToday)
        .filter(CompletedToday.typ.in_(["produktion", "beides"]))
        .order_by(CompletedToday.timestamp.desc())
        .all()
    )

    db.close()

    # ⭐ KEINE Gruppierung nötig – CompletedToday hat 1 Eintrag pro Auftrag
    fertige_auftraege = [
        {
            "kuerzel": f.kuerzel,
            "prod_id": f.prod_id,
            "start_bft": f.start_bft,
            "timestamp": f.timestamp,
        }
        for f in fertige_raw
    ]

    # Sortierung: Kürzel → Start-BFT → Timestamp
    entries = sorted(
        entries,
        key=lambda e: (e.kuerzel, e.start_bft or "", e.timestamp)
    )

    # ✅ WICHTIG: TemplateResponse mit KEYWORD-ARGUMENTEN
    return request.app.state.templates.TemplateResponse(
        name="dashboard.html",
        context={
            "request": request,
            "entries": entries,
            "fertige_auftraege": fertige_auftraege,
        }
    )


# ---------------------------------------------------------
# Alias-Route für /dashboard
# ---------------------------------------------------------
@router.get("/dashboard")
def dashboard_alias(request: Request):
    return RedirectResponse(url="/", status_code=307)


# ---------------------------------------------------------
# Excel-Export der Tagesübersicht
# ---------------------------------------------------------
@router.get("/dashboard/export")
def dashboard_export(request: Request):
    db = SessionLocal()
    entries = db.query(CompletedToday).all()
    db.close()

    if not entries:
        return RedirectResponse("/", status_code=303)

    rows = []
    for e in entries:
        d = e.__dict__.copy()
        d.pop("_sa_instance_state", None)
        rows.append(d)

    df = pd.DataFrame(rows)

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
