from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from backend.logic.ladungstraeger import LADUNGSTRAEGER
from backend.logic.produktion_state import load_state, save_state

router = APIRouter()


# ---------------------------------------------------------
# PRODUKTION – ÜBERSICHT
# ---------------------------------------------------------
@router.get("/produktion")
def produktion_overview(request: Request):
    state = load_state()

    tiles = []
    for lt in LADUNGSTRAEGER:
        lt_id = lt["id"]
        status = state.get(lt_id, "offen")

        if status == "fertig":
            color = "gruen"
            icon = "✔"
        else:
            color = "grau"
            icon = "⏳"

        tiles.append({
            "id": lt_id,
            "name": lt["name"],
            "status": color,
            "icon": icon
        })

    return request.app.state.templates.TemplateResponse(
        "produktion.html",
        {"request": request, "tiles": tiles}
    )


# ---------------------------------------------------------
# PRODUKTION – FERTIG MELDEN
# ---------------------------------------------------------
@router.post("/produktion/{lt_id}/fertig")
def produktion_fertig(lt_id: str):
    state = load_state()
    state[lt_id] = "fertig"
    save_state(state)
    return RedirectResponse("/produktion", status_code=303)


# ---------------------------------------------------------
# PRODUKTION – RESET (von Logistik oder Produktion)
# ---------------------------------------------------------
@router.post("/produktion/{lt_id}/reset")
def produktion_reset(lt_id: str):
    state = load_state()
    state[lt_id] = "offen"
    save_state(state)
    return RedirectResponse("/produktion", status_code=303)
