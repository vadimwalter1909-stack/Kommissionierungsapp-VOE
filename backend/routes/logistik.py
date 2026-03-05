from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, FileResponse
import pandas as pd
import json
from datetime import datetime, date

from backend.database_base import SessionLocal
from backend.database import Item
from backend.logic.status import is_done
from backend.logic.completed import mark_as_completed

# Produktionssignal
from backend.logic.ladungstraeger import LADUNGSTRAEGER
from backend.logic.produktion_state import load_state, save_state

router = APIRouter()
print(">>> LOGISTIK.PY WURDE GELADEN <<<")

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

    if df.empty:
        tiles = []
    else:
        tiles = []
        today = date.today()

        # NEU: Gruppierung nach (Kürzel, ProdID, Start-BFT)
        for (kuerzel, prod_id, start_bft) in sorted(
            df.groupby(["kuerzel", "prod_id", "start_bft"]).groups.keys(),
            key=lambda x: (x[0], x[1], x[2])
        ):

            # Prozess abgeschlossen?
            if is_done(kuerzel, prod_id, start_bft):
                continue

            # Relevante Logistikdaten
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
                "start_bft": start_bft
            })

        tiles = sorted(tiles, key=lambda t: (t["kuerzel"], t["prod_id"], t["start_bft"]))

    # Produktions-Kacheln
    state = load_state()
    prod_tiles = [
        {"id": lt["id"], "name": lt["name"]}
        for lt in LADUNGSTRAEGER
        if state.get(lt["id"]) == "fertig"
    ]

    return request.app.state.templates.TemplateResponse(
        "logistik.html",
        {
            "request": request,
            "tiles": tiles,
            "prod_tiles": prod_tiles
        }
    )


# ---------------------------------------------------------
# LOGISTIK – DETAILSEITE
# ---------------------------------------------------------
@router.get("/logistik/{kuerzel}/{prod_id}")
def logistik_detail(request: Request, kuerzel: str, prod_id: str):
    df = load_df()
    ziellagerorte = load_ziellagerorte()

    start_bft_filter = request.query_params.get("start_bft")

    # NEU: Filter nach ProdID
    df_k = df[
        (df["kuerzel"] == kuerzel) &
        (df["prod_id"] == prod_id)
    ].copy()

    if start_bft_filter:
        df_k = df_k[df_k["start_bft"] == start_bft_filter]

    produktion_fertig = True
    prod_ladungstraeger = None

    # Logistik-Gruppen
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

        fehlteil = bestellung

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
            "fehlteil": fehlteil,
            "kritisch_fehlteil": False,
            "start_bft": start_bft_val,
        })

    groups = sorted(groups, key=lambda g: (g["durchmesser"], g["laenge"]))

    # Logistik-Ladungsträger
    alle_relevant_kommissioniert = False
    alle_relevant_ausgeliefert = False
    log_ladungstraeger = None

    if groups:
        relevante = groups

        alle_relevant_kommissioniert = all(
            (g["kommissioniert"] or g["ausgeliefert"]) for g in relevante
        )
        alle_relevant_ausgeliefert = all(
            g["ausgeliefert"] for g in relevante
        )

        if alle_relevant_kommissioniert and not alle_relevant_ausgeliefert:
            menge_summe = sum(g["menge"] for g in relevante)
            all_row_keys = sorted({rk for g in relevante for rk in g["row_keys"]})
            all_prod_ids = sorted({pid for g in relevante for pid in g["prod_ids"]})

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
            "produktion_fertig": produktion_fertig,
            "prod_ladungstraeger": prod_ladungstraeger,
            "log_ladungstraeger": log_ladungstraeger,
            "start_bft": start_bft_filter or "",
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

    # Prozess abgeschlossen → Kachel verschwindet aus Übersicht
    mark_as_completed(kuerzel, prod_id, start_bft)

    return RedirectResponse("/logistik", status_code=303)


# ---------------------------------------------------------
# FEHLTEILE-ÜBERSICHT
# ---------------------------------------------------------
@router.get("/fehlteile")
def fehlteile_overview(request: Request):
    df = load_df()

    if "ausgebucht" not in df.columns:
        fehlteile = []
    else:
        df = df[df["ausgebucht"] == True]

        if df.empty:
            fehlteile = []
        else:
            group_cols = [
                "kuerzel",
                "artikel_nr",
                "artikel_clean",
                "durchmesser",
                "laenge",
                "biegung",
                "merge_key"
            ]

            df_grouped = (
                df.groupby(group_cols)
                .agg({
                    "bedarfs_menge_pos": "sum",
                    "prod_id": lambda x: ", ".join(sorted(set(x.astype(str)))),
                    "ausgebucht_am": "first",
                    "start_bft": "first"
                })
                .reset_index()
            )

            fehlteile = df_grouped.to_dict(orient="records")

    return request.app.state.templates.TemplateResponse(
        "fehlteile.html",
        {"request": request, "fehlteile": fehlteile}
    )
