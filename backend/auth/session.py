from fastapi import Request, Response

ROLE_COOKIE = "voe_role"
AUTH_COOKIE = "voe_auth"


# ---------------------------------------------------------
# Stufe 1: App-Passwort speichern
# ---------------------------------------------------------
def set_authenticated(response: Response):
    response.set_cookie(
        key=AUTH_COOKIE,
        value="true",
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12
    )


def is_authenticated(request: Request) -> bool:
    return request.cookies.get(AUTH_COOKIE) == "true"


# ---------------------------------------------------------
# Stufe 2: Rolle speichern
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
# Logout
# ---------------------------------------------------------
def clear_session(response: Response):
    response.delete_cookie(AUTH_COOKIE)
    response.delete_cookie(ROLE_COOKIE)
