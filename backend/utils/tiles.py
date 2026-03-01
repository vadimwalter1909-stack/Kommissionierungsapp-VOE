from backend.database import SessionLocal, Item
import pandas as pd


def load_df():
    db = SessionLocal()
    items = db.query(Item).all()
    db.close()

    if not items:
        return pd.DataFrame()

    df = pd.DataFrame([i.__dict__ for i in items])

    if "_sa_instance_state" in df.columns:
        df = df.drop(columns=["_sa_instance_state"])

    return df


def build_production_tiles():
    df = load_df()

    # Wenn keine Daten → keine Tiles
    if df.empty:
        return []

    # Wenn kuerzel fehlt → keine Tiles
    if "kuerzel" not in df.columns:
        return []

    # Leere oder Null-Kürzel entfernen
    df = df[df["kuerzel"].notna() & (df["kuerzel"] != "")]

    if df.empty:
        return []

    tiles = []

    for kuerzel in df["kuerzel"].unique():
        df_k = df[df["kuerzel"] == kuerzel]

        total = len(df_k)
        fertig = df_k["fertig"].sum() if "fertig" in df_k.columns else 0

        tiles.append({
            "kuerzel": kuerzel,
            "total": total,
            "fertig": int(fertig),
            "offen": int(total - fertig)
        })

    return tiles
