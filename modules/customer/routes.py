from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from db.models.customer import Customer
from .schema import CustomerCreate, CustomerUpdate, CustomerOut
from .service import (
    get_customer_by_id,
    get_customer_by_email,
    create_customer,
    update_customer,
    delete_customer,
)

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("/{customer_id}", response_model=CustomerOut)
async def read_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    customer = await get_customer_by_id(customer_id, db)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/by-email/{email}", response_model=CustomerOut)
async def read_customer_by_email(email: str, db: AsyncSession = Depends(get_db)):
    customer = await get_customer_by_email(email, db)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("/", response_model=CustomerOut, status_code=status.HTTP_201_CREATED)
async def create_new_customer(customer: CustomerCreate, db: AsyncSession = Depends(get_db)):
    existing_customer = await get_customer_by_email(customer.email, db)
    if existing_customer:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await create_customer(customer, db)


@router.put("/{customer_id}", response_model=CustomerOut)
async def update_existing_customer(
    customer_id: int, customer_data: CustomerUpdate, db: AsyncSession = Depends(get_db)
):
    customer = await update_customer(customer_id, customer_data, db)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_existing_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    customer = await delete_customer(customer_id, db)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return None

