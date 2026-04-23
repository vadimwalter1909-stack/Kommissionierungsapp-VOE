from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, FileResponse
import pandas as pd
import json
from datetime import datetime, date

from backend.database_base import SessionLocal
from backend.database import Item
from backend.logic.status import is_done
from backend.logic.completed import mark_as_completed
from backend.utils.arbeitsplatz_loader import load_arbeitsplatz_artikel


# Produktionssignal
from backend.logic.ladungstraeger import load_ladungstraeger
from backend.logic.produktion_state import load_state, save_state

router = APIRouter()

# ---------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------
def load_df() -> pd.DataFrame:
    db = SessionLocal()
    items = db.query(Item).all()
    db.close()

    if not items:
        return pd.DataFrame()

    df = pd.DataFrame([i.__dict__ for i in items])
    df = df.drop(columns=["_sa_instance_state"], errors="ignore")
    return df


def load_ziellagerorte():
    try:
        with open("backend/data/zielorte.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def parse_start_bft(series: pd.Series):
    try:
        dt = pd.to_datetime(series, errors="coerce")
        return dt.dt.date
    except Exception:
        return pd.Series([None] * len(series))


# ---------------------------------------------------------
# LOGISTIK – ÜBERSICHT
# ---------------------------------------------------------
@router.get("/logistik")
def logistik_overview(request: Request):
    df = load_df()

    # Parkzone ausblenden
    if "verschoben" in df.columns:
        df = df[df["verschoben"] != True]

    tiles = []
    if not df.empty:

        # Gruppierung nach (Kürzel, ProdID, Start-BFT)
        for (kuerzel, prod_id, start_bft) in sorted(
            df.groupby(["kuerzel", "prod_id", "start_bft"]).groups.keys(),
            key=lambda x: (x[0], x[1], x[2])
        ):

            # Prozess abgeschlossen?
            # ⭐ Reaktivierte Aufträge trotzdem anzeigen!
            df_all = df[(df["kuerzel"] == kuerzel) & (df["prod_id"] == prod_id)]
            reaktiviert = False
            if "reaktiviert" in df.columns:
                reaktiviert = bool(df_all["reaktiviert"].any())

            # Wenn Auftrag fertig ist → IMMER ausblenden
            if is_done(kuerzel, prod_id, start_bft):
                continue

            # Nur Logistik-relevante Zeilen
            df_k = df[
                (df["kuerzel"] == kuerzel) &
                (df["prod_id"] == prod_id) &
                (df["start_bft"] == start_bft) &
                ~(
                    (df["beschaffung"] == "Produktion") &
                    (df["referenz"] == "Produktion")
                )
            ]

            if df_k.empty:
                continue

            fehlteile_vorhanden = bool((df_k["referenz"] == "Bestellung").any())

            total_buendel = df_k["merge_key"].nunique()
            kommissioniert_buendel = (
                df_k.groupby("merge_key")["kommissioniert"].all().sum()
            )

            kommi_alle = bool(df_k["kommissioniert"].all())
            kommi_einige = bool(df_k["kommissioniert"].any())

            # Statuslogik
            if not kommi_einige:
                status = "grau"; icon = "⏳"
            elif kommi_einige and not kommi_alle:
                status = "gelb"; icon = "🛠"
            elif kommi_alle:
                status = "hellgruen"; icon = "✅"
            else:
                status = "grau"; icon = "⏳"

            tiles.append({
                "kuerzel": kuerzel,
                "prod_id": prod_id,
                "status": status,
                "icon": icon,
                "fehlteile": fehlteile_vorhanden,
                "kritische_fehlteile": False,
                "total": total_buendel,
                "done": kommissioniert_buendel,
                "produktion_fertig": True,
                "start_bft": start_bft,
                "reaktiviert": reaktiviert,
                "verschoben": False,
                "artikel_nr": df_k.iloc[0]["artikel_nr"]
            })

        # Sortierung: Reaktivierte oben
        tiles = sorted(
            tiles,
            key=lambda t: (
                0 if t["reaktiviert"] else 1,
                t["kuerzel"],
                t["prod_id"],
                t["start_bft"]
            )
        )

    # ---------------------------------------------------------
    # PRODUKTIONS-KACHELN (Ladungsträger aus Produktion)
    # ---------------------------------------------------------
    state = load_state()
    lt_list = load_ladungstraeger()

    prod_tiles = []
    for lt in lt_list:
        lt_id = lt["id"]
        if state.get(lt_id) == "fertig":
            prod_tiles.append({
                "id": lt_id,
                "name": lt["name"],
                "status": "fertig",
                "icon": "🚚",
            })

    prod_tiles = sorted(prod_tiles, key=lambda x: int(x["id"].replace("LT", "")))

    return request.app.state.templates.TemplateResponse(
        "logistik.html",
        {
            "request": request,
            "tiles": tiles or [],
            "prod_tiles": prod_tiles or []
        }
    )


    # ---------------------------------------------------------
    # PRODUKTIONS-KACHELN
    # ---------------------------------------------------------
    state = load_state()
    lt_list = load_ladungstraeger()

    prod_tiles = []
    for lt in lt_list:
        lt_id = lt["id"]
        if state.get(lt_id) == "fertig":
            prod_tiles.append({
                "id": lt_id,
                "name": lt["name"],
                "status": "fertig",
                "icon": "🚚",
            })

    prod_tiles = sorted(prod_tiles, key=lambda x: int(x["id"].replace("LT", "")))

    return request.app.state.templates.TemplateResponse(
        "logistik.html",
        {
            "request": request,
            "tiles": tiles or [],
            "prod_tiles": prod_tiles or []
        }
    )
# ---------------------------------------------------------
# KOMMISSIONIEREN
# ---------------------------------------------------------
@router.post("/logistik/kommissioniert")
def logistik_kommissioniert(
    request: Request,
    kuerzel: str = Form(...),
    prod_id: str = Form(...),
    row_keys: list[str] = Form(...),
    start_bft: str = Form(default="")
):
    db = SessionLocal()
    items = db.query(Item).filter(Item.merge_key.in_(row_keys)).all()

    for item in items:
        item.kommissioniert = True
        db.add(item)

    db.commit()
    db.close()

    if is_done(kuerzel, prod_id, start_bft):
        mark_as_completed(kuerzel, prod_id, start_bft)

    return RedirectResponse(
        f"/logistik/{kuerzel}/{prod_id}?start_bft={start_bft}",
        status_code=303
    )


# ---------------------------------------------------------
# FEHLTEIL ERLEDIGT
# ---------------------------------------------------------
@router.post("/logistik/fehlteil_erledigt")
def logistik_nicht_gefunden(
    request: Request,
    kuerzel: str = Form(...),
    prod_id: str = Form(...),
    row_keys: list[str] = Form(...),
    start_bft: str = Form(default="")
):
    db = SessionLocal()

    merge_key = row_keys[0]
    items = db.query(Item).filter(Item.merge_key == merge_key).all()

    for item in items:
        item.referenz = "Nicht gefunden"
        db.add(item)

    db.commit()
    db.close()

    return RedirectResponse(
        f"/logistik/{kuerzel}/{prod_id}?start_bft={start_bft}",
        status_code=303
    )


# ---------------------------------------------------------
# AUSLIEFERN
# ---------------------------------------------------------
@router.post("/logistik/ausliefern")
def logistik_ausliefern(
    request: Request,
    kuerzel: str = Form(...),
    prod_id: str = Form(...),
    row_keys: list[str] = Form(...),
    ziellager: str = Form(default=""),
    start_bft: str = Form(default="")
):
    db = SessionLocal()
    items = db.query(Item).filter(Item.merge_key.in_(row_keys)).all()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for item in items:
        item.ausgeliefert = True
        item.ziel_lagerort = ziellager
        item.ausgeliefert_am = timestamp
        db.add(item)

    db.commit()
    db.close()

    mark_as_completed(kuerzel, prod_id, start_bft)

    return RedirectResponse("/logistik", status_code=303)


# ---------------------------------------------------------
# PARKZONE – VERSCHIEBEN
# ---------------------------------------------------------
@router.post("/logistik/verschieben")
def logistik_verschieben(
    kuerzel: str = Form(...),
    prod_id: str = Form(...),
    start_bft: str = Form(...)
):
    db = SessionLocal()

    db.query(Item).filter(
        Item.kuerzel == kuerzel,
        Item.prod_id == prod_id
    ).update({"verschoben": True})

    db.commit()
    db.close()

    return RedirectResponse("/logistik", status_code=303)


# ---------------------------------------------------------
# PARKZONE – ÜBERSICHT
# ---------------------------------------------------------
@router.get("/parkzone")
def parkzone_overview(request: Request):
    df = load_df()

    if "verschoben" not in df.columns:
        tiles = []
    else:
        df = df[df["verschoben"] == True]

        tiles = []
        for (kuerzel, prod_id, start_bft) in sorted(
            df.groupby(["kuerzel", "prod_id", "start_bft"]).groups.keys(),
            key=lambda x: (x[0], x[1], x[2])
        ):
            tiles.append({
                "kuerzel": kuerzel,
                "prod_id": prod_id,
                "start_bft": start_bft,
                "icon": "🅿️",
                "status": "verschoben"
            })

    return request.app.state.templates.TemplateResponse(
        request=request,
        name="parkzone.html",
        context={
            "request": request,
            "tiles": tiles or [],
        },
    )


# ---------------------------------------------------------
# PARKZONE – REAKTIVIEREN
# ---------------------------------------------------------
@router.post("/parkzone/reaktivieren")
def parkzone_reaktivieren(
    kuerzel: str = Form(...),
    prod_id: str = Form(...),
    start_bft: str = Form(...)
):
    db = SessionLocal()

    db.query(Item).filter(
        Item.kuerzel == kuerzel,
        Item.prod_id == prod_id
    ).update({
        "verschoben": False,
        "reaktiviert": True
    })

    db.commit()
    db.close()

    return RedirectResponse("/logistik", status_code=303)
# ---------------------------------------------------------
# ARBEITSPLATZ-ARTIKEL – SEITE ANZEIGEN
# ---------------------------------------------------------
@router.get("/arbeitsplatz-artikel")
def arbeitsplatz_artikel_page(request: Request):
    data = load_arbeitsplatz_artikel()
    return request.app.state.templates.TemplateResponse(
        "arbeitsplatz_artikel.html",
        {
            "request": request,
            "artikel": data["artikel"]
        }
    )


# ---------------------------------------------------------
# ARBEITSPLATZ-ARTIKEL – HINZUFÜGEN
# ---------------------------------------------------------
@router.post("/arbeitsplatz-artikel/add")
def arbeitsplatz_artikel_add(artikel: str = Form(...)):
    data = load_arbeitsplatz_artikel()

    if artikel not in data["artikel"]:
        data["artikel"].append(artikel)

    with open("backend/data/arbeitsplatz_artikel.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return RedirectResponse("/arbeitsplatz-artikel", status_code=303)


# ---------------------------------------------------------
# ARBEITSPLATZ-ARTIKEL – LÖSCHEN
# ---------------------------------------------------------
@router.post("/arbeitsplatz-artikel/delete")
def arbeitsplatz_artikel_delete(artikel: str = Form(...)):
    data = load_arbeitsplatz_artikel()

    if artikel in data["artikel"]:
        data["artikel"].remove(artikel)

    with open("backend/data/arbeitsplatz_artikel.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return RedirectResponse("/arbeitsplatz-artikel", status_code=303)


# ---------------------------------------------------------
# LOGISTIK – DETAILSEITE
# ---------------------------------------------------------
@router.get("/logistik/{kuerzel}/{prod_id}")
def logistik_detail(request: Request, kuerzel: str, prod_id: str):
    df = load_df()
    ziellagerorte = load_ziellagerorte()

    # ⭐ Arbeitsplatz-Artikel laden
    arbeitsplatz = load_arbeitsplatz_artikel()
    artikel_liste = arbeitsplatz["artikel"]

    start_bft_filter = request.query_params.get("start_bft")
    if not start_bft_filter:
        return RedirectResponse("/logistik", status_code=303)

    df["prod_id"] = df["prod_id"].astype(str)
    prod_id_clean = str(prod_id)

    df_k = df[
        (df["kuerzel"] == kuerzel) &
        (df["prod_id"] == prod_id_clean) &
        (df["start_bft"] == start_bft_filter)
    ].copy()

    if df_k.empty:
        return request.app.state.templates.TemplateResponse(
            "logistik_detail.html",
            {
                "request": request,
                "kuerzel": kuerzel,
                "prod_id": prod_id,
                "groups": [],
                "ziellagerorte": ziellagerorte,
                "produktion_fertig": True,
                "prod_ladungstraeger": None,
                "log_ladungstraeger": None,
                "start_bft": start_bft_filter,
            }
        )

        # ---------------------------------------------------------
    # LOGISTIK-GRUPPEN
    # ---------------------------------------------------------
    df_groups = df_k[
        ~(
            (df_k["beschaffung"].astype(str).str.strip() == "Produktion") &
            (df_k["referenz"].astype(str).str.strip() == "Produktion")
        )
    ].copy()

    df_groups["durchmesser"] = pd.to_numeric(df_groups.get("durchmesser", 0), errors="coerce").fillna(0.0)
    df_groups["laenge"] = pd.to_numeric(df_groups.get("laenge", 0), errors="coerce").fillna(0.0)
    df_groups["biegung"] = df_groups.get("biegung", "").astype(str).replace({"nan": "unbekannt", "": "unbekannt"})
    df_groups["artikel_nr"] = df_groups.get("artikel_nr", "").astype(str).replace({"nan": "?", "": "?"})
    df_groups["artikel_clean"] = df_groups.get("artikel_clean", "").astype(str).replace({"nan": "?", "": "?"})
    df_groups["start_bft"] = df_groups.get("start_bft", "").astype(str)

    groups = []

    group_cols = ["kuerzel", "artikel_clean", "artikel_nr", "durchmesser", "laenge", "biegung", "start_bft"]

    for keys, df_art in df_groups.groupby(group_cols):
        (
            kuerzel_val,
            artikel_clean,
            artikel_nr,
            durchmesser,
            laenge,
            biegung,
            start_bft_val,
        ) = keys

        referenzen = df_art["referenz"].astype(str).str.strip().unique()

        bestellung = any(ref == "Bestellung" for ref in referenzen)

        kommissioniert = bool(df_art["kommissioniert"].all())
        ausgeliefert = bool(df_art["ausgeliefert"].all())
        am_lager = all(ref == "Am Lager" for ref in referenzen)

        # ⭐ NEU: Normalisierung für Arbeitsplatz-Abgleich
        artikel_nr_norm = str(artikel_nr).strip().lower()
        artikel_clean_norm = str(artikel_clean).strip().lower()

        # ⭐ NEU: Bew.-Artikel aus Excel (falls vorhanden)
        bew_artikel_series = df_art.get("bew_artikel")
        if bew_artikel_series is None:
            bew_artikel_series = df_art.get("Bew.-Artikel")
        if bew_artikel_series is not None and len(bew_artikel_series) > 0:
            bew_artikel = str(bew_artikel_series.iloc[0])
        else:
            bew_artikel = ""
        bew_artikel_norm = bew_artikel.strip().lower()

        arbeitsplatz_norm = [str(a).strip().lower() for a in artikel_liste]

        liegt_am_arbeitsplatz = (
            artikel_nr_norm in arbeitsplatz_norm
            or artikel_clean_norm in arbeitsplatz_norm
            or bew_artikel_norm in arbeitsplatz_norm
        )

        groups.append({
            "artikel_clean": artikel_clean,
            "artikel_nr": artikel_nr,
            "durchmesser": float(durchmesser),
            "laenge": float(laenge),
            "biegung": biegung,
            "menge": int(df_art["bedarfs_menge_pos"].abs().sum()),
            "prod_ids": sorted(df_art["prod_id"].unique()),
            "row_keys": sorted(df_art["merge_key"].astype(str).unique()),
            "kommissioniert": kommissioniert,
            "ausgeliefert": ausgeliefert,
            "am_lager": am_lager,
            "fehlteil": bestellung,
            "kritisch_fehlteil": False,
            "start_bft": start_bft_val,
            "liegt_am_arbeitsplatz": liegt_am_arbeitsplatz,
        })

    groups = sorted(groups, key=lambda g: (g["durchmesser"], g["laenge"]))

    # ---------------------------------------------------------
    # LOGISTIK-LADUNGSTRÄGER
    # ---------------------------------------------------------
    log_ladungstraeger = None

    alle_relevant_kommissioniert = all(
        (g["kommissioniert"] or g["ausgeliefert"]) for g in groups
    )
    alle_relevant_ausgeliefert = all(
        g["ausgeliefert"] for g in groups
    )

    if alle_relevant_kommissioniert and not alle_relevant_ausgeliefert:
        menge_summe = sum(g["menge"] for g in groups)
        all_row_keys = sorted({rk for g in groups for rk in g["row_keys"]})
        all_prod_ids = sorted({pid for g in groups for pid in g["prod_ids"]})

        log_ladungstraeger = {
            "menge": int(menge_summe),
            "row_keys": all_row_keys,
            "prod_ids": all_prod_ids
        }

    return request.app.state.templates.TemplateResponse(
        "logistik_detail.html",
        {
            "request": request,
            "kuerzel": kuerzel,
            "prod_id": prod_id,
            "groups": groups,
            "ziellagerorte": ziellagerorte,
            "produktion_fertig": True,
            "prod_ladungstraeger": None,
            "log_ladungstraeger": log_ladungstraeger,
            "start_bft": start_bft_filter,
        }
    )
