from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import pandas as pd
from io import BytesIO
from datetime import date

from backend.database_base import SessionLocal
from backend.database import Item

router = APIRouter()

@router.get("/items/export")
def export_items():
    db = SessionLocal()

    # Nur ausgelieferte Items exportieren
    items = db.query(Item).filter(Item.ausgeliefert == True).all()
    db.close()

    if not items:
        empty = BytesIO()
        empty.write(b"Keine ausgelieferten Items vorhanden.")
        empty.seek(0)
        return StreamingResponse(empty, media_type="text/plain")

    # Alle Spalten exportieren
    rows = []
    for i in items:
        d = i.__dict__.copy()
        d.pop("_sa_instance_state", None)
        rows.append(d)

    df = pd.DataFrame(rows)

    # Excel in Memory erzeugen
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Ausgelieferte_Items")

    output.seek(0)

    filename = f"VOE_Ausgelieferte_Items_{date.today().isoformat()}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
