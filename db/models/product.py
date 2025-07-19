
from sqlalchemy import Column, Integer, String, Float,DateTime, func,ForeignKey
from sqlalchemy.orm import relationship
from db.session import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Float)
    stock = Column(Integer)
    category_id = Column(Integer, ForeignKey("categories.id"))
    average_rating = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    review_count = Column(Integer, default=0)


    category = relationship("Category", back_populates="products")
