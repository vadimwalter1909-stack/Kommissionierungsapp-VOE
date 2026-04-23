from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from backend.logic.produktion_state import load_state, save_state
from backend.logic.ladungstraeger import load_ladungstraeger, save_ladungstraeger

router = APIRouter()


# ---------------------------------------------------------
# PRODUKTION – ÜBERSICHT
# ---------------------------------------------------------
@router.get("/produktion")
def produktion_overview(request: Request):
    state = load_state()
    lt_list = load_ladungstraeger()

    tiles = []
    for lt in lt_list:
        lt_id = lt["id"]
        name = lt["name"]
        status = state.get(lt_id, "offen")

        if status == "fertig":
            color = "gruen"
            icon = "✔"
        else:
            color = "grau"
            icon = "⏳"

        tiles.append(
            {
                "id": lt_id,
                "name": name,
                "status": color,
                "icon": icon,
            }
        )

    # Sortierung nach LT-Nummer
    tiles.sort(key=lambda x: int(x["id"].replace("LT", "")))

    # ✅ FIX: request MUSS explizit übergeben werden
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="produktion.html",
        context={
            "request": request,
            "tiles": tiles,
        },
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
# PRODUKTION – RESET
# ---------------------------------------------------------
@router.post("/produktion/{lt_id}/reset")
def produktion_reset(lt_id: str):
    state = load_state()
    state[lt_id] = "offen"
    save_state(state)
    return RedirectResponse("/produktion", status_code=303)


# ---------------------------------------------------------
# PRODUKTION – NEUEN LADUNGSTRÄGER ANLEGEN
# ---------------------------------------------------------
@router.post("/produktion/add")
def produktion_add(name: str = Form(...)):
    lt_list = load_ladungstraeger()
    state = load_state()

    # nächste freie Nummer finden
    existing_numbers = [
        int(lt["id"].replace("LT", "")) for lt in lt_list
    ]
    next_number = max(existing_numbers + [0]) + 1

    new_id = f"LT{next_number:02d}"

    # neuen Ladungsträger speichern
    lt_list.append(
        {
            "id": new_id,
            "name": name,
        }
    )
    save_ladungstraeger(lt_list)

    # Status initialisieren
    state[new_id] = "offen"
    save_state(state)

    return RedirectResponse("/produktion", status_code=303)


# ---------------------------------------------------------
# PRODUKTION – LADUNGSTRÄGER LÖSCHEN
# ---------------------------------------------------------
@router.post("/produktion/{lt_id}/delete")
def produktion_delete(lt_id: str):
    lt_list = load_ladungstraeger()
    state = load_state()

    # aus Ladungsträger-Liste entfernen
    lt_list = [lt for lt in lt_list if lt["id"] != lt_id]
    save_ladungstraeger(lt_list)

    # Status entfernen
    if lt_id in state:
        del state[lt_id]
        save_state(state)

    return RedirectResponse("/produktion", status_code=303)
