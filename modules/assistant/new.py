from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from datetime import datetime, timedelta
import json

from db.session import get_db_session
from modules.catalog.service import (
    get_product_by_id, 
    search_products, 
    get_products_by_category,
    get_featured_products,
    get_product_recommendations
)
from modules.cart.service import (
    add_to_cart as svc_add_to_cart,
    get_cart_items,
    update_cart_item,
    remove_from_cart,
    clear_cart,
    get_cart_total
)
from modules.checkout.service import create_order, get_order_by_id
from modules.customer.service import (
    get_user_profile,
    update_user_profile,
    get_user_orders,
    get_user_wishlist,
    add_to_wishlist,
    remove_from_wishlist
)
from modules.inventory.service import check_inventory, reserve_inventory
from modules.pricing.service import get_price, apply_discount, check_promotions
from modules.shipping.service import (
    calculate_shipping_cost,
    get_shipping_options,
    track_shipment
)
from modules.payment.service import process_payment, get_payment_methods
from modules.reviews.service import get_product_reviews, add_review
from modules.analytics.service import log_user_interaction, get_user_behavior
from modules.cart.schema import CartItemCreate, CartItemUpdate
from modules.checkout.schema import OrderCreate, OrderItemCreate
from modules.customer.schema import UserProfileUpdate
from modules.reviews.schema import ReviewCreate


# --- Enhanced Tool Input Schemas ---
class SearchProductsInput(BaseModel):
    query: str = Field(description="Search query for products")
    category_id: Optional[int] = Field(default=None, description="Filter by category")
    min_price: Optional[float] = Field(default=None, description="Minimum price filter")
    max_price: Optional[float] = Field(default=None, description="Maximum price filter")
    sort_by: Optional[str] = Field(default="relevance", description="Sort by: relevance, price_asc, price_desc, rating, newest")
    limit: Optional[int] = Field(default=10, description="Maximum number of results")


class ViewProductInput(BaseModel):
    product_id: int


class AddToCartInput(BaseModel):
    user_id: int
    product_id: int
    quantity: int


class UpdateCartInput(BaseModel):
    user_id: int
    cart_item_id: int
    quantity: int


class RemoveFromCartInput(BaseModel):
    user_id: int
    cart_item_id: int


class ViewCartInput(BaseModel):
    user_id: int


class PlaceOrderItem(BaseModel):
    product_id: int
    quantity: int
    price: float


class PlaceOrderInput(BaseModel):
    user_id: int
    items: List[PlaceOrderItem]
    shipping_address: Optional[Dict[str, str]] = None
    payment_method: Optional[str] = None


class TrackOrderInput(BaseModel):
    user_id: int
    order_id: int


class GetRecommendationsInput(BaseModel):
    user_id: int
    product_id: Optional[int] = None
    limit: Optional[int] = Field(default=5, description="Number of recommendations")


class WishlistInput(BaseModel):
    user_id: int
    product_id: int


class ReviewInput(BaseModel):
    user_id: int
    product_id: int
    rating: int = Field(ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = None


class CompareProductsInput(BaseModel):
    product_ids: List[int] = Field(min_items=2, max_items=5, description="2-5 product IDs to compare")


class CheckInventoryInput(BaseModel):
    product_id: int
    quantity: int


class CalculateShippingInput(BaseModel):
    user_id: int
    shipping_address: Dict[str, str]
    items: List[Dict[str, Any]]


class ApplyDiscountInput(BaseModel):
    user_id: int
    discount_code: str
    cart_total: float


class UserProfileInput(BaseModel):
    user_id: int


class UpdateProfileInput(BaseModel):
    user_id: int
    profile_data: Dict[str, Any]


# --- Enhanced Tool Functions ---

@tool
async def done():
    """Signal that the agent has completed all requested tasks successfully."""
    return "Task completed successfully. Is there anything else I can help you with?"


@tool
def ask_question(question: str):
    """Ask a clarifying question to the user when you need additional information."""
    return f"I need some additional information: {question}"


@tool(args_schema=SearchProductsInput)
async def search_products(
    query: str,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = "relevance",
    limit: Optional[int] = 10
):
    """Search for products based on query and filters.
    
    Perfect for when users ask to find products, search for items,
    or browse products with specific criteria.
    """
    async with get_db_session() as db:
        products = await search_products(
            db, query, category_id, min_price, max_price, sort_by, limit
        )
        if not products:
            return {"message": f"No products found for '{query}'", "products": []}
        
        return {
            "message": f"Found {len(products)} products for '{query}'",
            "products": [
                {
                    "product_id": p.id,
                    "name": p.name,
                    "price": float(p.price),
                    "stock": p.stock,
                    "category": p.category.name if p.category else "Uncategorized",
                    "rating": float(p.average_rating or 0),
                    "review_count": p.review_count or 0
                }
                for p in products
            ]
        }


@tool(args_schema=ViewProductInput)
async def view_product(product_id: int):
    """Get detailed information about a specific product including reviews and specifications."""
    async with get_db_session() as db:
        product = await get_product_by_id(product_id, db)
        if not product:
            return {"error": f"Product with ID {product_id} not found"}
        
        # Get reviews
        reviews = await get_product_reviews(product_id, db, limit=5)
        
        return {
            "product_id": product_id,
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "stock": product.stock,
            "category": product.category.name if product.category else "Uncategorized",
            "brand": product.brand,
            "specifications": product.specifications,
            "images": product.images,
            "average_rating": float(product.average_rating or 0),
            "review_count": product.review_count or 0,
            "recent_reviews": [
                {
                    "rating": r.rating,
                    "comment": r.comment,
                    "user_name": r.user.name,
                    "date": r.created_at.isoformat()
                }
                for r in reviews
            ],
            "status": "available" if product.stock > 0 else "out_of_stock"
        }


@tool(args_schema=ViewCartInput)
async def view_cart(user_id: int):
    """View the user's shopping cart with all items and total cost."""
    async with get_db_session() as db:
        cart_items = await get_cart_items(user_id, db)
        cart_total = await get_cart_total(user_id, db)
        
        if not cart_items:
            return {"message": "Your cart is empty", "items": [], "total": 0}
        
        return {
            "message": f"You have {len(cart_items)} items in your cart",
            "items": [
                {
                    "cart_item_id": item.id,
                    "product_id": item.product_id,
                    "product_name": item.product.name,
                    "price": float(item.product.price),
                    "quantity": item.quantity,
                    "subtotal": float(item.product.price * item.quantity),
                    "image": item.product.images[0] if item.product.images else None
                }
                for item in cart_items
            ],
            "total": float(cart_total),
            "item_count": sum(item.quantity for item in cart_items)
        }


@tool(args_schema=AddToCartInput)
async def add_to_cart(user_id: int, product_id: int, quantity: int):
    """Add a product to the user's shopping cart."""
    if quantity <= 0:
        return {"error": "Quantity must be greater than 0"}
        
    async with get_db_session() as db:
        product = await get_product_by_id(product_id, db)
        if not product:
            return {"error": f"Product with ID {product_id} not found"}
            
        if product.stock < quantity:
            return {
                "error": f"Insufficient stock. Available: {product.stock}, Requested: {quantity}"
            }
        
        item = CartItemCreate(user_id=user_id, product_id=product_id, quantity=quantity)
        result = await svc_add_to_cart(item, db)
        
        # Log interaction for analytics
        await log_user_interaction(user_id, "add_to_cart", {"product_id": product_id, "quantity": quantity}, db)
        
        return {
            "success": True,
            "message": f"Successfully added {result.quantity}x {product.name} to your cart",
            "product_id": result.product_id,
            "quantity": result.quantity,
            "product_name": product.name,
            "cart_item_id": result.id
        }


@tool(args_schema=UpdateCartInput)
async def update_cart_item(user_id: int, cart_item_id: int, quantity: int):
    """Update the quantity of an item in the cart."""
    if quantity <= 0:
        return await remove_from_cart(user_id, cart_item_id)
        
    async with get_db_session() as db:
        update_data = CartItemUpdate(quantity=quantity)
        result = await update_cart_item(cart_item_id, update_data, db)
        
        if result:
            return {
                "success": True,
                "message": f"Updated cart item quantity to {quantity}",
                "cart_item_id": cart_item_id,
                "new_quantity": quantity
            }
        return {"error": "Cart item not found or update failed"}


@tool(args_schema=RemoveFromCartInput)
async def remove_from_cart(user_id: int, cart_item_id: int):
    """Remove an item from the shopping cart."""
    async with get_db_session() as db:
        success = await remove_from_cart(cart_item_id, db)
        if success:
            return {
                "success": True,
                "message": "Item removed from cart",
                "cart_item_id": cart_item_id
            }
        return {"error": "Cart item not found or removal failed"}


@tool(args_schema=ViewCartInput)
async def clear_cart(user_id: int):
    """Clear all items from the user's shopping cart."""
    async with get_db_session() as db:
        success = await clear_cart(user_id, db)
        if success:
            return {
                "success": True,
                "message": "Cart cleared successfully"
            }
        return {"error": "Failed to clear cart"}


@tool(args_schema=GetRecommendationsInput)
async def get_product_recommendations(user_id: int, product_id: Optional[int] = None, limit: Optional[int] = 5):
    """Get personalized product recommendations for the user."""
    async with get_db_session() as db:
        recommendations = await get_product_recommendations(user_id, product_id, limit, db)
        
        if not recommendations:
            # Fallback to featured products
            recommendations = await get_featured_products(limit, db)
        
        return {
            "message": f"Here are {len(recommendations)} product recommendations for you",
            "recommendations": [
                {
                    "product_id": p.id,
                    "name": p.name,
                    "price": float(p.price),
                    "rating": float(p.average_rating or 0),
                    "reason": "Based on your browsing history" if product_id is None else f"Similar to {product_id}",
                    "image": p.images[0] if p.images else None
                }
                for p in recommendations
            ]
        }


@tool(args_schema=CompareProductsInput)
async def compare_products(product_ids: List[int]):
    """Compare multiple products side by side."""
    async with get_db_session() as db:
        products = []
        for pid in product_ids:
            product = await get_product_by_id(pid, db)
            if product:
                products.append(product)
        
        if len(products) < 2:
            return {"error": "Need at least 2 valid products to compare"}
        
        comparison = {
            "message": f"Comparing {len(products)} products",
            "products": [
                {
                    "product_id": p.id,
                    "name": p.name,
                    "price": float(p.price),
                    "rating": float(p.average_rating or 0),
                    "brand": p.brand,
                    "specifications": p.specifications,
                    "stock": p.stock,
                    "review_count": p.review_count or 0
                }
                for p in products
            ]
        }
        
        # Add comparison insights
        prices = [float(p.price) for p in products]
        ratings = [float(p.average_rating or 0) for p in products]
        
        comparison["insights"] = {
            "cheapest": products[prices.index(min(prices))].name,
            "most_expensive": products[prices.index(max(prices))].name,
            "highest_rated": products[ratings.index(max(ratings))].name,
            "price_range": {"min": min(prices), "max": max(prices)},
            "rating_range": {"min": min(ratings), "max": max(ratings)}
        }
        
        return comparison


@tool(args_schema=WishlistInput)
async def add_to_wishlist(user_id: int, product_id: int):
    """Add a product to the user's wishlist."""
    async with get_db_session() as db:
        success = await add_to_wishlist(user_id, product_id, db)
        if success:
            product = await get_product_by_id(product_id, db)
            return {
                "success": True,
                "message": f"Added {product.name if product else 'product'} to your wishlist",
                "product_id": product_id
            }
        return {"error": "Failed to add to wishlist or already exists"}


@tool(args_schema=WishlistInput)
async def remove_from_wishlist(user_id: int, product_id: int):
    """Remove a product from the user's wishlist."""
    async with get_db_session() as db:
        success = await remove_from_wishlist(user_id, product_id, db)
        if success:
            return {
                "success": True,
                "message": "Removed from wishlist",
                "product_id": product_id
            }
        return {"error": "Failed to remove from wishlist"}


@tool(args_schema=UserProfileInput)
async def view_wishlist(user_id: int):
    """View the user's wishlist."""
    async with get_db_session() as db:
        wishlist = await get_user_wishlist(user_id, db)
        return {
            "message": f"You have {len(wishlist)} items in your wishlist",
            "items": [
                {
                    "product_id": item.product.id,
                    "name": item.product.name,
                    "price": float(item.product.price),
                    "rating": float(item.product.average_rating or 0),
                    "stock": item.product.stock,
                    "added_date": item.created_at.isoformat()
                }
                for item in wishlist
            ]
        }


@tool(args_schema=ReviewInput)
async def add_product_review(user_id: int, product_id: int, rating: int, comment: Optional[str] = None):
    """Add a review and rating for a product."""
    async with get_db_session() as db:
        review_data = ReviewCreate(
            user_id=user_id,
            product_id=product_id,
            rating=rating,
            comment=comment
        )
        review = await add_review(review_data, db)
        if review:
            return {
                "success": True,
                "message": "Review added successfully",
                "review_id": review.id,
                "rating": rating
            }
        return {"error": "Failed to add review"}


@tool(args_schema=CheckInventoryInput)
async def check_product_inventory(product_id: int, quantity: int):
    """Check if sufficient inventory is available for a product."""
    async with get_db_session() as db:
        available = await check_inventory(product_id, quantity, db)
        product = await get_product_by_id(product_id, db)
        
        return {
            "product_id": product_id,
            "product_name": product.name if product else "Unknown",
            "requested_quantity": quantity,
            "available_stock": product.stock if product else 0,
            "sufficient_stock": available,
            "message": "Stock available" if available else "Insufficient stock"
        }


@tool(args_schema=CalculateShippingInput)
async def calculate_shipping(user_id: int, shipping_address: Dict[str, str], items: List[Dict[str, Any]]):
    """Calculate shipping cost for cart items to a specific address."""
    async with get_db_session() as db:
        shipping_options = await get_shipping_options(shipping_address, items, db)
        
        return {
            "shipping_address": shipping_address,
            "options": [
                {
                    "method": option["method"],
                    "cost": option["cost"],
                    "estimated_days": option["estimated_days"],
                    "description": option["description"]
                }
                for option in shipping_options
            ]
        }


@tool(args_schema=ApplyDiscountInput)
async def apply_discount_code(user_id: int, discount_code: str, cart_total: float):
    """Apply a discount code to the cart total."""
    async with get_db_session() as db:
        discount_result = await apply_discount(discount_code, cart_total, user_id, db)
        
        if discount_result["valid"]:
            return {
                "success": True,
                "discount_code": discount_code,
                "discount_amount": discount_result["discount_amount"],
                "discount_percentage": discount_result["discount_percentage"],
                "new_total": discount_result["new_total"],
                "message": f"Discount applied! You saved ${discount_result['discount_amount']:.2f}"
            }
        else:
            return {
                "success": False,
                "message": discount_result["reason"]
            }


@tool(args_schema=PlaceOrderInput)
async def place_order(
    user_id: int, 
    items: List[PlaceOrderItem],
    shipping_address: Optional[Dict[str, str]] = None,
    payment_method: Optional[str] = None
):
    """Create and place an order for the user."""
    if not items:
        return {"error": "Cannot place an empty order"}
        
    total_amount = sum(item.quantity * item.price for item in items)
    order_items = [OrderItemCreate(**item.dict()) for item in items]
    order_data = OrderCreate(
        user_id=user_id, 
        total_amount=total_amount, 
        items=order_items,
        shipping_address=shipping_address,
        payment_method=payment_method
    )

    async with get_db_session() as db:
        # Reserve inventory
        for item in items:
            reserved = await reserve_inventory(item.product_id, item.quantity, db)
            if not reserved:
                return {"error": f"Could not reserve inventory for product {item.product_id}"}
        
        order = await create_order(order_data, db)
        
        # Log order placement
        await log_user_interaction(user_id, "place_order", {"order_id": order.id, "total": total_amount}, db)
        
        return {
            "success": True,
            "order_id": order.id,
            "total_amount": float(order.total_amount),
            "message": f"Order successfully placed! Order ID: {order.id}",
            "items_count": len(items),
            "estimated_delivery": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        }


@tool(args_schema=TrackOrderInput)
async def track_order(user_id: int, order_id: int):
    """Track the status and location of an order."""
    async with get_db_session() as db:
        order = await get_order_by_id(order_id, db)
        if not order or order.user_id != user_id:
            return {"error": "Order not found or access denied"}
        
        tracking_info = await track_shipment(order.tracking_number, db) if order.tracking_number else None
        
        return {
            "order_id": order_id,
            "status": order.status,
            "order_date": order.created_at.isoformat(),
            "total_amount": float(order.total_amount),
            "tracking_number": order.tracking_number,
            "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
            "tracking_info": tracking_info,
            "items": [
                {
                    "product_name": item.product.name,
                    "quantity": item.quantity,
                    "price": float(item.price)
                }
                for item in order.items
            ]
        }


@tool(args_schema=UserProfileInput)
async def view_order_history(user_id: int):
    """View the user's order history."""
    async with get_db_session() as db:
        orders = await get_user_orders(user_id, db)
        
        return {
            "message": f"You have {len(orders)} orders",
            "orders": [
                {
                    "order_id": order.id,
                    "date": order.created_at.isoformat(),
                    "total": float(order.total_amount),
                    "status": order.status,
                    "item_count": len(order.items)
                }
                for order in orders
            ]
        }


@tool(args_schema=UserProfileInput)
async def get_user_profile(user_id: int):
    """Get the user's profile information."""
    async with get_db_session() as db:
        profile = await get_user_profile(user_id, db)
        if not profile:
            return {"error": "User profile not found"}
        
        return {
            "user_id": user_id,
            "name": profile.name,
            "email": profile.email,
            "phone": profile.phone,
            "addresses": profile.addresses,
            "preferences": profile.preferences,
            "member_since": profile.created_at.isoformat()
        }


@tool(args_schema=UpdateProfileInput)
async def update_customer_profile(user_id: int, profile_data: Dict[str, Any]):
    """Update the customer's profile information."""
    async with get_db_session() as db:
        update_data = UserProfileUpdate(**profile_data)
        success = await update_customer_profile(user_id, update_data, db)
        
        if success:
            return {
                "success": True,
                "message": "Profile updated successfully",
                "updated_fields": list(profile_data.keys())
            }
        return {"error": "Failed to update profile"}


# Export enhanced tools list
tools = [
    # Core functionality
    view_product,
    search_products,
    view_cart,
    add_to_cart,
    update_cart_item,
    remove_from_cart,
    clear_cart,
    place_order,
    track_order,
    view_order_history,
    
    # Product discovery
    get_product_recommendations,
    compare_products,
    check_product_inventory,
    
    # Wishlist functionality
    add_to_wishlist,
    remove_from_wishlist,
    view_wishlist,
    
    # Reviews and ratings
    add_product_review,
    
    # User management
    get_user_profile,
    update_user_profile,
    
    # Pricing and discounts
    apply_discount_code,
    calculate_shipping,
    
    # Utility tools
    ask_question,
    done
]

tools_by_name = {tool.name: tool for tool in tools}