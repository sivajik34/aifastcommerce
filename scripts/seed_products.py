import sys
import os
import asyncio

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.session import get_db
from modules.catalog.schema import ProductCreate
from modules.catalog.service import create_product

sample_products = [
    ProductCreate(name="Laptop", description="High-end gaming laptop", price=1500.00, stock=10),
    ProductCreate(name="Phone", description="Latest smartphone", price=999.99, stock=25),
    ProductCreate(name="Headphones", description="Noise cancelling headphones", price=199.99, stock=50),
    ProductCreate(name="Monitor", description="4K UHD monitor", price=349.99, stock=15),
]

async def seed():
    async with get_db() as db:
        for product in sample_products:
            await create_product(product, db)
        print("✅ Sample products added.")

if __name__ == "__main__":
    asyncio.run(seed())
