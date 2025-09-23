from sqlalchemy.orm import Session
from . import models, schemas

def create_item(db: Session, data: schemas.ItemCreate) -> models.Item:
    obj = models.Item(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_item(db: Session, item_id: int) -> models.Item | None:
    return db.query(models.Item).filter(models.Item.id == item_id).first()

def list_items(db: Session, skip: int = 0, limit: int = 50) -> list[models.Item]:
    return db.query(models.Item).offset(skip).limit(limit).all()

def update_item(db: Session, item_id: int, data: schemas.ItemUpdate) -> models.Item | None:
    obj = get_item(db, item_id)
    if not obj:
        return None
    update_data = data.dict(exclude_unset=True)
    for k, v in update_data.items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

def delete_item(db: Session, item_id: int) -> bool:
    obj = get_item(db, item_id)
    if not obj:
        return False
    db.delete(obj)
    db.commit()
    return True
