from langchain_core.tools import tool
from .schemas import LowStockAlertInput,AssignCategoryInput,CreateProductInput,ViewProductInput,UpdateStockInput,SearchProductsInput,CreateCategoryInput,UpdateProductInput
from .client import magento_client
from typing import  Optional,Dict,List
import logging
from utils.log import Logger
logger=Logger(name="product_tools", log_file="Logs/app.log", level=logging.DEBUG)
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
        endpoint = f"products/{sku}"
        product = magento_client.send_request(endpoint=endpoint, method="GET")
        stock_item = product.get("extension_attributes", {}).get("stock_item", {})
        item_id = stock_item.get("item_id")

        if not item_id:
            return {"error": f"Could not find stock item for SKU '{sku}'."}

        # Prepare update payload
        update_endpoint = f"products/{sku}/stockItems/{item_id}"
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

        endpoint = "products?" + "&".join(filters)
        response = magento_client.send_request(endpoint, method="GET")
        items = response.get("items", [])

        return [{"sku": item["sku"], "name": item["name"], "price": item.get("price", 0.0)} for item in items]

    except Exception as e:
        return error_response("search products", e)
    
@tool(args_schema=CreateCategoryInput)
def create_category(name: str,
                    parent_id: int = 2,
                    is_active: bool = True,
                    include_in_menu: bool = True) -> dict:
    """
    Create a new category in Magento under the given parent category ID.
    """
    try:
        payload = {
            "category": {
                "name": name,
                "parent_id": parent_id,
                "is_active": is_active,
                "include_in_menu": include_in_menu
            }
        }
        response = magento_client.send_request("categories", method="POST", data=payload)
        return {"category_id": response.get("id"), "name": response.get("name")}
    except Exception as e:
        return {"error": str(e)}

@tool
def list_all_categories() -> dict:
    """
    List all categories in Magento as a tree structure.
    """
    try:
        response = magento_client.send_request("categories", method="GET")
        return response  # returns category tree
    except Exception as e:
        return {"error": str(e)}

@tool(args_schema=CreateProductInput)
async def create_product(
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
async def update_product(
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

@tool(args_schema=AssignCategoryInput)
async def assign_product_to_categories(sku: str, category_ids: List[int]):
    """Assign a product to one or more categories by updating its category_ids.

    Args:
        sku: Product SKU
        category_ids: List of category IDs to assign to the product

    Returns:
        Confirmation message or error.
    """
    logger.info("assign_product_to_categories tool invoked")
    logger.info(f"category_ids:{category_ids}")    
    try:
        endpoint = f"products/{sku}" 
        category_links = [
            {
                "position": i,
                "category_id": int(cat_id)
            } for i, cat_id in enumerate(category_ids)
        ]
        payload = {
            "product": {
                "sku": sku,
                "extension_attributes": {
                    "category_links": category_links
                }
            }
        }
        response = magento_client.send_request(endpoint, method="PUT", data=payload)
        return {
            "message": f"Product '{sku}' assigned to categories {category_ids}.",
            "updated_product": response
        }
    except Exception as e:
        return {"error": f"Failed to assign categories: {str(e)}"}

from urllib.parse import urlencode

def get_product_skus_by_ids(product_ids: List[int]) -> List[Dict]:
    """Fetch full product info (includes SKU) for given product_ids"""
    if not product_ids:
        return []

    # Construct search criteria query string manually
    base_endpoint = "products"
    query_params = {
        "searchCriteria[filterGroups][0][filters][0][field]": "entity_id",
        "searchCriteria[filterGroups][0][filters][0][value]": ",".join(str(pid) for pid in product_ids),
        "searchCriteria[filterGroups][0][filters][0][condition_type]": "in"
    }
    full_endpoint = f"{base_endpoint}?{urlencode(query_params)}"

    response = magento_client.send_request(
        endpoint=full_endpoint,
        method="GET"
    )
    items = response.get("items", [])
    logger.info(f"countskus{len(items)}")
    return {item["id"]: item["sku"] for item in items  if item.get("type_id") != "configurable"}
    
        
@tool(args_schema=LowStockAlertInput)
async def low_stock_alert(threshold: float = 10.0, scope_id: int = 0, page_size: int = 100) -> List[Dict]:
    """
    Retrieve SKUs with inventory below the specified threshold using Magento's lowStock endpoint.

    Args:
        threshold: Stock quantity threshold (default 10).
        scope_id: Website scope ID (default 0).
        page_size: Number of items per page (default 100).

    Returns:
        List of product SKUs with low stock.
    """
    try:
        all_items = []
        current_page = 1
        page_size = 100

        while True:
            endpoint = (
                f"stockItems/lowStock"
                f"?qty={threshold}&scopeId={scope_id}&pageSize={page_size}&currentPage={current_page}"
            )

            response = magento_client.send_request(endpoint=endpoint, method="GET")
            low_stock_items = response.get("items", [])
            all_items.extend(low_stock_items)
            total_count = response.get("total_count", 0)
            if len(all_items) >= total_count:
                break
            current_page += 1

        product_ids = [item["product_id"] for item in all_items]
        id_to_sku = get_product_skus_by_ids(product_ids)
        logger.info(f"id_to_sku:{len(id_to_sku)}")
        logger.info(f"id_to_sku:{id_to_sku}")
        ll_results = []
        for item in all_items:
            pid = item["product_id"]
            if pid not in id_to_sku:
                continue
            ll_results.append({
                "sku": id_to_sku.get(pid, "SKU"),
                "qty": item.get("qty"),
                "notify_stock_qty": item.get("notify_stock_qty")
            })
        logger.info(f"id_to_sku1:{ll_results}")
        return ll_results

    except Exception as e:
        return {"error": f"Failed to retrieve low stock products: {str(e)}"}


            
tools=[low_stock_alert,view_product,update_stock_qty,search_products,list_all_categories,create_category,update_product,create_product,assign_product_to_categories]     