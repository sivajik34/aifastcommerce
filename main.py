from fastapi import FastAPI
from modules.assistant.routes import router as assistant_router
from modules.catalog.routes import router as catalog_router
from modules.cart.routes import router as cart_router
from modules.checkout.routes import router as order_router

app = FastAPI()
app.include_router(catalog_router)
app.include_router(cart_router)
app.include_router(order_router)
app.include_router(assistant_router)
