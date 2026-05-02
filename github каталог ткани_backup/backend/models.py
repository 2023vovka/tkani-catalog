from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Fabric(Base):
    __tablename__ = "fabrics"

    id = Column(Integer, primary_key=True, index=True)
    manufacturer = Column(String, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True, nullable=True) # A, B, C etc
    
    price = Column(Float, nullable=True) # Retail price
    wholesale_price = Column(Float, nullable=True) # Wholesale price
    missing_price = Column(Boolean, default=False) # Helper for filtering
    
    density = Column(Integer, nullable=True) # Grams / m2
    martindale = Column(Integer, nullable=True) # Cycles
    
    properties = Column(String, nullable=True) # Text like "водоотталкивание, чистка, ..."
    
    # URLs
    product_url = Column(String, nullable=True) # Direct link to fabric page
    image_url = Column(String, nullable=True) # Cover image URL
    fabric_type = Column(String, default="Другое")
    
    colors = relationship("FabricColor", back_populates="fabric", cascade="all, delete-orphan")

class FabricColor(Base):
    __tablename__ = "fabric_colors"

    id = Column(Integer, primary_key=True, index=True)
    fabric_id = Column(Integer, ForeignKey("fabrics.id"))
    color_name = Column(String)
    image_path = Column(String, nullable=True) # Local path (deprecated/legacy)
    image_url = Column(String, nullable=True) # Direct internet URL
    
    fabric = relationship("Fabric", back_populates="colors")
