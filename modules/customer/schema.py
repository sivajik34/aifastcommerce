from pydantic import BaseModel, EmailStr, Field

class CustomerBase(BaseModel):
    first_name: str = Field(..., example="John")
    last_name: str = Field(..., example="Doe")
    email: EmailStr = Field(..., example="john.doe@example.com")
    phone: str | None = Field(None, example="+1234567890")


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None


class CustomerOut(CustomerBase):
    id: int

    class Config:
        orm_mode = True

