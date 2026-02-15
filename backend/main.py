from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse

import pandas as pd
from pathlib import Path
from datetime import datetime

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR.parent / "frontend" / "templates"
STATIC_DIR = BASE_DIR.parent / "frontend" / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.state.df_original = None
app.state.produktion_tiles = []
app.state.logistik_tiles = []

# Zielorte aus JSON laden
import json

ZIELORTE_PATH = BASE_DIR / "data" / "zielorte.json"

if ZIELORTE_PATH.exists():
    with open(ZIELORTE_PATH, "r", encoding="utf-8") as f:
        app.state.zielorte = json.load(f)
else:
    app.state.zielorte = []
# ---------------------------------------------------------
# LOGISTIK – Tiles erzeugen
# ---------------------------------------------------------
def build_logistics_tiles(df):
    tiles = []

    kuerzel_list = df["Kuerzel_clean"].dropna().unique()

    for k in kuerzel_list:
        df_k = df[df["Kuerzel_clean"] == k]

        prod_mask = (df_k["Beschaffung"] == "Produktion") & (df_k["Referenz"] == "Produktion")
        log_mask  = (df_k["Referenz"] == "Am Lager")

        hat_prod = df_k[prod_mask].shape[0] > 0
        hat_log  = df_k[log_mask].shape[0] > 0

        # Wenn keine Produktion und keine Logistik → ignorieren
        if not hat_prod and not hat_log:
            continue

        # PRODUKTION
        prod_fertig = df_k[prod_mask]["fertig"].all() if hat_prod else True
        prod_ausgeliefert = df_k[prod_mask]["ausgeliefert"].all() if hat_prod else True

        # LOGISTIK
        log_fertig = df_k[log_mask]["fertig"].all() if hat_log else True
        log_ausgeliefert = df_k[log_mask]["ausgeliefert"].all() if hat_log else True

        # ---------------------------------------------------------
        # NEUE, NARRENSICHERE LOGIK
        # ---------------------------------------------------------

        # Zustand E – komplett abgeschlossen
        if prod_fertig and log_fertig and prod_ausgeliefert and log_ausgeliefert:
            status = "komplett"
            icon = "✔️"

        # Zustand D – alles fertig, aber noch nicht ausgeliefert
        elif prod_fertig and log_fertig and not (prod_ausgeliefert and log_ausgeliefert):
            status = "warten_auf_auslieferung"
            icon = "📦📦"

        # Zustand C – Produktion fertig, Logistik NICHT fertig
        elif prod_fertig and not log_fertig:
            status = "logistik_muss"
            icon = "🏭📦"

        # Zustand B – Logistik fertig, Produktion NICHT fertig
        elif log_fertig and not prod_fertig:
            status = "warten_auf_produktion"
            icon = "📦"

        # Zustand A – nichts fertig
        else:
            status = "offen"
            icon = "⏳"

        tiles.append({
            "kuerzel": k,
            "status": status,
            "icon": icon
        })

    return tiles


# ---------------------------------------------------------
# Data Preparation
# ---------------------------------------------------------
def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:

    # ProdID BFT robust bereinigen
    df["ProdID BFT"] = (
        df["ProdID BFT"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("\u202f", "", regex=False)
        .str.replace("\xa0", "", regex=False)
        .str.strip()
    )

    # Weitere Spalten bereinigen
    df["Artikel-Nr. BFT"] = df["Artikel-Nr. BFT"].astype(str).str.strip()
    df["Kürzel"] = df["Kürzel"].astype(str).str.strip()
    df["Bew.-Artikel"] = df["Bew.-Artikel"].astype(str).str.strip()
    df["Beschaffung"] = df["Beschaffung"].astype(str).str.strip()
    df["Referenz"] = df["Referenz"].astype(str).str.strip()

    # ProdID_clean setzen
    df["ProdID_clean"] = df["ProdID BFT"]

    df["Kuerzel_clean"] = df["Kürzel"].str.replace("CP-", "", regex=False).str.strip()
    df["ArtikelNr_clean"] = df["Artikel-Nr. BFT"]

    df = df.reset_index(drop=True)
    df["row_key"] = df.index.astype(str)

    if "fertig" not in df.columns:
        df["fertig"] = False

    # Durchmesser bereinigen
    if "Durchm." in df.columns:
        df["Durchm."] = (
            df["Durchm."]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .str.replace("mm", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace("\u202f", "", regex=False)
            .str.replace("\xa0", "", regex=False)
            .str.strip()
        )
        df["Durchm."] = pd.to_numeric(df["Durchm."], errors="coerce")

    # Länge bereinigen
    if "Länge" in df.columns:
        df["Länge"] = pd.to_numeric(df["Länge"], errors="coerce")

    # Bedarfs-Menge bereinigen
    if "Bedarfs-Menge" in df.columns:
        df["Bedarfs-Menge"] = (
            df["Bedarfs-Menge"]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .str.strip()
        )
        df["Bedarfs-Menge"] = pd.to_numeric(df["Bedarfs-Menge"], errors="coerce")
        df["Bedarfs_Menge_pos"] = df["Bedarfs-Menge"].abs()
    else:
        df["Bedarfs_Menge_pos"] = 1

    return df


# ---------------------------------------------------------
# Tiles – Produktion
# ---------------------------------------------------------
def build_production_tiles(df: pd.DataFrame):
    df_prod = df[
        (df["Beschaffung"] == "Produktion") &
        (df["Referenz"] == "Produktion")
    ].copy()

    tiles = []
    for kuerzel, gruppe in df_prod.groupby("Kuerzel_clean"):
        total_positions = len(gruppe)
        done_positions = gruppe["fertig"].sum()
        anzahl_auftraege = gruppe["ProdID_clean"].nunique()

        if done_positions == 0:
            status = "offen"
        elif done_positions == total_positions:
            status = "fertig"
        else:
            status = "teilweise"

        tiles.append({
            "kuerzel": kuerzel,
            "anzahl_auftraege": anzahl_auftraege,
            "anzahl_positionen": total_positions,
            "fertige_positionen": int(done_positions),
            "status": status,
        })

    return sorted(tiles, key=lambda x: x["kuerzel"])


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---------------------------------------------------------
# Excel Upload – NEUE VERSION
# ---------------------------------------------------------
@app.post("/upload_excel")
async def upload_excel(request: Request, file: UploadFile = File(...)):
    df = pd.read_excel(file.file)
    df = prepare_dataframe(df)
    # Neue Spalten für Logistik-Zielorte
    if "zielort" not in df.columns:
        df["zielort"] = None

    if "ausgeliefert" not in df.columns:
        df["ausgeliefert"] = False


    app.state.df_original = df
    app.state.produktion_tiles = build_production_tiles(df)
    app.state.logistik_tiles = build_logistics_tiles(df)

    timestamp = datetime.now().strftime("%d.%m.%Y – %H:%M:%S")
    pos_count = len(df)

    return RedirectResponse(
        f"/?upload=success&ts={timestamp}&pos={pos_count}",
        status_code=303
    )
# ---------------------------------------------------------
# PRODUKTION – Übersicht
# ---------------------------------------------------------
@app.get("/produktion", response_class=HTMLResponse)
def produktion_overview(request: Request):
    tiles = app.state.produktion_tiles if app.state.df_original is not None else []
    return templates.TemplateResponse("produktion.html", {"request": request, "tiles": tiles})


# ---------------------------------------------------------
# PRODUKTION – Detailseite
# ---------------------------------------------------------
@app.get("/produktion/{kuerzel}", response_class=HTMLResponse)
def produktion_detail(request: Request, kuerzel: str):
    df = app.state.df_original
    if df is None:
        return RedirectResponse("/", status_code=303)

    df_prod = df[
        (df["Kuerzel_clean"] == kuerzel) &
        (df["Beschaffung"] == "Produktion") &
        (df["Referenz"] == "Produktion")
    ].copy()

    if df_prod.empty:
        groups = []
    else:
        grouped = (
            df_prod
            .groupby(["Bew.-Artikel", "Durchm.", "Länge"], dropna=False)
            .agg(
                row_keys=("row_key", list),
                fertig_sum=("fertig", "sum"),
                total_menge=("Bedarfs_Menge_pos", "sum"),
            )
            .reset_index()
        )

        def bundle_status(row):
            if row["fertig_sum"] == 0:
                return "offen"
            if row["fertig_sum"] == len(row["row_keys"]):
                return "fertig"
            return "teilweise"

        grouped["status"] = grouped.apply(bundle_status, axis=1)

        grouped = grouped.sort_values(
            by=["Durchm.", "Länge", "Bew.-Artikel"],
            ascending=[True, True, True]
        )

        groups = []
        for _, row in grouped.iterrows():
            df_bundle = df_prod[
                (df_prod["Bew.-Artikel"] == row["Bew.-Artikel"]) &
                (df_prod["Durchm."] == row["Durchm."]) &
                (df_prod["Länge"] == row["Länge"])
            ]

            prodid_counts = (
                df_bundle
                .groupby("ProdID_clean", dropna=False)["Bedarfs_Menge_pos"]
                .sum()
                .to_dict()
            )

            prodid_list = [
                {"prodid": pid, "anzahl": int(menge)}
                for pid, menge in prodid_counts.items()
            ]

            groups.append({
                "bew_artikel": row["Bew.-Artikel"],
                "durchmesser": row["Durchm."],
                "laenge": row["Länge"],
                "anzahl_stk": int(row["total_menge"]),
                "prodids": prodid_list,
                "row_keys": row["row_keys"],
                "status": row["status"],
            })

    return templates.TemplateResponse(
        "produktion_detail.html",
        {"request": request, "kuerzel": kuerzel, "groups": groups}
    )


# ---------------------------------------------------------
# PRODUKTION – Bündel fertig melden
# ---------------------------------------------------------
@app.post("/produktion/buendel_fertig")
async def produktion_buendel_fertig(
    request: Request,
    kuerzel: str = Form(...),
    row_keys: list[str] = Form(...)
):
    df = app.state.df_original
    if df is None:
        return RedirectResponse("/", status_code=303)

    df.loc[df["row_key"].isin(row_keys), "fertig"] = True

    app.state.produktion_tiles = build_production_tiles(df)
    app.state.logistik_tiles = build_logistics_tiles(df)

    return RedirectResponse(f"/produktion/{kuerzel}", status_code=303)
# ---------------------------------------------------------
# LOGISTIK – Bündel fertig melden
# ---------------------------------------------------------
@app.post("/logistik/buendel_fertig")
async def logistik_buendel_fertig(
    request: Request,
    kuerzel: str = Form(...),
    row_keys: list[str] = Form(...)
):
    df = app.state.df_original
    if df is None:
        return RedirectResponse("/", status_code=303)

    # Markiere die Positionen als fertig
    df.loc[df["row_key"].isin(row_keys), "fertig"] = True

    # Tiles neu berechnen
    app.state.produktion_tiles = build_production_tiles(df)
    app.state.logistik_tiles = build_logistics_tiles(df)

    # Zurück zur Detailseite
    return RedirectResponse(f"/logistik/{kuerzel}", status_code=303)


# ---------------------------------------------------------
# LOGISTIK – Übersicht
# ---------------------------------------------------------
@app.get("/logistik", response_class=HTMLResponse)
def logistik_overview(request: Request):
    df = app.state.df_original
    if df is None:
        return RedirectResponse("/", status_code=303)

    # Produktion neu berechnen (WICHTIG!)
    app.state.produktion_tiles = build_production_tiles(df)

    # Logistik neu berechnen
    tiles = build_logistics_tiles(df)

    return templates.TemplateResponse(
        "logistik.html",
        {"request": request, "tiles": tiles}
    )

# ---------------------------------------------------------
# LOGISTIK – Detailseite (narrensicher umgebaut)
# ---------------------------------------------------------
@app.get("/logistik/{kuerzel}", response_class=HTMLResponse)
def logistik_detail(request: Request, kuerzel: str):
    df = app.state.df_original
    if df is None:
        return RedirectResponse("/", status_code=303)

    df_k = df[df["Kuerzel_clean"] == kuerzel]

    # ---------------------------------------------------------
    # 1) PRODUKTIONS-ARTIKEL ERKENNEN
    # ---------------------------------------------------------
    df_prod = df_k[
        (df_k["Beschaffung"] == "Produktion") &
        (df_k["Referenz"] == "Produktion")
    ].copy()

    hat_prod = not df_prod.empty

    # Produktions-Ladungsträger erst anzeigen, wenn ALLE fertig
    if hat_prod:
        prod_fertig = df_prod["fertig"].all()
        prod_ausgeliefert = df_prod["ausgeliefert"].all()
    else:
        prod_fertig = False
        prod_ausgeliefert = False

    zielort_prod = None
    if prod_ausgeliefert:
        zielort_series = df_prod["zielort"].dropna().unique()
        if len(zielort_series) > 0:
            zielort_prod = zielort_series[0]

    # Produktions-Bündel für Anzeige
    if hat_prod:
        prod_buendel = (
            df_prod.groupby("ProdID_clean")["Bedarfs_Menge_pos"]
            .sum()
            .reset_index()
            .rename(columns={"ProdID_clean": "prodid", "Bedarfs_Menge_pos": "anzahl"})
            .to_dict(orient="records")
        )
    else:
        prod_buendel = []

    # ---------------------------------------------------------
    # 2) LOGISTIK-ARTIKEL ERKENNEN (Referenz = Am Lager)
    # ---------------------------------------------------------
    df_log = df_k[df_k["Referenz"] == "Am Lager"].copy()
    hat_log = not df_log.empty

    if hat_log:
        log_fertig = df_log["fertig"].all()
        log_ausgeliefert = df_log["ausgeliefert"].all()
    else:
        log_fertig = False
        log_ausgeliefert = False

    zielort_log = None
    if log_ausgeliefert:
        zielort_series = df_log["zielort"].dropna().unique()
        if len(zielort_series) > 0:
            zielort_log = zielort_series[0]

    # Logistik-Bündel für Anzeige
    if hat_log:
        log_buendel = (
            df_log.groupby("Bew.-Artikel")["Bedarfs_Menge_pos"]
            .sum()
            .reset_index()
            .rename(columns={"Bew.-Artikel": "bew_artikel", "Bedarfs_Menge_pos": "anzahl"})
            .to_dict(orient="records")
        )
    else:
        log_buendel = []

    # ---------------------------------------------------------
    # 3) LOGISTIK-BÜNDEL (Kommissionierung)
    # ---------------------------------------------------------
    if df_log.empty:
        groups = []
    else:
        grouped = (
            df_log
            .groupby(["Bew.-Artikel", "Durchm.", "Länge"], dropna=False)
            .agg(
                row_keys=("row_key", list),
                fertig_sum=("fertig", "sum"),
                total_menge=("Bedarfs_Menge_pos", "sum"),
            )
            .reset_index()
        )

        def bundle_status(row):
            if row["fertig_sum"] == 0:
                return "offen"
            if row["fertig_sum"] == len(row["row_keys"]):
                return "fertig"
            return "teilweise"

        grouped["status"] = grouped.apply(bundle_status, axis=1)

        grouped = grouped.sort_values(
            by=["Durchm.", "Länge", "Bew.-Artikel"],
            ascending=[True, True, True]
        )

        groups = []
        for _, row in grouped.iterrows():
            df_bundle = df_log[
                (df_log["Bew.-Artikel"] == row["Bew.-Artikel"]) &
                (df_log["Durchm."] == row["Durchm."]) &
                (df_log["Länge"] == row["Länge"])
            ]

            prodid_counts = (
                df_bundle
                .groupby("ProdID_clean", dropna=False)["Bedarfs_Menge_pos"]
                .sum()
                .to_dict()
            )

            prodid_list = [
                {"prodid": pid, "anzahl": int(menge)}
                for pid, menge in prodid_counts.items()
            ]

            groups.append({
                "bew_artikel": row["Bew.-Artikel"],
                "durchmesser": row["Durchm."],
                "laenge": row["Länge"],
                "anzahl_stk": int(row["total_menge"]),
                "prodids": prodid_list,
                "row_keys": row["row_keys"],
                "status": row["status"],
            })

    # ---------------------------------------------------------
    # 4) TEMPLATE RENDERN
    # ---------------------------------------------------------
    return templates.TemplateResponse(
        "logistik_detail.html",
        {
            "request": request,
            "kuerzel": kuerzel,

            # Produktions-Ladungsträger
            "prod_buendel": prod_buendel,
            "prod_fertig": prod_fertig,
            "prod_ausgeliefert": prod_ausgeliefert,
            "zielort_prod": zielort_prod,

            # Logistik-Ladungsträger
            "log_buendel": log_buendel,
            "log_fertig": log_fertig,
            "log_ausgeliefert": log_ausgeliefert,
            "zielort_log": zielort_log,

            # Kommissionier-Bündel
            "groups": groups,

            # Dropdown
            "zielorte": app.state.zielorte,
        }
    )

# ---------------------------------------------------------
# LOGISTIK – Produktions-Ladungsträger ausliefern
# ---------------------------------------------------------
@app.post("/logistik/ausliefern_produktionsladung")
def ausliefern_produktionsladung(request: Request, kuerzel: str = Form(...), zielort: str = Form(...)):
    df = app.state.df_original

    # Produktionsartikel filtern
    mask = (
        (df["Kuerzel_clean"] == kuerzel) &
        (df["Beschaffung"] == "Produktion") &
        (df["Referenz"] == "Produktion")
    )

    # Ausliefern
    df.loc[mask, "ausgeliefert"] = True
    df.loc[mask, "zielort"] = zielort

    # Speichern
    app.state.df_original = df

    return RedirectResponse(f"/logistik/{kuerzel}", status_code=303)



# ---------------------------------------------------------
# LOGISTIK – Logistik-Ladungsträger ausliefern
# ---------------------------------------------------------
@app.post("/logistik/ausliefern_logistikladung")
def ausliefern_logistikladung(request: Request, kuerzel: str = Form(...), zielort: str = Form(...)):
    df = app.state.df_original

    # Logistikartikel filtern
    mask = (
        (df["Kuerzel_clean"] == kuerzel) &
        (df["Referenz"] == "Am Lager")
    )

    # Ausliefern
    df.loc[mask, "ausgeliefert"] = True
    df.loc[mask, "zielort"] = zielort

    # Speichern
    app.state.df_original = df

    return RedirectResponse(f"/logistik/{kuerzel}", status_code=303)

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    df = app.state.df_original

    if df is None:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "items": [],
            "total": 0,
            "prod_fertig_count": 0,
            "log_fertig_count": 0,
            "komplett_count": 0,
            "progress": 0
        })

    kuerzel_list = df["Kuerzel_clean"].dropna().unique()

    komplett = []
    prod_fertig_count = 0
    log_fertig_count = 0

    valid_kuerzel = []   # <- NEU

    for k in kuerzel_list:
        df_k = df[df["Kuerzel_clean"] == k]

        prod_mask = (df_k["Beschaffung"] == "Produktion") & (df_k["Referenz"] == "Produktion")
        log_mask  = (df_k["Referenz"] == "Am Lager")

        hat_prod = df_k[prod_mask].shape[0] > 0
        hat_log  = df_k[log_mask].shape[0] > 0

        # Kürzel ohne Artikel ignorieren
        if not hat_prod and not hat_log:
            continue

        valid_kuerzel.append(k)   # NUR echte Kürzel zählen

        if hat_prod:
            prod_ladung_ausgeliefert = df_k[prod_mask]["ausgeliefert"].all()
        else:
            prod_ladung_ausgeliefert = True

        if hat_log:
            log_ladung_ausgeliefert = df_k[log_mask]["ausgeliefert"].all()
        else:
            log_ladung_ausgeliefert = True

        if prod_ladung_ausgeliefert:
            prod_fertig_count += 1
        if log_ladung_ausgeliefert:
            log_fertig_count += 1

        if prod_ladung_ausgeliefert and log_ladung_ausgeliefert:
            komplett.append(k)

    total = len(valid_kuerzel)   # <- KORREKT!
    komplett_count = len(komplett)
    progress = int((komplett_count / total) * 100) if total > 0 else 0

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "items": komplett,
        "total": total,
        "prod_fertig_count": prod_fertig_count,
        "log_fertig_count": log_fertig_count,
        "komplett_count": komplett_count,
        "progress": progress
    })

# ---------------------------------------------------------
# EXPORT – Komplett fertige Kürzel als Excel (Variante B mit Timestamp)
# ---------------------------------------------------------
@app.get("/export/komplett")
def export_komplett():
    df = app.state.df_original
    if df is None:
        return JSONResponse({"error": "Keine Daten geladen"}, status_code=400)

    # FIX 1: NaN-Kürzel entfernen
    kuerzel_list = df["Kuerzel_clean"].dropna().unique()

    komplett = []

    for k in kuerzel_list:
        df_k = df[df["Kuerzel_clean"] == k]

        prod_mask = (df_k["Beschaffung"] == "Produktion") & (df_k["Referenz"] == "Produktion")
        log_mask  = (df_k["Referenz"] == "Am Lager")

        hat_prod = df_k[prod_mask].shape[0] > 0
        hat_log  = df_k[log_mask].shape[0] > 0

        # FIX 2: Kürzel ohne Artikel ignorieren
        if not hat_prod and not hat_log:
            continue

        if hat_prod:
            prod_ladung_ausgeliefert = df_k[prod_mask]["ausgeliefert"].all()
        else:
            prod_ladung_ausgeliefert = True

        if hat_log:
            log_ladung_ausgeliefert = df_k[log_mask]["ausgeliefert"].all()
        else:
            log_ladung_ausgeliefert = True

        if prod_ladung_ausgeliefert and log_ladung_ausgeliefert:
            komplett.append(k)

    if not komplett:
        return JSONResponse({"error": "Keine vollständig fertigen Kürzel vorhanden"}, status_code=400)

    df_export = df[df["Kuerzel_clean"].isin(komplett)].copy()

    columns = [
        "Kuerzel_clean", "zielort", "Bew.-Artikel", "Durchm.", "Länge",
        "Bedarfs_Menge_pos", "ProdID_clean", "fertig", "ausgeliefert"
    ]
    df_export = df_export[columns]

    df_export = df_export.sort_values(["Kuerzel_clean", "Bew.-Artikel", "Durchm.", "Länge"])

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"export_{timestamp}.xlsx"
    output_path = BASE_DIR / filename

    df_export.to_excel(output_path, index=False)

    return FileResponse(
        output_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )

# ---------------------------------------------------------
# EXPORT – App zurücksetzen nach Abschluss
# ---------------------------------------------------------
@app.get("/export/reset")
def export_reset():
    app.state.df_original = None
    app.state.produktion_tiles = []
    app.state.logistik_tiles = []
    app.state.logistik_tiles = []
    return RedirectResponse("/", status_code=303)

# ---------------------------------------------------------
# DASHBOARD – Detailansicht eines fertigen Kürzels
# ---------------------------------------------------------
@app.get("/dashboard/{kuerzel}", response_class=HTMLResponse)
def dashboard_detail(request: Request, kuerzel: str):
    df = app.state.df_original
    if df is None:
        return RedirectResponse("/", status_code=303)

    # Filter: nur dieses Kürzel, nur fertige Zeilen
    df_done = df[
        (df["Kuerzel_clean"] == kuerzel) &
        (df["fertig"] == True)
    ].copy()

    # Gruppieren wie in Produktion/Logistik
    grouped = (
        df_done
        .groupby(["Bew.-Artikel", "Durchm.", "Länge"], dropna=False)
        .agg(
            total_menge=("Bedarfs_Menge_pos", "sum"),
            prodids=("ProdID_clean", list)
        )
        .reset_index()
    )

    return templates.TemplateResponse(
        "dashboard_detail.html",
        {
            "request": request,
            "kuerzel": kuerzel,
            "groups": grouped.to_dict(orient="records")
        }
    )


# ---------------------------------------------------------
# LOGISTIK – Ladungsträger ausliefern
# ---------------------------------------------------------
@app.post("/logistik/ausliefern")
async def logistik_ausliefern(
    request: Request,
    kuerzel: str = Form(...),
    zielort: str = Form(...)
):
    df = app.state.df_original
    if df is None:
        return RedirectResponse("/", status_code=303)

    # Zielort setzen
    df.loc[df["Kuerzel_clean"] == kuerzel, "zielort"] = zielort
    df.loc[df["Kuerzel_clean"] == kuerzel, "ausgeliefert"] = True

    # Tiles neu berechnen
    app.state.produktion_tiles = build_production_tiles(df)
    app.state.logistik_tiles = build_logistics_tiles(df)

    return RedirectResponse(f"/logistik/{kuerzel}", status_code=303)
