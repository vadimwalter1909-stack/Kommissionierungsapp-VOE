import pandas as pd
import datetime

def prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # ---------------------------------------------------------
    # 1. Spaltennamen vereinheitlichen
    # ---------------------------------------------------------
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace("-", "_")
        .str.replace(".", "")
        .str.replace("ä", "ae")
        .str.replace("ö", "oe")
        .str.replace("ü", "ue")
    )

    # ---------------------------------------------------------
    # 2. Kürzel-Spalte finden
    # ---------------------------------------------------------
    kuerzel_aliases = ["kuerzel", "kürzel", "kurzel", "kennz", "kennzeichen", "kz"]
    found = None
    for alias in kuerzel_aliases:
        if alias in df.columns:
            found = alias
            break

    if not found:
        raise ValueError("Keine gültige Kürzel-Spalte gefunden.")

    df["kuerzel"] = df[found].astype(str).str.strip()

    # ---------------------------------------------------------
    # 3. Leere oder ungültige Kürzel entfernen
    # ---------------------------------------------------------
    df = df[df["kuerzel"].notna()]
    df = df[df["kuerzel"].str.strip() != ""]
    df = df[df["kuerzel"].str.lower() != "nan"]

    # ---------------------------------------------------------
    # 4. Excel → interne Spaltennamen (Mapping)
    # ---------------------------------------------------------
    column_map = {
        "prodid_bft": "prod_id",
        "prodid": "prod_id",

        "artikel_nr_bft": "artikel_nr",
        "artikel_nr": "artikel_nr",

        "bew_artikel": "artikel_clean",
        "bew_art": "artikel_clean",
        "bewartikel": "artikel_clean",
        "bew_artikel_bft": "artikel_clean",
        "bew_artikel_bew": "artikel_clean",
        "bewartikelbft": "artikel_clean",
        "bewartikelbew": "artikel_clean",

        "durchm": "durchmesser",
        "durchmesser": "durchmesser",

        "laenge": "laenge",
        "laenge_bft": "laenge",
        "laengebew": "laenge",

        "biegung": "biegung",

        "bedarfs_menge": "bedarfs_menge_pos",
        "bedarfs_n": "bedarfs_menge_pos",
        "bedarfs_nr": "bedarfs_menge_pos",
        "bedarfsnr": "bedarfs_menge_pos",
        "bedarfsmenge": "bedarfs_menge_pos",

        "menge": "menge",

        "beschaffung": "beschaffung",
        "beschaff": "beschaffung",

        "referenz": "referenz",
        "ref": "referenz",
        "refnr": "referenz",

        "start_bft": "start_bft",
        "start_bew": "start_bew",
    }

    for old, new in column_map.items():
        if old in df.columns:
            df[new] = df[old]

    # ---------------------------------------------------------
    # 5. Typkonvertierungen (narrensicher)
    # ---------------------------------------------------------
    numeric_fields = ["durchmesser", "laenge", "bedarfs_menge_pos", "menge"]
    for col in numeric_fields:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # ---------------------------------------------------------
    # 6. Biegung absichern (keine NaN-Gruppen)
    # ---------------------------------------------------------
    if "biegung" in df.columns:
        df["biegung"] = df["biegung"].fillna("unbekannt").astype(str)

    # ---------------------------------------------------------
    # 7. Datumsfelder in Strings umwandeln
    # ---------------------------------------------------------
    date_fields = ["start_bft", "start_bew"]

    for col in date_fields:
        if col in df.columns:
            def convert_date(x):
                if pd.isna(x):
                    return ""
                if isinstance(x, (pd.Timestamp, datetime.datetime)):
                    return x.strftime("%Y-%m-%d")
                return str(x)

            df[col] = df[col].apply(convert_date)

    # ---------------------------------------------------------
    # 8. Fehlende Spalten ergänzen
    # ---------------------------------------------------------
    defaults = {
        "artikel_nr": "",
        "artikel_clean": "",
        "durchmesser": 0.0,
        "laenge": 0.0,
        "biegung": "unbekannt",
        "bedarfs_menge_pos": 0.0,
        "menge": 0.0,
        "prod_id": "",
        "start_bft": "",
        "start_bew": "",
        "beschaffung": "",
        "referenz": "",
        "fertig": False,
        "ausgeliefert": False,
    }

    for col, default in defaults.items():
        if col not in df.columns:
            df[col] = default

    return df
