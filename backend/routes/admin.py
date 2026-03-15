from fastapi import APIRouter, Request, HTTPException
from backend.database_base import SessionLocal
from backend.database import Item

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/delete/{item_id}")
async def delete_item(item_id: int, request: Request):
    # Nur Admins dürfen löschen
    if request.state.role != "admin":
        raise HTTPException(status_code=403, detail="Keine Berechtigung")

    db = SessionLocal()
    item = db.query(Item).filter(Item.id == item_id).first()

    if not item:
        db.close()
        raise HTTPException(status_code=404, detail="Item nicht gefunden")

    db.delete(item)
    db.commit()
    db.close()

    return {"status": "ok", "message": f"Item {item_id} gelöscht"}
