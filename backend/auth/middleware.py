from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import RedirectResponse

from backend.auth.session import (
    is_authenticated,
    is_session_expired,
    update_last_activity,
    clear_session
)

PUBLIC_PATHS = [
    "/login",
    "/static",
]


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path

        # Öffentliche Seiten immer erlauben
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)

        # Wenn nicht eingeloggt → Login
        if not is_authenticated(request):
            return RedirectResponse("/login")

        # Session-Timeout prüfen
        if is_session_expired(request):
            response = RedirectResponse("/login")
            clear_session(response)
            return response

        # Aktivität aktualisieren
        response = await call_next(request)
        update_last_activity(response)
        return response
