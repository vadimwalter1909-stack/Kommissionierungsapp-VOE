from fastapi import APIRouter, UploadFile, File, Request
from fastapi.responses import RedirectResponse
import pandas as pd
from datetime import datetime

from backend.utils.dataframe import prepare_dataframe
from backend.database_base import SessionLocal
from backend.database import Item, CompletedToday

router = APIRouter()


# ---------------------------------------------------------
# Hilfsfunktion: Werte narrensicher normalisieren
# ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # 1) Dashboard leeren (Tagesübersicht)
    # ---------------------------------------------------------
    db.query(CompletedToday).delete()
    db.commit()

    # ---------------------------------------------------------
    # 2) Nur vollständig abgeschlossene Items löschen
    # ---------------------------------------------------------
    db.query(Item).filter(Item.ausgeliefert == True).delete()
    db.commit()

    # ---------------------------------------------------------
    # 3) Fehler- und Warnlisten
    # ---------------------------------------------------------
    errors = []     # echte Duplikate → Upload blockiert
    warnings = []   # Parkzone → Reaktivierung nötig

    # ---------------------------------------------------------
    # 4) Neue Items aus Excel hinzufügen
    # ---------------------------------------------------------
    for _, row in df.iterrows():

        # ⭐ Alle Felder narrensicher normalisieren
        prod_id = norm(row.get("prod_id"))
        kuerzel = norm(row.get("kuerzel"))
        start_bft = norm(row.get("start_bft"))
        artikel_nr = norm(row.get("artikel_nr"))
        start_bew = norm(row.get("start_bew"))

        durchmesser = norm(row.get("durchmesser"))
        laenge = norm(row.get("laenge"))
        biegung = norm(row.get("biegung"))
        menge = norm(row.get("menge"))

        # ⭐ Erweiterter merge_key – jede Zeile eindeutig
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

        # ---------------------------------------------------------
        # B) Prüfen, ob Auftrag (ProdID) bereits existiert
        #    → Parkzone hat VORRANG vor merge_key
        # ---------------------------------------------------------
        existing_items_same_prod = db.query(Item).filter(Item.prod_id == prod_id).all()

        if existing_items_same_prod:

            # ⭐ B1: Auftrag ist vollständig in Parkzone → automatische Reaktivierung
            if all(i.verschoben for i in existing_items_same_prod):

                # → Alle alten Items aus Parkzone holen
                for old in existing_items_same_prod:
                    old.verschoben = False
                    old.reaktiviert = True  # ⭐ WICHTIG: Flag setzen

                db.commit()

                warnings.append({
                    "prod_id": prod_id,
                    "kuerzel": kuerzel,
                    "start_bft_alt": existing_items_same_prod[0].start_bft,
                    "start_bft_neu": start_bft,
                    "reason": "Auftrag wurde automatisch aus der Parkzone reaktiviert."
                })

                # → KEIN continue!
                # Upload fährt fort und legt neue Positionen an

            # ⭐ B2: Auftrag existiert, ist aber NICHT in Parkzone
            # → neue Positionen sind erlaubt
            # → merge_key entscheidet später

        # ---------------------------------------------------------
        # A) Prüfen, ob diese Position (merge_key) bereits existiert
        #    (nur wenn Auftrag NICHT in Parkzone ist)
        # ---------------------------------------------------------
        existing_item = db.query(Item).filter(Item.merge_key == merge_key).first()

        if existing_item:
            errors.append({
                "prod_id": prod_id,
                "kuerzel": kuerzel,
                "reason": "Position existiert bereits (merge_key)."
            })
            continue

        # ---------------------------------------------------------
        # C) Position neu anlegen
        # ---------------------------------------------------------
        item = Item()
        db.add(item)
        db.flush()

        # ⭐ merge_key setzen
        item.merge_key = merge_key

        item.fertig = False
        item.kommissioniert = False
        item.ausgeliefert = False

        item.kuerzel = kuerzel
        item.prod_id = prod_id
        item.artikel_nr = artikel_nr
        item.artikel_clean = norm(row.get("artikel_clean"))

        # numerische Felder sicher casten
        item.durchmesser = float(row.get("durchmesser", 0) or 0)
        item.laenge = float(row.get("laenge", 0) or 0)
        item.biegung = norm(row.get("biegung"))

        item.bedarfs_menge_pos = float(row.get("bedarfs_menge_pos", 0) or 0)
        item.menge = float(row.get("menge", 0) or 0)

        item.beschaffung = norm(row.get("beschaffung"))
        item.referenz = norm(row.get("referenz"))

        item.start_bft = start_bft
        item.start_bew = start_bew

    db.commit()
    db.close()

    # ---------------------------------------------------------
    # 5) Wenn Fehler oder Warnungen → Übersicht anzeigen
    # ---------------------------------------------------------
    if errors or warnings:
        return request.app.state.templates.TemplateResponse(
            "upload_summary.html",
            {
                "request": request,
                "errors": errors,
                "warnings": warnings
            }
        )

    # ---------------------------------------------------------
    # 6) Wenn alles ok → normal redirecten
    # ---------------------------------------------------------
    timestamp = datetime.now().strftime("%H:%M")
    return RedirectResponse(f"/?upload_success=1&timestamp={timestamp}", status_code=303)
