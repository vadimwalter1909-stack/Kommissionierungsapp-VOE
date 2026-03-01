from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

# Datenbank-Basis
from backend.database_base import Base, engine

# Auth
from backend.auth.middleware import AuthMiddleware
from backend.auth.auth_router import router as auth_router
from backend.auth.session import get_role

# Routen
from backend.routes.upload import router as upload_router
from backend.routes.produktion import router as produktion_router
from backend.routes.logistik import router as logistik_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.test_export import test_router
from backend.routes.export import router as export_router
from backend.routes.daily_export import router as daily_export_router

# ---------------------------------------------------------
# Datenbanktabellen erzeugen
# ---------------------------------------------------------
Base.metadata.create_all(bind=engine)

app = FastAPI()

# ---------------------------------------------------------
# Templates & Static
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR.parent / "frontend" / "templates"
STATIC_DIR = BASE_DIR.parent / "frontend" / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.state.templates = templates

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------------------------------------------------------
# Middleware
# ---------------------------------------------------------
@app.middleware("http")
async def add_role(request, call_next):
    request.state.role = get_role(request)
    return await call_next(request)

app.add_middleware(AuthMiddleware)

# ---------------------------------------------------------
# Router registrieren
# ---------------------------------------------------------
app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(produktion_router)
app.include_router(logistik_router)
app.include_router(dashboard_router)
app.include_router(test_router)
app.include_router(export_router)
app.include_router(daily_export_router)

# ---------------------------------------------------------
# DEBUG: Items eines Kürzels anzeigen
# ---------------------------------------------------------
from backend.database_base import SessionLocal
from backend.database import Item
