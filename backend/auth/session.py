from fastapi import Request, Response
from datetime import datetime, timedelta

ROLE_COOKIE = "voe_role"
AUTH_COOKIE = "voe_auth"
LAST_ACTIVITY_COOKIE = "voe_last_activity"

SESSION_TIMEOUT_MINUTES = 60


# ---------------------------------------------------------
# Login: Authentifizierung setzen
# ---------------------------------------------------------
def set_authenticated(response: Response):
    response.set_cookie(
        key=AUTH_COOKIE,
        value="true",
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12
    )
    update_last_activity(response)


def is_authenticated(request: Request) -> bool:
    return request.cookies.get(AUTH_COOKIE) == "true"


# ---------------------------------------------------------
# Rolle setzen / lesen
# ---------------------------------------------------------
def set_role(response: Response, role: str):
    response.set_cookie(
        key=ROLE_COOKIE,
        value=role,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12
    )


def get_role(request: Request) -> str | None:
    return request.cookies.get(ROLE_COOKIE)


# ---------------------------------------------------------
# Aktivität aktualisieren
# ---------------------------------------------------------
def update_last_activity(response: Response):
    response.set_cookie(
        key=LAST_ACTIVITY_COOKIE,
        value=datetime.utcnow().isoformat(),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12
    )


def get_last_activity(request: Request):
    ts = request.cookies.get(LAST_ACTIVITY_COOKIE)
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except:
        return None


def is_session_expired(request: Request) -> bool:
    last = get_last_activity(request)
    if not last:
        return True
    return datetime.utcnow() - last > timedelta(minutes=SESSION_TIMEOUT_MINUTES)


# ---------------------------------------------------------
# Logout
# ---------------------------------------------------------
def clear_session(response: Response):
    response.delete_cookie(AUTH_COOKIE)
    response.delete_cookie(ROLE_COOKIE)
    response.delete_cookie(LAST_ACTIVITY_COOKIE)
