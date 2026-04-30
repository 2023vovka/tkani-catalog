import os
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pydantic import BaseModel

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db, Base, engine
from backend.models import Fabric, FabricColor

# Create tables if not exists
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fabric Database CRM")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Static files
frontend_dir = os.path.join(base_dir, "frontend")
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")

images_dir = os.path.join(base_dir, "fabric_images")
os.makedirs(images_dir, exist_ok=True)
app.mount("/images", StaticFiles(directory=images_dir), name="images")

# Pydantic Schemas
class ColorSchema(BaseModel):
    id: int
    color_name: str
    image_path: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

class FabricSchema(BaseModel):
    id: int
    manufacturer: str
    name: str
    category: Optional[str] = None
    price: Optional[float] = None
    wholesale_price: Optional[float] = None
    missing_price: Optional[bool] = False
    density: Optional[int] = None
    martindale: Optional[int] = None
    properties: Optional[str] = None
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    fabric_type: Optional[str] = "Другое"
    colors: List[ColorSchema] = []

    class Config:
        from_attributes = True

class PriceUpdate(BaseModel):
    price: float

@app.get("/api/fabrics", response_model=List[FabricSchema])
def get_fabrics(
    q: Optional[str] = None,
    manufacturer: Optional[str] = None,
    category: Optional[str] = None,
    min_density: Optional[int] = Query(None),
    max_density: Optional[int] = Query(None),
    min_martindale: Optional[int] = Query(None),
    max_martindale: Optional[int] = Query(None),
    property: Optional[List[str]] = Query(None),
    type: Optional[List[str]] = Query(None),
    missing_price_only: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Fabric)

    if q:
        search = f"%{q}%"
        query = query.filter(or_(Fabric.name.ilike(search), Fabric.manufacturer.ilike(search)))
    
    if manufacturer:
        query = query.filter(Fabric.manufacturer.ilike(f"%{manufacturer}%"))
    
    if category:
        query = query.filter(Fabric.category.ilike(f"%{category}%"))

    if min_density is not None:
        query = query.filter(Fabric.density >= min_density)
    if max_density is not None:
        query = query.filter(Fabric.density <= max_density)
        
    if min_martindale is not None:
        query = query.filter(Fabric.martindale >= min_martindale)
    if max_martindale is not None:
        query = query.filter(Fabric.martindale <= max_martindale)

    if property:
        for p in property:
            query = query.filter(Fabric.properties.like(f"%{p}%"))
            
    if type:
        type_conditions = [Fabric.fabric_type == t for t in type]
        if type_conditions:
            query = query.filter(or_(*type_conditions))
            
    if missing_price_only:
        query = query.filter(Fabric.missing_price == True)

    fabrics = query.all()
    return fabrics

@app.put("/api/fabrics/{fabric_id}/price", response_model=FabricSchema)
def update_price(fabric_id: int, price_data: PriceUpdate, db: Session = Depends(get_db)):
    fabric = db.query(Fabric).filter(Fabric.id == fabric_id).first()
    if not fabric:
        raise HTTPException(status_code=404, detail="Fabric not found")
    
    fabric.price = price_data.price
    fabric.missing_price = False
    db.commit()
    db.refresh(fabric)
    return fabric

@app.get("/api/filters")
def get_filter_options(db: Session = Depends(get_db)):
    manufacturers = [r[0] for r in db.query(Fabric.manufacturer).distinct().all() if r[0]]
    categories = [r[0] for r in db.query(Fabric.category).distinct().all() if r[0]]
    
    max_density = db.query(Fabric.density).order_by(Fabric.density.desc()).first()
    max_martindale = db.query(Fabric.martindale).order_by(Fabric.martindale.desc()).first()
    
    return {
        "manufacturers": manufacturers,
        "categories": categories,
        "max_density": max_density[0] if max_density and max_density[0] else 1000,
        "max_martindale": max_martindale[0] if max_martindale and max_martindale[0] else 200000
    }
# --- РАЗДАЧА ФРОНТЕНДА ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Даем доступ к папке frontend (чтобы работали стили, JS и картинки)
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

# При заходе на главную страницу показываем каталог
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
