import smtplib
from datetime import date
import pandas as pd
from email.message import EmailMessage
from io import BytesIO
import os

from backend.database_base import SessionLocal
from backend.database import Item


def export_and_send_email():
    today = date.today()
    db = SessionLocal()

    try:
        # Nur ausgelieferte Items exportieren
        items = db.query(Item).filter(Item.ausgeliefert == True).all()

        if not items:
            return  # Nichts zu exportieren

        # Vollständige Datensätze exportieren
        rows = []
        for i in items:
            d = i.__dict__.copy()
            d.pop("_sa_instance_state", None)
            rows.append(d)

        df = pd.DataFrame(rows)

        # Excel in Memory erzeugen
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Items")

        output.seek(0)

        # E-Mail senden
        send_email(output, today)

    finally:
        db.close()


def send_email(output, today):
    EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.mailersend.net")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

    EMPFAENGER = [
        "prodlog-empfang@firemail.de"
    ]

    msg = EmailMessage()
    msg["Subject"] = f"VOE Tagesabschluss {today}"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = ", ".join(EMPFAENGER)
    msg.set_content("Anbei der Tagesabschluss der VOE-Kommissionierungs-App.")

    # Datei aus dem RAM anhängen
    msg.add_attachment(
        output.getvalue(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"VOE_Abschluss_{today}.xlsx"
    )

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
