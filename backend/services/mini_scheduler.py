import threading
import time
from datetime import datetime

from backend.services.daily_export import export_and_send_email


def scheduler_loop():
    """
    Mini-Scheduler, der jede Minute prüft,
    ob es 23:59 ist. Wenn ja, wird der Export ausgeführt.
    """
    print("Mini-Scheduler gestartet...")

    while True:
        now = datetime.now()

        # Prüfen: Ist es 23:59?
        if now.hour == 23 and now.minute == 59:
            print("Mini-Scheduler: Export wird ausgeführt...")
            try:
                export_and_send_email()
                print("Mini-Scheduler: Export erfolgreich ausgeführt.")
            except Exception as e:
                print("Mini-Scheduler Fehler:", e)

            # 60 Sekunden warten, damit er nicht mehrfach auslöst
            time.sleep(60)

        # Normaler Schlafzyklus
        time.sleep(30)


def start_scheduler():
    """
    Startet den Scheduler in einem Hintergrund-Thread.
    """
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    print("Mini-Scheduler Thread gestartet.")
