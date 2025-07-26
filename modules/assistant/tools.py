import logging
from typing import List, Optional,Dict,Literal
from pydantic import BaseModel,Field,EmailStr
from langchain_core.tools import tool

from utils import common
from .magento_oauth_client import MagentoOAuthClient
from utils.log import Logger
logger=Logger(name="tools", log_file="Logs/app.log", level=logging.DEBUG)
# --- Tool Input Schemas ---
class ViewProductInput(BaseModel):
    sku: str    

class ViewCustomerInput(BaseModel):
    email: EmailStr

class AddressInput(BaseModel):
    firstname: str
    lastname: str
    street: List[str]
    city: str
    region: Optional[str]
    region_id: Optional[int]
    postcode: str
    country_id: Literal["IN", "US", "UK", "CA", "AU"]  # Add more as needed
    telephone: str
    default_shipping: Optional[bool] = False
    default_billing: Optional[bool] = False

class CreateCustomerInput(BaseModel):
    email: EmailStr
    firstname:str
    lastname:str
    password:Optional[str] = None
    store_view_code: Optional[str] = "default"
    website_id: Optional[int] = 1
    store_id: Optional[int] = 1
    group_id: Optional[int] = 1
    address: Optional[AddressInput] = None

class SearchProductsInput(BaseModel):
    query: Optional[str] = Field(description="Search query for products")
    category_id: Optional[int] = Field(default=None, description="Filter by category")
    min_price: Optional[float] = Field(default=None, description="Minimum price filter")
    max_price: Optional[float] = Field(default=None, description="Maximum price filter")
    sort_by: Optional[str] = Field(default="relevance", description="Sort by: relevance, price_asc, price_desc, rating, newest")
    limit: Optional[int] = Field(default=10, description="Maximum number of results")

def error_response(action: str, error: Exception) -> Dict:
    return {"error": f"Failed to {action}: {str(error)}"}

env_vars = common.get_required_env_vars(["MAGENTO_BASE_URL","MAGENTO_CONSUMER_KEY","MAGENTO_CONSUMER_SECRET","MAGENTO_ACCESS_TOKEN","MAGENTO_ACCESS_TOKEN_SECRET","MAGENTO_VERIFY_SSL"])
#print(env_vars)
magento_client = MagentoOAuthClient(
    base_url=env_vars["MAGENTO_BASE_URL"],
    consumer_key=env_vars["MAGENTO_CONSUMER_KEY"],
    consumer_secret=env_vars["MAGENTO_CONSUMER_SECRET"], 
    access_token=env_vars["MAGENTO_ACCESS_TOKEN"],
    access_token_secret=env_vars["MAGENTO_ACCESS_TOKEN_SECRET"],
    verify_ssl=False
)

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

@tool(args_schema=ViewCustomerInput)
async def get_customer_info(email: str):
    """Retrieve detailed information about a specific customer.
    
    Args:
        email: Customer email
        
    Returns:
        Customer details including name, email.        
    """
    try:        
        endpoint=f'/rest/V1/customers/search?searchCriteria[filterGroups][0][filters][0][field]=email&searchCriteria[filterGroups][0][filters][0][value]={email}'
        data=magento_client.send_request(endpoint=endpoint, method="GET")
        customers=data.get("items",[])
        if customers:
            for customer in customers:
                first_name = customer.get("firstname")
                last_name = customer.get("lastname")
            return {
                "email": email,
                "firstname": first_name,
                "lastname":last_name                
            }    
        else:
            return ("No Customer found with this email")       
        
    except Exception as e:
        return {"error": f"Failed to retrieve customer with email '{email}': {str(e)}"}

@tool(args_schema=CreateCustomerInput)
async def create_customer(
    email: str,
    firstname: str,
    lastname: str,
    password: Optional[str] = None,
    website_id: int = 1,
    group_id: int = 1,
    store_id: int = 1,
    address: Optional[AddressInput] = None
):
    """
    Create a new customer account in Magento (Admin context).
    Password is optional. Address can also be added optionally.
    """

    payload = {
        "customer": {
            "email": email,
            "firstname": firstname,
            "lastname": lastname,
            "website_id": website_id,
            "store_id": store_id,
            "group_id": group_id
        }
    }

    if password:
        payload["password"] = password

    if address:
        payload["customer"]["addresses"] = [address.dict(exclude_none=True)]

    try:
        response = magento_client.send_request(
            endpoint="/rest/V1/customers",
            method="POST",
            data=payload
        )
        return {
            "message": "Customer created successfully",
            "customer_id": response.get("id"),
            "email": response.get("email"),
            "name": f"{response.get('firstname')} {response.get('lastname')}"
        }
    except Exception as e:
        return {"error": f"Failed to create customer: {str(e)}"}                  


@tool(args_schema=ViewProductInput)
async def view_product(sku: str):
    """Retrieve detailed information about a specific product.
    
    Args:
        sku: The unique identifier of the product
        
    Returns:
        Product details including name, current price, and available stock quantity.
        Use this before adding items to cart or when users ask about specific products.
    """
    try:
        endpoint = f"/rest/V1/products/{sku}"
        product=magento_client.send_request(endpoint=endpoint, method="GET")
        name = product.get("name")
        price = product.get("price", product.get("price", 0.0))
        stock_item = product.get("extension_attributes", {}).get("stock_item", {})
        stock_qty = stock_item.get("qty", 0)
        is_in_stock = stock_item.get("is_in_stock", False)
        return {
                "sku": sku,
                "name": name,
                "price": float(price),
                "stock": stock_qty,
                "status": "available" if is_in_stock else "out_of_stock"
            }
    except Exception as e:
        return {"error": f"Failed to retrieve product with SKU '{sku}': {str(e)}"}

class UpdateStockInput(BaseModel):
    sku: str
    qty: float
    is_in_stock: bool = True  # Optional, defaults to True

@tool(args_schema=UpdateStockInput)
async def update_stock_qty(sku: str, qty: float, is_in_stock: bool = True):
    """Update stock quantity for a specific product.
    
    Args:
        sku: The unique identifier of the product.
        qty: New quantity to set for the product.
        is_in_stock: Whether the product is in stock or not.
        
    Returns:
        Confirmation message with updated quantity and status.
    """
    try:
        # Fetch item ID (required for the stock update endpoint)
        endpoint = f"/rest/V1/products/{sku}"
        product = magento_client.send_request(endpoint=endpoint, method="GET")
        stock_item = product.get("extension_attributes", {}).get("stock_item", {})
        item_id = stock_item.get("item_id")

        if not item_id:
            return {"error": f"Could not find stock item for SKU '{sku}'."}

        # Prepare update payload
        update_endpoint = f"/rest/V1/products/{sku}/stockItems/{item_id}"
        payload = {
            "stockItem": {
                "qty": qty,
                "is_in_stock": is_in_stock
            }
        }

        result = magento_client.send_request(
            endpoint=update_endpoint,
            method="PUT",
            data=payload
        )

        return {
            "sku": sku,
            "updated_qty": qty,
            "is_in_stock": is_in_stock,
            "message": f"Stock quantity for SKU '{sku}' updated successfully."
        }

    except Exception as e:
        return {"error": f"Failed to update stock for SKU '{sku}': {str(e)}"}


@tool(args_schema=SearchProductsInput)
async def search_products(
    query: str,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = "relevance",
    limit: Optional[int] = 10
):
    """Search for products based on query, price, category and sort filters."""
    try:
        filters = []
        if query:
            filters.append(f"searchCriteria[filterGroups][0][filters][0][field]=name")
            filters.append(f"searchCriteria[filterGroups][0][filters][0][value]=%25{query}%25")
            filters.append(f"searchCriteria[filterGroups][0][filters][0][conditionType]=like")

        group = 1
        if category_id:
            filters.append(f"searchCriteria[filterGroups][{group}][filters][0][field]=category_id")
            filters.append(f"searchCriteria[filterGroups][{group}][filters][0][value]={category_id}")
            filters.append(f"searchCriteria[filterGroups][{group}][filters][0][conditionType]=eq")
            group += 1

        if min_price is not None:
            filters.append(f"searchCriteria[filterGroups][{group}][filters][0][field]=price")
            filters.append(f"searchCriteria[filterGroups][{group}][filters][0][value]={min_price}")
            filters.append(f"searchCriteria[filterGroups][{group}][filters][0][conditionType]=gteq")
            group += 1

        if max_price is not None:
            filters.append(f"searchCriteria[filterGroups][{group}][filters][0][field]=price")
            filters.append(f"searchCriteria[filterGroups][{group}][filters][0][value]={max_price}")
            filters.append(f"searchCriteria[filterGroups][{group}][filters][0][conditionType]=lteq")
            group += 1

        filters.append(f"searchCriteria[pageSize]={limit}")
        sort_map = {
            "price_asc": ("price", "ASC"),
            "price_desc": ("price", "DESC"),
            "newest": ("created_at", "DESC")
        }
        sort_field, direction = sort_map.get(sort_by, ("relevance", "DESC"))
        filters.append(f"searchCriteria[sortOrders][0][field]={sort_field}")
        filters.append(f"searchCriteria[sortOrders][0][direction]={direction}")

        endpoint = "/rest/V1/products?" + "&".join(filters)
        response = magento_client.send_request(endpoint, method="GET")
        items = response.get("items", [])

        return [{"sku": item["sku"], "name": item["name"], "price": item.get("price", 0.0)} for item in items]

    except Exception as e:
        return error_response("search products", e) 



class OrderItem(BaseModel):
    sku: str
    qty: int

class CreateOrderInput(BaseModel):
    customer_email: EmailStr
    firstname: str
    lastname: str
    items: List[OrderItem]
    payment_method: Literal["checkmo", "banktransfer", "cashondelivery"] = "checkmo"

@tool(args_schema=CreateOrderInput)
async def create_order_for_customer(
    customer_email: str,
    firstname: str,
    lastname: str,
    items: List[OrderItem],
    payment_method: str = "checkmo"
):
    """
    Place an order for a registered customer using admin System Integration credentials
    following Magento 2 REST API cart + order flow.
    """
    try:
        # Step 1: Get customer ID by email
        endpoint = f"/rest/V1/customers/search?searchCriteria[filterGroups][0][filters][0][field]=email&searchCriteria[filterGroups][0][filters][0][value]={customer_email}"
        customer_data = magento_client.send_request(endpoint, method="GET")
        customers = customer_data.get("items", [])
        if not customers:
            return {"error": f"No customer found with email {customer_email}"}
        
        customer = customers[0]
        customer_id = customer.get("id")
        logger.info(f"customer id:{customer_id}")
        # Step 2: Create a cart (quote) for the customer
        cart_id = magento_client.send_request(
            endpoint=f"/rest/V1/customers/{customer_id}/carts",
            method="POST"
        )
        if not cart_id:
            return {"error": "Failed to create cart for customer."}
        logger.info(f"cart id:{cart_id}")
        # Step 3: Add items to the cart
        for item in items:
            add_item_payload = {
                "cartItem": {
                    "sku": item.sku,
                    "qty": item.qty,
                    "quote_id": str(cart_id)
                }
            }
            magento_client.send_request(
                endpoint=f"/rest/V1/carts/{cart_id}/items",
                method="POST",
                data=add_item_payload
            )

        # Step 4: Prepare billing and shipping address (using dummy/fixed data here)
        address = {
            "region": "NY",
            "region_id": 43,
            "region_code": "NY",
            "country_id": "US",
            "street": ["123 Order St"],
            "telephone": "1234567890",
            "postcode": "10001",
            "city": "New York",
            "firstname": firstname,
            "lastname": lastname,
            "email": customer_email
        }

        # Step 5: Set shipping info (including address and shipping method)
        shipping_info_payload = {
            "addressInformation": {
                "shipping_address": address,
                "billing_address": address,
                "shipping_method_code": "flatrate",
                "shipping_carrier_code": "flatrate"
            }
        }
        magento_client.send_request(
            endpoint=f"/rest/V1/carts/{cart_id}/shipping-information",
            method="POST",
            data=shipping_info_payload
        )

        # Step 6: Place order with payment method
        payment_payload = {
            "method": {
                "method": payment_method
            },
            "billing_address": address,
            "email": customer_email
        }
        magento_client.send_request(
            endpoint=f"/rest/V1/carts/{cart_id}/selected-payment-method",
            method="PUT",
            data=payment_payload
        )
        order_response = magento_client.send_request(
    endpoint=f"/rest/V1/carts/{cart_id}/order",
    method="PUT"
)
        order_increment_id = order_response
        logger.info(f"order_increment_id:{order_increment_id}")
        return {                       
            "order_increment_id": order_increment_id
        }

    except Exception as e:
        logger.error(f"{str(e)}")
        return {"error": f"Failed to create order: {str(e)}"}


# Export tools list
tools = [view_product,search_products,update_stock_qty, get_customer_info,create_customer,create_order_for_customer,ask_question, done]
tools_by_name = {tool.name: tool for tool in tools}