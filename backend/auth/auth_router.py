from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from datetime import datetime
import os

from backend.auth.session import (
    set_authenticated,
    set_role,
    clear_session,
    update_last_activity
)

router = APIRouter()

# ---------------------------------------------------------
# Passwörter aus .env laden
# ---------------------------------------------------------
APP_PASSWORD = os.getenv("APP_PASSWORD")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")


# ---------------------------------------------------------
# Login-Seite
# ---------------------------------------------------------
@router.get("/login")
def login_form(request: Request):
    return request.app.state.templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": None,
            "year": datetime.now().year
        }
    )

# ---------------------------------------------------------
# Login-Submit
# ---------------------------------------------------------
@router.post("/login")
def login_submit(request: Request, password: str = Form(...)):

    # Admin-Login
    if password == ADMIN_PASSWORD:
        response = RedirectResponse("/", status_code=303)
        set_authenticated(response)
        set_role(response, "admin")
        update_last_activity(response)
        return response

    # Normaler Login
    if password == APP_PASSWORD:
        response = RedirectResponse("/", status_code=303)
        set_authenticated(response)
        set_role(response, "user")
        update_last_activity(response)
        return response

    # Falsches Passwort
    return request.app.state.templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Falsches Passwort"}
    )


# ---------------------------------------------------------
# Logout
# ---------------------------------------------------------
@router.get("/logout")
def logout(request: Request):
    response = RedirectResponse("/login", status_code=303)
    clear_session(response)
    return response
