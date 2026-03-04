from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from backend.logic.ladungstraeger import LADUNGSTRAEGER
from backend.logic.produktion_state import load_state, save_state

router = APIRouter()


# ---------------------------------------------------------
# PRODUKTIONS-KACHELN IN LOGISTIK ANZEIGEN
# ---------------------------------------------------------
@router.get("/logistik_produktionssignal")
def logistik_produktionssignal(request: Request):
    state = load_state()

    prod_tiles = []
    for lt in LADUNGSTRAEGER:
        lt_id = lt["id"]
        if state.get(lt_id) == "fertig":
            prod_tiles.append({
                "id": lt_id,
                "name": lt["name"]
            })

    return request.app.state.templates.TemplateResponse(
        "logistik_produktionssignal.html",
        {"request": request, "prod_tiles": prod_tiles}
    )


# ---------------------------------------------------------
# LOGISTIK – PRODUKTIONS-LT ALS "AUSGELIEFERT" MARKIEREN
# ---------------------------------------------------------
@router.post("/logistik/produktion_ausgeliefert/{lt_id}")
def logistik_produktions_lieferung(lt_id: str):
    state = load_state()
    state[lt_id] = "offen"
    save_state(state)
    return RedirectResponse("/logistik", status_code=303)

