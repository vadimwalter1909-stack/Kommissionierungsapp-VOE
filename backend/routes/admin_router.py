from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from backend.database_base import SessionLocal
from backend.database import Item

router = APIRouter()

@router.post("/admin/delete/{prod_id}")
def admin_delete_order(request: Request, prod_id: str):
    if request.state.role != "admin":
        return RedirectResponse("/logistik", status_code=303)
    print("DEBUG: prod_id =", prod_id)

    db = SessionLocal()
    items = db.query(Item).filter(Item.prod_id == prod_id).all()
    print("DEBUG: Items gefunden =", len(items))
    for item in items:
        db.delete(item)

    db.commit()

    return RedirectResponse("/logistik", status_code=303)

