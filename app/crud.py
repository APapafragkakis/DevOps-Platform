from sqlalchemy.orm import Session
import models
import schemas
from auth import hash_password, verify_password


def get_items(db: Session, skip: int = 0, limit: int = 10):
    return db.query(models.Item).filter(models.Item.is_active).offset(skip).limit(limit).all()


def create_item(db: Session, item: schemas.ItemCreate):
    db_item = models.Item(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def delete_item(db: Session, item_id: int) -> bool:
    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        return False
    item.is_active = False  # soft delete
    db.commit()
    return True


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        username=user.username,
        hashed_password=hash_password(user.password),
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

