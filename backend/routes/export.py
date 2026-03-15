from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.database_base import SessionLocal
from backend.database import Item
import io
import pandas as pd

router = APIRouter()


@router.get("/export/logistik")
def export_logistik():
    db = SessionLocal()

    items = db.query(Item).all()

    rows = []

    for item in items:

        # 🔥 1) PRODUKTIONSARTIKEL IGNORIEREN
        # Diese Artikel sind NIE kommissionierbar
        if item.beschaffung == "Produktion" and item.referenz == "Produktion":
            continue

        # 🔥 2) Status bestimmen
        if item.ausgebucht:
            status = "kritisch"
        elif not item.kommissioniert:
            status = "offen"
        else:
            status = "teil-kommissioniert"

        # 🔥 3) Nur offene oder teil-kommissionierte Logistik-Artikel exportieren
        if status not in ["offen", "teil-kommissioniert"]:
            continue

        rows.append({
            "ProdID": item.prod_id,
            "Kürzel": item.kuerzel,
            "Artikel-Nr": item.artikel_nr,
            "Bew.-Artikel": item.artikel_clean,
            "Durchmesser": item.durchmesser,
            "Länge": item.laenge,
            "Biegung": item.biegung,
            "Bedarfs-Menge": item.bedarfs_menge_pos,
            "Beschaffung": item.beschaffung,
            "Referenz (ERP-Artikel)": item.referenz,
            "Menge": item.menge,
            "Kommissioniert": item.kommissioniert,
            "Status": status,
            "Start-BFT": item.start_bft,
            "Start-Bew": item.start_bew,
        })

    df = pd.DataFrame(rows)

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=logistik_export.xlsx"}
    )
