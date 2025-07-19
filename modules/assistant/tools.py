from typing import List
from pydantic import BaseModel
from langchain_core.tools import tool

from db.session import get_db_session
from modules.catalog.service import get_product_by_id
from modules.cart.service import add_to_cart as svc_add_to_cart
from modules.checkout.service import create_order
from modules.cart.schema import CartItemCreate
from modules.checkout.schema import OrderCreate, OrderItemCreate


# --- Tool Input Schemas ---
class ViewProductInput(BaseModel):
    product_id: int


class AddToCartInput(BaseModel):
    user_id: int
    product_id: int
    quantity: int


class PlaceOrderItem(BaseModel):
    product_id: int
    quantity: int
    price: float


class PlaceOrderInput(BaseModel):
    user_id: int
    items: List[PlaceOrderItem]


# --- Tool Functions ---
@tool
async def done():
    """Signal that the agent has completed all requested tasks successfully.
    
    Call this tool when you have fully completed the user's request and no further 
    actions are needed. This will end the conversation gracefully.
    """
    return "Task completed successfully. Is there anything else I can help you with?"


@tool
def ask_question(question: str):
    """Ask a clarifying question to the user when you need additional information.
    
    Args:
        question: The specific question you want to ask the user
        
    Use this when:
    - You need missing information to complete a task
    - The user's request is ambiguous
    - You need confirmation before taking an action
    """
    return f"I need some additional information: {question}"


@tool(args_schema=ViewProductInput)
async def view_product(product_id: int):
    """Retrieve detailed information about a specific product.
    
    Args:
        product_id: The unique identifier of the product
        
    Returns:
        Product details including name, current price, and available stock quantity.
        Use this before adding items to cart or when users ask about specific products.
    """
    async with get_db_session() as db:
        product = await get_product_by_id(product_id, db)
        if product:
            return {
                "product_id": product_id,
                "name": product.name,
                "price": float(product.price),
                "stock": product.stock,
                "status": "available" if product.stock > 0 else "out_of_stock"
            }
        return {"error": f"Product with ID {product_id} not found"}


@tool(args_schema=AddToCartInput)
async def add_to_cart(user_id: int, product_id: int, quantity: int):
    """Add a specified quantity of a product to the user's shopping cart.
    
    Args:
        user_id: The ID of the user whose cart to modify
        product_id: The ID of the product to add
        quantity: The number of items to add (must be positive)
        
    Always check product availability with view_product before adding to cart.
    Confirm the action was successful before proceeding.
    """
    if quantity <= 0:
        return {"error": "Quantity must be greater than 0"}
        
    async with get_db_session() as db:
        # First check if product exists and has enough stock
        product = await get_product_by_id(product_id, db)
        if not product:
            return {"error": f"Product with ID {product_id} not found"}
            
        if product.stock < quantity:
            return {
                "error": f"Insufficient stock. Available: {product.stock}, Requested: {quantity}"
            }
        
        item = CartItemCreate(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity
        )
        result = await svc_add_to_cart(item, db)
        return {
            "success": True,
            "message": f"Successfully added {result.quantity}x {product.name} to your cart",
            "product_id": result.product_id,
            "quantity": result.quantity,
            "product_name": product.name
        }


@tool(args_schema=PlaceOrderInput)
async def place_order(user_id: int, items: List[PlaceOrderItem]):
    """Create and place an order for the user with the specified items.
    
    Args:
        user_id: The ID of the user placing the order
        items: List of items to order, each containing product_id, quantity, and price
        
    This will create a formal order and process the purchase. Use this only when
    the user explicitly confirms they want to complete their purchase.
    """
    if not items:
        return {"error": "Cannot place an empty order"}
        
    total_amount = sum(item.quantity * item.price for item in items)
    order_items = [OrderItemCreate(**item.dict()) for item in items]
    order_data = OrderCreate(
        user_id=user_id, 
        total_amount=total_amount, 
        items=order_items
    )

    async with get_db_session() as db:
        order = await create_order(order_data, db)
        return {
            "success": True,
            "order_id": order.id,
            "total_amount": float(order.total_amount),
            "message": f"Order successfully placed! Order ID: {order.id}",
            "items_count": len(items)
        }


# Export tools list
tools = [view_product, add_to_cart, place_order, ask_question, done]
tools_by_name = {tool.name: tool for tool in tools}