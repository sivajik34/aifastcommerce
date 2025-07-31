import logging
from typing import  Optional,Dict
from langchain_core.tools import tool
from .schemas import CreateProductInput,ViewProductInput,SearchProductsInput,UpdateProductInput
from modules.magento.client import magento_client
from utils.log import Logger

logger=Logger(name="product_tools", log_file="Logs/app.log", level=logging.DEBUG)

def error_response(action: str, error: Exception) -> Dict:
    return {"error": f"Failed to {action}: {str(error)}"}

@tool(args_schema=ViewProductInput)
def view_product(sku: str):
    """Retrieve detailed information about a specific product.
    
    Args:
        sku: The unique identifier of the product
        
    Returns:
        Product details including name, current price, and available stock quantity.
        Use this before adding items to cart or when users ask about specific products.
    """
    try:        
        endpoint = f"products/{sku}"
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


@tool(args_schema=SearchProductsInput)
def search_products(
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

        endpoint = "products?" + "&".join(filters)
        response = magento_client.send_request(endpoint, method="GET")
        items = response.get("items", [])

        return [{"sku": item["sku"], "name": item["name"], "price": item.get("price", 0.0)} for item in items]

    except Exception as e:
        return error_response("search products", e)


@tool(args_schema=CreateProductInput)
def create_product(
    sku: str,
    name: str,
    price: float,
    status: int,
    type_id: str = "simple",
    attribute_set_id: int = 4,
    weight: float = 1.0,
    visibility: int = 4,
    qty: float = 0,
    is_in_stock: bool = True,
):
    """Create a new product in Magento.

    Args:
        sku: Product SKU
        name: Product name
        price: Product price
        status: 1 = enabled, 2 = disabled
        type_id: Product type (simple, virtual, configurable)
        attribute_set_id: ID of the attribute set (default is 4)
        weight: Product weight
        visibility: 1 = Not visible, 2 = Catalog, 3 = Search, 4 = Catalog/Search
        qty: Stock quantity
        is_in_stock: Whether it's in stock

    Returns:
        A confirmation with product ID and SKU if created successfully.
    """
    try:
        payload = {
            "product": {
                "sku": sku,
                "name": name,
                "price": price,
                "status": status,
                "type_id": type_id,
                "attribute_set_id": attribute_set_id,
                "weight": weight,
                "visibility": visibility,
                "extension_attributes": {
                    "stock_item": {
                        "qty": qty,
                        "is_in_stock": is_in_stock
                    }
                }
            }
        }
        response = magento_client.send_request("products", method="POST", data=payload)
        return {"product_id": response.get("id"), "sku": response.get("sku")}
    except Exception as e:
        return {"error": f"Failed to create product: {str(e)}"} 

@tool(args_schema=UpdateProductInput)
def update_product(
    sku: str,
    name: Optional[str] = None,
    price: Optional[float] = None,
    status: Optional[int] = None,
    visibility: Optional[int] = None,
    weight: Optional[float] = None,
    qty: Optional[float] = None,
    is_in_stock: Optional[bool] = None,
):
    """Update an existing product in Magento using its SKU.

    Args:
        sku: Product SKU (required)
        name: New name (optional)
        price: New price (optional)
        status: New status (1 = enabled, 2 = disabled)
        visibility: New visibility (optional)
        weight: New weight (optional)
        qty: New quantity (optional)
        is_in_stock: Stock status (optional)

    Returns:
        Updated product details or error message.
    """
    logger.info("update_product tool invoked")
    try:
        product_data = {"sku": sku}  

        if name is not None:
            product_data["name"] = name
        if price is not None:
            product_data["price"] = price
        if status is not None:
            product_data["status"] = status
        if visibility is not None:
            product_data["visibility"] = visibility
        if weight is not None:
            product_data["weight"] = weight
        if qty is not None or is_in_stock is not None:
            product_data.setdefault("extension_attributes", {})
            product_data["extension_attributes"]["stock_item"] = {}
            if qty is not None:
                product_data["extension_attributes"]["stock_item"]["qty"] = qty
            if is_in_stock is not None:
                product_data["extension_attributes"]["stock_item"]["is_in_stock"] = is_in_stock

        if len(product_data) == 1:  # only `sku` present
            return {"message": "No fields provided to update."}

        payload = {"product": product_data}
        logger.debug(payload)

        endpoint = f"products/{sku}"
        response = magento_client.send_request(endpoint, method="PUT", data=payload)

        return {"updated_product": response}
    except Exception as e:
        return {"error": f"Failed to update product {sku}: {str(e)}"}
            
tools=[view_product,search_products,update_product,create_product]     