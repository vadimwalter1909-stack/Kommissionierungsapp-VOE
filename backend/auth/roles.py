from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from backend.auth.session import create_session

router = APIRouter()

# ---------------------------------------------------------
# Rollen-Auswahlseite
# ---------------------------------------------------------
@router.get("/roles")
def choose_role(request: Request):
    return request.app.state.templates.TemplateResponse(
        "roles.html",
        {"request": request}
    )


# ---------------------------------------------------------
# Auswahl absenden → Passwortseite
# ---------------------------------------------------------
@router.post("/roles/select")
def select_role(role: str = Form(...)):
    return RedirectResponse(f"/role/{role}", status_code=303)


# ---------------------------------------------------------
# Rollen-Passwörter
# ---------------------------------------------------------
ROLE_PASSWORDS = {
    "produktion": "prod123",
    "logistik": "logi123",
    "av": "av123",
    "admin": "admin123"
}

ROLE_TARGET = {
    "produktion": "/produktion",
    "logistik": "/logistik",
    "av": "/upload",
    "admin": "/upload"
}


# ---------------------------------------------------------
# Passwortseite
# ---------------------------------------------------------
@router.get("/role/{role}")
def role_password_page(request: Request, role: str):
    return request.app.state.templates.TemplateResponse(
        "role_password.html",
        {"request": request, "role": role}
    )


# ---------------------------------------------------------
# Passwortprüfung + Weiterleitung
# ---------------------------------------------------------
@router.post("/role/{role}")
def role_password_submit(role: str, password: str = Form(...)):
    if password != ROLE_PASSWORDS.get(role):
        return RedirectResponse(f"/role/{role}", status_code=303)

    response = RedirectResponse(ROLE_TARGET[role], status_code=303)
    create_session(response, role)  # <-- einzig richtige Stelle
    return response
