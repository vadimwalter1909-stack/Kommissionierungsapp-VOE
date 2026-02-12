@app.post("/upload_excel")
async def upload_excel(file: UploadFile = File(...)):
    mapping = load_hallen_mapping()
    df = pd.read_excel(file.file, engine="openpyxl")

    # DEBUG
    print("\n--- DEBUG: EINDEUTIGE WERTE ---")
    print("Beschaffung:", df["Beschaffung"].unique())
    print("Referenz:", df["Referenz"].unique())
    print("--------------------------------\n")

    # ---------------------------------------------------------
    # Pflichtspalten prüfen
    # ---------------------------------------------------------
    required_cols = {"Kürzel", "Referenz", "Beschaffung"}
    if not required_cols.issubset(df.columns):
        app.state.hall_counts = {}
        app.state.df_produkt = []
        app.state.df_lager = []
        app.state.df_bestellung = []
        return RedirectResponse("/", status_code=303)

    # ---------------------------------------------------------
    # Kürzel normalisieren (CP-WAOI → WAOI)
    # ---------------------------------------------------------
    df["Kürzel_clean"] = (
        df["Kürzel"]
        .astype(str)
        .str.replace("CP-", "", regex=False)
        .str.strip()
        .str.upper()
    )

    # ---------------------------------------------------------
    # Halle bestimmen
    # ---------------------------------------------------------
    df["Halle"] = df["Kürzel_clean"].apply(lambda k: finde_halle(k, mapping))

    # Für Startseite speichern
    app.state.df_original = df
    app.state.hall_counts = df["Halle"].value_counts().to_dict()

    # ---------------------------------------------------------
    # Robuste Normalisierung für Referenz & Beschaffung
    # ---------------------------------------------------------
    def clean(x):
        return (
            str(x)
            .replace("\u00A0", " ")
            .replace("\t", " ")
            .strip()
            .lower()
        )

    df["Referenz_clean"] = df["Referenz"].apply(clean)
    df["Beschaffung_clean"] = df["Beschaffung"].apply(clean)

    # ---------------------------------------------------------
    # Matching-Funktion
    # ---------------------------------------------------------
    def match(value, patterns):
        v = str(value).strip().lower()
        return any(p in v for p in patterns)

    # ---------------------------------------------------------
    # PRODUKTION (dynamisch)
    # ---------------------------------------------------------
    df_produkt = df[
        df["Beschaffung_clean"].apply(lambda x: match(x, ["prod", "fert"]))
    ]

    # ---------------------------------------------------------
    # PRODUKTIONSLISTE als Dicts erzeugen (WICHTIG!)
    # ---------------------------------------------------------
    produkt_liste = []
    for _, row in df_produkt.iterrows():
        produkt_liste.append({
            "prod_id": row["ProdID BFT"],
            "bew_artikel": row["Bew.-Artikel"],
            "durchmesser": row["Durchm."],
            "laenge": row["Länge"],
            "bedarfs_menge": row["Bedarfs-Menge"],
            "ref_nr": row["Ref.-Nr."],
            "halle": row["Halle"],
            "kuerzel": row["Kürzel_clean"],   # ← WAOI, DERDOA, GIBO2F, WAG …
        })

    app.state.df_produkt = produkt_liste

    # ---------------------------------------------------------
    # LOGISTIK
    # ---------------------------------------------------------
    app.state.df_lager = df[
        df["Referenz_clean"].apply(lambda x: match(x, ["lager"]))
    ]

    # ---------------------------------------------------------
    # BESTELLUNG
    # ---------------------------------------------------------
    app.state.df_bestellung = df[
        df["Beschaffung_clean"].apply(lambda x: match(x, ["bestell"]))
        | df["Referenz_clean"].apply(lambda x: match(x, ["bestell"]))
    ]

    return RedirectResponse("/", status_code=303)
