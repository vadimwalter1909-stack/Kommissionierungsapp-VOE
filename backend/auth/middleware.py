from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import RedirectResponse

from backend.auth.session import is_authenticated

PUBLIC_PATHS = [
    "/login",
    "/static",
    "/",   # Root darf passieren
]


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path

        # Öffentliche Seiten
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)

        # Login-Prüfung
        if not is_authenticated(request):
            return RedirectResponse("/login")

        # Rollen komplett deaktiviert – jeder eingeloggt darf alles
        return await call_next(request)
