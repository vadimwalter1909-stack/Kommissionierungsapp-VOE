from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse, FileResponse
import pandas as pd
import json
from datetime import datetime, date

from backend.database_base import SessionLocal
from backend.database import Item
from backend.logic.status import is_done
from backend.logic.completed import mark_as_completed


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

    if df.empty:
        tiles = []
    else:
        tiles = []
        today = date.today()
        
        for (kuerzel, start_bft) in sorted(
                df.groupby(["kuerzel", "start_bft"]).groups.keys(),
                key=lambda x: (x[0], x[1])  # alphabetisch, dann Datum aufsteigend
            ):

            # TAGESSCHARFE DONE-PRÜFUNG (WICHTIG!)
            if is_done(kuerzel, start_bft):
                mark_as_completed(kuerzel, start_bft)
                continue

            df_k = df[
                (df["kuerzel"] == kuerzel) &
                (df["start_bft"] == start_bft) &
                ~(
                    (df["beschaffung"] == "Produktion") &
                    (df["referenz"] == "Produktion")
                )
            ]

            if df_k.empty:
                continue

            # Nur Hinweis, keine Blockade
            fehlteile_vorhanden = bool((df_k["referenz"] == "Bestellung").any())

            # Keine kritischen Fehlteile mehr
            kritische_fehlteile = False

            total_buendel = df_k["merge_key"].nunique()
            kommissioniert_buendel = (
                df_k.groupby("merge_key")["kommissioniert"].all().sum()
            )

            df_prod = df[
                (df["kuerzel"] == kuerzel) &
                (df["start_bft"] == start_bft) &
                (df["beschaffung"] == "Produktion") &
                (df["referenz"] == "Produktion")
            ]

            produktion_fertig = df_prod.empty or bool(df_prod["fertig"].all())

            kommi_alle = bool(df_k["kommissioniert"].all())
            kommi_einige = bool(df_k["kommissioniert"].any())

            if not kommi_einige:
                status = "grau"; icon = "⏳"
            elif kommi_einige and not kommi_alle:
                status = "gelb"; icon = "🛠"
            elif kommi_alle and not produktion_fertig:
                status = "hellblau"; icon = "📦"
            elif kommi_alle and produktion_fertig:
                status = "hellgruen"; icon = "✅"
            else:
                status = "grau"; icon = "⏳"

            tiles.append({
                "kuerzel": kuerzel,
                "status": status,
                "icon": icon,
                "fehlteile": fehlteile_vorhanden,
                "kritische_fehlteile": False,
                "total": total_buendel,
                "done": kommissioniert_buendel,
                "produktion_fertig": produktion_fertig,
                "start_bft": df_k["start_bft"].iloc[0] if "start_bft" in df_k.columns else ""
            })
        
        tiles = sorted(tiles, key=lambda t: (t["kuerzel"], t["start_bft"]))

    return request.app.state.templates.TemplateResponse(
        "logistik.html",
        {"request": request, "tiles": tiles}
    )


# ---------------------------------------------------------
# LOGISTIK – DETAILSEITE (TAGESSCHARF & BÜNDELSCHARF)
# ---------------------------------------------------------
@router.get("/logistik/{kuerzel}")
def logistik_detail(request: Request, kuerzel: str):
    df = load_df()
    ziellagerorte = load_ziellagerorte()

    start_bft_filter = request.query_params.get("start_bft")

    df_k = df[df["kuerzel"] == kuerzel].copy()

    if start_bft_filter:
        df_k = df_k[df_k["start_bft"] == start_bft_filter]

    # ---------------------------------------------------------
    # PRODUKTIONS-LADUNGSTRÄGER
    # ---------------------------------------------------------
    df_prod = df_k[
        (df_k["beschaffung"].astype(str).str.strip() == "Produktion") &
        (df_k["referenz"].astype(str).str.strip() == "Produktion")
    ]

    if df_prod.empty:
        produktion_fertig = False
        prod_ladungstraeger = None
    else:
        produktion_fertig = bool(df_prod["fertig"].all())
        prod_ladungstraeger = {
            "menge": int(df_prod["bedarfs_menge_pos"].abs().sum()),
            "row_keys": sorted(df_prod["merge_key"].astype(str).unique()),
            "prod_ids": sorted(df_prod["prod_id"].unique()),
            "ziel_lagerort": df_prod["ziel_lagerort"].iloc[0] if "ziel_lagerort" in df_prod else "",
            "ausgeliefert": bool(df_prod["ausgeliefert"].all()),
            "ausgeliefert_am": df_prod["ausgeliefert_am"].iloc[0] if "ausgeliefert_am" in df_prod else ""
        }

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

        # Nur Hinweis
        fehlteil = bestellung
        kritisch_fehlteil = False

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
    # ---------------------------------------------------------
    # LOGISTIK-LADUNGSTRÄGER (sobald ALLE kommissioniert)
    # ---------------------------------------------------------
    alle_relevant_kommissioniert = False
    alle_relevant_ausgeliefert = False
    log_ladungstraeger = None

    if groups:
        # Alle Gruppen sind relevant (keine kritischen Fehlteile mehr)
        relevante = groups

        alle_relevant_kommissioniert = all(
            (g["kommissioniert"] or g["ausgeliefert"]) for g in relevante
        )
        alle_relevant_ausgeliefert = all(
            g["ausgeliefert"] for g in relevante
        )

        # Ladungsträger erscheint, sobald alles kommissioniert ist
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

    # TAGESSCHARFE DONE-PRÜFUNG
    if is_done(kuerzel, start_bft):
        mark_as_completed(kuerzel, start_bft)

    # Immer zur tagesscharfen Detailseite zurück
    return RedirectResponse(
        f"/logistik/{kuerzel}?start_bft={start_bft}",
        status_code=303
    )


# ---------------------------------------------------------
# "NICHT GEFUNDEN"
# ---------------------------------------------------------
@router.post("/logistik/fehlteil_erledigt")
def logistik_nicht_gefunden(
    request: Request,
    kuerzel: str = Form(...),
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

    if start_bft:
        return RedirectResponse(f"/logistik/{kuerzel}?start_bft={start_bft}", status_code=303)

    return RedirectResponse(f"/logistik/{kuerzel}", status_code=303)


# ---------------------------------------------------------
# AUSLIEFERN
# ---------------------------------------------------------
@router.post("/logistik/ausliefern")
def logistik_ausliefern(
    request: Request,
    kuerzel: str = Form(...),
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

    # TAGESSCHARFE DONE-PRÜFUNG
    if is_done(kuerzel, start_bft):
        mark_as_completed(kuerzel, start_bft)

    # Immer zur tagesscharfen Detailseite zurück
    return RedirectResponse(
        f"/logistik/{kuerzel}?start_bft={start_bft}",
        status_code=303
    )

# ---------------------------------------------------------
# EXPORT: AUSGEBUCHTE FEHLTEILE (Excel)
# ---------------------------------------------------------
@router.get("/export/fehlteile")
def export_fehlteile(request: Request):
    df = load_df()

    if "ausgebucht" not in df.columns:
        return RedirectResponse("/fehlteile", status_code=303)

    df = df[df["ausgebucht"] == True]

    if df.empty:
        return RedirectResponse("/fehlteile", status_code=303)

    group_cols = ["kuerzel", "artikel_nr", "artikel_clean", "durchmesser", "laenge", "biegung", "merge_key"]
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

    filename = f"fehlteile_{date.today().isoformat()}.xlsx"
    filepath = f"/tmp/{filename}"

    df_grouped.to_excel(filepath, index=False)

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ---------------------------------------------------------
# ÜBERSICHT: AUSGEBUCHTE FEHLTEILE
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
            group_cols = ["kuerzel", "artikel_nr", "artikel_clean", "durchmesser", "laenge", "biegung", "merge_key"]
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
