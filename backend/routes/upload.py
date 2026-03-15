from fastapi import APIRouter, UploadFile, File, Request
from fastapi.responses import RedirectResponse
import pandas as pd
from datetime import datetime

from backend.utils.dataframe import prepare_dataframe
from backend.database_base import SessionLocal
from backend.database import Item, CompletedToday

router = APIRouter()


def norm(value):
    if value is None:
        return ""
    value = str(value).strip()
    if value.lower() in ["nan", "none", "null"]:
        return ""
    return value


@router.post("/upload")
async def upload_excel(request: Request, file: UploadFile = File(...)):
    df = pd.read_excel(file.file)
    df = prepare_dataframe(df)

    db = SessionLocal()

    # 1) Dashboard leeren
    db.query(CompletedToday).delete()
    db.commit()

    # 2) Nur vollständig abgeschlossene Items löschen
    db.query(Item).filter(Item.ausgeliefert == True).delete()
    db.commit()

    errors = []
    warnings = []

    # 3) Neue Items aus Excel hinzufügen
    for _, row in df.iterrows():

        prod_id = norm(row.get("prod_id"))
        kuerzel = norm(row.get("kuerzel"))
        start_bft = norm(row.get("start_bft"))
        artikel_nr = norm(row.get("artikel_nr"))

        # 🔥 WICHTIG:
        # Bew.-Artikel ≠ Start Bew.
        bew_artikel = norm(row.get("bew_artikel"))   # z.B. B500B-K07
        start_bew = norm(row.get("start_bew"))       # echtes Start-Bew.-Datum / Wert

        durchmesser = norm(row.get("durchmesser"))
        laenge = norm(row.get("laenge"))
        biegung = norm(row.get("biegung"))
        menge = norm(row.get("menge"))

        # merge_key bleibt unverändert
        merge_key = (
            f"{prod_id}|"
            f"{kuerzel}|"
            f"{artikel_nr}|"
            f"{start_bew}|"
            f"{durchmesser}|"
            f"{laenge}|"
            f"{biegung}|"
            f"{menge}"
        )

        # Prüfen, ob Auftrag existiert
        existing_items_same_prod = db.query(Item).filter(Item.prod_id == prod_id).all()

        if existing_items_same_prod:
            # Auftrag komplett in Parkzone → reaktivieren
            if all(i.verschoben for i in existing_items_same_prod):
                for old in existing_items_same_prod:
                    old.verschoben = False
                    old.reaktiviert = True

                db.commit()

                warnings.append({
                    "prod_id": prod_id,
                    "kuerzel": kuerzel,
                    "start_bft_alt": existing_items_same_prod[0].start_bft,
                    "start_bft_neu": start_bft,
                    "reason": "Auftrag wurde automatisch aus der Parkzone reaktiviert."
                })

        # Prüfen, ob Position existiert
        existing_item = db.query(Item).filter(Item.merge_key == merge_key).first()

        if existing_item:
            errors.append({
                "prod_id": prod_id,
                "kuerzel": kuerzel,
                "reason": "Position existiert bereits (merge_key)."
            })
            continue

        # Neue Position anlegen
        item = Item()
        db.add(item)
        db.flush()

        item.merge_key = merge_key

        item.fertig = False
        item.kommissioniert = False
        item.ausgeliefert = False

        item.kuerzel = kuerzel
        item.prod_id = prod_id
        item.artikel_nr = artikel_nr

        # 🔥 KORREKT:
        # Bew.-Artikel → artikel_clean
        item.artikel_clean = bew_artikel

        # numerische Felder
        item.durchmesser = float(row.get("durchmesser", 0) or 0)
        item.laenge = float(row.get("laenge", 0) or 0)
        item.biegung = norm(row.get("biegung"))

        item.bedarfs_menge_pos = float(row.get("bedarfs_menge_pos", 0) or 0)
        item.menge = float(row.get("menge", 0) or 0)

        item.beschaffung = norm(row.get("beschaffung"))
        item.referenz = norm(row.get("referenz"))

        # 🔥 KORREKT:
        # Start-BFT bleibt Start-BFT
        # Start-Bew bleibt Start-Bew
        item.start_bft = start_bft
        item.start_bew = start_bew

    db.commit()
    db.close()

    if errors or warnings:
        return request.app.state.templates.TemplateResponse(
            "upload_summary.html",
            {
                "request": request,
                "errors": errors,
                "warnings": warnings
            }
        )

    timestamp = datetime.now().strftime("%H:%M")
    return RedirectResponse(f"/?upload_success=1&timestamp={timestamp}", status_code=303)
