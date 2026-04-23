from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse

from backend.database_base import SessionLocal
from backend.database import Item

router = APIRouter()


# ---------------------------------------------------------
# LOGISTIK – AUFTRAG REAKTIVIEREN
# ---------------------------------------------------------
@router.post("/reactivate/{prod_id}")
async def reactivate_order(
    request: Request,
    prod_id: str,
    start_bft: str = Form(...)
):
    db = SessionLocal()

    items = db.query(Item).filter(Item.prod_id == prod_id).all()

    if not items:
        db.close()
        return RedirectResponse("/", status_code=303)

    for item in items:
        item.verschoben = False
        item.start_bft = start_bft

    db.commit()
    db.close()

    # ✅ WICHTIG: TemplateResponse nur mit KEYWORD-ARGUMENTEN
    return request.app.state.templates.TemplateResponse(
        name="reactivate_confirm.html",
        context={
            "request": request,
            "prod_id": prod_id,
            "start_bft": start_bft,
        },
    )
