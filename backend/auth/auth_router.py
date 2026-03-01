from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from backend.auth.session import (
    set_authenticated,
    set_role,
    clear_session,
    is_authenticated
)

router = APIRouter()

APP_PASSWORD = "goldbeck-voe"


# ---------------------------------------------------------
# Stufe 1: Passwort-Seite
# ---------------------------------------------------------
@router.get("/login")
def login_form(request: Request):
    return request.app.state.templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None}
    )


@router.post("/login")
def login_submit(request: Request, password: str = Form(...)):
    if password == APP_PASSWORD:
        response = RedirectResponse("/roles", status_code=303)
        set_authenticated(response)
        return response

    return request.app.state.templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Falsches Passwort"}
    )


# ---------------------------------------------------------
# Stufe 2: Rollenwahl
# ---------------------------------------------------------
@router.get("/roles")
def roles_form(request: Request):
    if not is_authenticated(request):
        return RedirectResponse("/login")

    return request.app.state.templates.TemplateResponse(
        "roles.html",
        {"request": request}
    )


@router.post("/roles")
def roles_submit(request: Request, role: str = Form(...)):
    response = RedirectResponse("/", status_code=303)
    set_role(response, role)
    return response


# ---------------------------------------------------------
# Logout
# ---------------------------------------------------------
@router.get("/logout")
def logout(request: Request):
    response = RedirectResponse("/login", status_code=303)
    clear_session(response)
    return response
