from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
import pandas as pd

from backend.database_base import SessionLocal
from backend.database import Item
from backend.logic.status import is_done


router = APIRouter()


# ---------------------------------------------------------
# HILFSFUNKTION: DataFrame laden
# ---------------------------------------------------------
def load_df() -> pd.DataFrame:
    db = SessionLocal()
    items = db.query(Item).all()
    db.close()

    if not items:
        return pd.DataFrame()

    df = pd.DataFrame([i.__dict__ for i in items])
    df = df.drop(columns=["_sa_instance_state"], errors="ignore")

    # WICHTIG: fertig als bool casten
    if "fertig" in df.columns:
        df["fertig"] = df["fertig"].astype(bool)

    return df


# ---------------------------------------------------------
# PRODUKTION – ÜBERSICHT
# ---------------------------------------------------------
@router.get("/produktion")
def produktion_overview(request: Request):
    df = load_df()

    if df.empty:
        tiles = []
    else:
        tiles = []

        for (kuerzel, start_bft) in sorted(
                df.groupby(["kuerzel", "start_bft"]).groups.keys(),
                key=lambda x: (x[0], x[1])  # alphabetisch, dann Datum aufsteigend
            ):

            # TAGESSCHARFE DONE-PRÜFUNG (WICHTIG!)
            if is_done(kuerzel, start_bft):
                continue

            df_k = df[
                (df["kuerzel"] == kuerzel) &
                (df["start_bft"] == start_bft) &
                (df["beschaffung"] == "Produktion") &
                (df["referenz"] == "Produktion")
            ]

            if df_k.empty:
                continue

            total_buendel = df_k["merge_key"].nunique()
            fertig_buendel = df_k.groupby("merge_key")["fertig"].all().sum()

            fertig_alle = bool(df_k["fertig"].all())
            fertig_einige = bool(df_k["fertig"].any())

            if fertig_alle:
                status = "gruen"
                icon = "✔"
            elif fertig_einige:
                status = "gelb"
                icon = "🛠"
            else:
                status = "grau"
                icon = "⏳"

            start_bft = df_k["start_bft"].iloc[0] if "start_bft" in df_k.columns else ""

            tiles.append({
                "kuerzel": kuerzel,
                "status": status,
                "icon": icon,
                "total": total_buendel,
                "done": fertig_buendel,
                "start_bft": start_bft
            })

        tiles = sorted(tiles, key=lambda t: (t["kuerzel"], t["start_bft"]))

    return request.app.state.templates.TemplateResponse(
        "produktion.html",
        {"request": request, "tiles": tiles}
    )


# ---------------------------------------------------------
# PRODUKTION – DETAILSEITE (TAGESSCHARF + KÜRZEL-SCHARF)
# ---------------------------------------------------------
@router.get("/produktion/{kuerzel}")
def produktion_detail(request: Request, kuerzel: str):
    df = load_df()

    start_bft = request.query_params.get("start_bft")

    df_k = df[
        (df["kuerzel"] == kuerzel) &
        (df["beschaffung"] == "Produktion") &
        (df["referenz"] == "Produktion")
    ]

    if start_bft:
        df_k = df_k[df_k["start_bft"] == start_bft]

    if df_k.empty:
        groups = []
    else:
        groups = []

        # NARRSICHER: Kürzel + Artikel + Maße + Biegung + Datum
        group_cols = ["kuerzel", "artikel_clean", "durchmesser", "laenge", "biegung", "start_bft"]

        for keys, df_art in df_k.groupby(group_cols):
            (
                kuerzel_val,
                artikel_clean,
                durchmesser,
                laenge,
                biegung,
                start_bft_val
            ) = keys

            print("DEBUG BÜNDEL:", keys)
            print(df_art[["merge_key", "artikel_clean", "durchmesser", "laenge", "biegung", "start_bft", "fertig"]])


            groups.append({
                "artikel_clean": artikel_clean,
                "artikel_nr": df_art["artikel_nr"].iloc[0],
                "durchmesser": float(durchmesser),
                "laenge": float(laenge),
                "biegung": biegung,
                "menge": int(df_art["bedarfs_menge_pos"].abs().sum()),
                "prod_ids": sorted(df_art["prod_id"].unique()),
                "row_keys": list(df_art["merge_key"].astype(str)),
                "fertig": bool(df_art["fertig"].all()),
                "start_bft": start_bft_val,
            })

        groups = sorted(groups, key=lambda g: (g["durchmesser"], g["laenge"]))

    return request.app.state.templates.TemplateResponse(
        "produktion_detail.html",
        {"request": request, "kuerzel": kuerzel, "groups": groups, "start_bft": start_bft}
    )


# ---------------------------------------------------------
# PRODUKTION – BÜNDEL ALS FERTIG MELDEN
# ---------------------------------------------------------
@router.post("/produktion/buendel_fertig")
def produktion_buendel_fertig(
    request: Request,
    kuerzel: str = Form(...),
    row_keys: list[str] = Form(...),
    start_bft: str = Form("")
):
    db = SessionLocal()

    for key in row_keys:
        item = db.query(Item).filter(Item.merge_key == key).first()
        if item:
            item.fertig = True
            db.add(item)

    db.commit()
    db.close()

    if start_bft:
        return RedirectResponse(f"/produktion/{kuerzel}?start_bft={start_bft}", status_code=303)

    return RedirectResponse(f"/produktion/{kuerzel}", status_code=303)
