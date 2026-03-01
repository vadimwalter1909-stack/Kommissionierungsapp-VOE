from fastapi import APIRouter, UploadFile, File
from fastapi.responses import RedirectResponse
import pandas as pd
from datetime import datetime

from backend.utils.dataframe import prepare_dataframe
from backend.database_base import SessionLocal
from backend.database import Item, CompletedToday

router = APIRouter()


@router.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    df = pd.read_excel(file.file)
    df = prepare_dataframe(df)

    db = SessionLocal()

    # ---------------------------------------------------------
    # 1) Dashboard leeren (Tagesübersicht)
    # ---------------------------------------------------------
    db.query(CompletedToday).delete()
    db.commit()

    # ---------------------------------------------------------
    # 2) Nur vollständig abgeschlossene Items löschen
    #    (Produktion fertig + Logistik ausgeliefert)
    # ---------------------------------------------------------
    db.query(Item).filter(Item.ausgeliefert == True).delete()
    db.commit()

    # ---------------------------------------------------------
    # 3) Neue Items aus der Excel hinzufügen
    #    Offene Items bleiben bestehen!
    # ---------------------------------------------------------
    for _, row in df.iterrows():
        item = Item()

        # merge_key eindeutig pro Zeile
        db.add(item)
        db.flush()  # erzeugt item.id
        item.merge_key = str(item.id)

        # Statusfelder
        item.fertig = False
        item.kommissioniert = False
        item.ausgeliefert = False

        # Pflichtfelder
        item.kuerzel = row.get("kuerzel", "")
        item.prod_id = row.get("prod_id", "")
        item.artikel_nr = row.get("artikel_nr", "")
        item.artikel_clean = row.get("artikel_clean", "")

        # Artikel-Infos
        item.durchmesser = float(row.get("durchmesser", 0))
        item.laenge = float(row.get("laenge", 0))
        item.biegung = row.get("biegung", "")

        # Mengen
        item.bedarfs_menge_pos = float(row.get("bedarfs_menge_pos", 0))
        item.menge = float(row.get("menge", 0))

        # Beschaffung / Referenz
        item.beschaffung = row.get("beschaffung", "")
        item.referenz = row.get("referenz", "")

        # Zeitliche Infos
        item.start_bft = row.get("start_bft", "")
        item.start_bew = row.get("start_bew", "")

    db.commit()
    db.close()

    timestamp = datetime.now().strftime("%H:%M")
    return RedirectResponse(f"/?upload_success=1&timestamp={timestamp}", status_code=303)
