from langchain_core.tools import tool
from .schemas import ViewProductInput,UpdateStockInput,SearchProductsInput
from .client import magento_client
from typing import  Optional,Dict

def error_response(action: str, error: Exception) -> Dict:
    return {"error": f"Failed to {action}: {str(error)}"}

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
tools=[view_product,update_stock_qty,search_products]     