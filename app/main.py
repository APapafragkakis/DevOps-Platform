import logging
from datetime import timedelta
from typing import List

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session

import crud
import models
import schemas
from auth import (
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from cache import cache_get, cache_set, cache_delete, redis_ping
from database import SessionLocal, engine
from logging_config import setup_logging, get_logger
from tracing import setup_tracing

setup_logging()
logger = get_logger(__name__)

models.Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

app = FastAPI(
    title="DevOps Platform API",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)
setup_tracing(app, engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health", tags=["ops"])
def health_check(db: Session = Depends(get_db)):
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("db health check failed", extra={"error": str(exc)})
        db_ok = False

    redis_ok = redis_ping()

    if not db_ok:
        raise HTTPException(status_code=503, detail="database unavailable")

    return {
        "status": "healthy",
        "version": "3.0.0",
        "dependencies": {
            "database": "ok" if db_ok else "error",
            "redis": "ok" if redis_ok else "unavailable",
        },
    }


@app.post("/auth/register", response_model=schemas.UserOut, status_code=201, tags=["auth"])
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="username already exists")
    return crud.create_user(db, user)


@app.post("/auth/token", response_model=schemas.Token, tags=["auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info("user logged in", extra={"username": user.username})
    return {"access_token": token, "token_type": "bearer"}


ITEMS_CACHE_KEY = "items:all"


@app.get("/items", response_model=List[schemas.Item], tags=["items"])
@limiter.limit("60/minute")
def read_items(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    cache_key = f"{ITEMS_CACHE_KEY}:{skip}:{limit}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    items = crud.get_items(db, skip=skip, limit=limit)
    serialized = [schemas.Item.model_validate(i).model_dump(mode="json") for i in items]
    cache_set(cache_key, serialized)
    return items


@app.post("/items", response_model=schemas.Item, status_code=201, tags=["items"])
@limiter.limit("30/minute")
def create_item(
    request: Request,
    item: schemas.ItemCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    db_item = crud.create_item(db, item)
    cache_delete(ITEMS_CACHE_KEY)
    logger.info("item created", extra={"item_id": db_item.id, "item_name": db_item.name})
    return db_item


@app.delete("/items/{item_id}", status_code=204, tags=["items"])
@limiter.limit("30/minute")
def delete_item(
    request: Request,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    deleted = crud.delete_item(db, item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="item not found")
    cache_delete(ITEMS_CACHE_KEY)
    logger.info("item deleted", extra={"item_id": item_id})
