from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from datetime import date
import pandas as pd
from io import BytesIO

from backend.database_base import SessionLocal
from backend.database import Item

router = APIRouter()

@router.get("/dashboard/export")
def dashboard_export(request: Request):
    today = date.today()
    db = SessionLocal()

    # 1) Alle fertigen oder ausgelieferten Items holen
    items = db.query(Item).filter(
        (Item.fertig == True) | (Item.ausgeliefert == True)
    ).all()

    # 2) In vollständiges DataFrame umwandeln
    rows = []
    for i in items:
        d = i.__dict__.copy()
        d.pop("_sa_instance_state", None)
        rows.append(d)

    df = pd.DataFrame(rows)

    # 3) Excel in Memory erzeugen
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Items")

    output.seek(0)

    # 4) Nur abgeschlossene Items löschen
    db.query(Item).filter(
        (Item.fertig == True) | (Item.ausgeliefert == True)
    ).delete()
    db.commit()
    db.close()

    # 5) Datei zurückgeben
    filename = f"VOE_Abschluss_{today}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
