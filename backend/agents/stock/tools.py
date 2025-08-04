import logging
from typing import  Dict,List
from urllib.parse import urlencode
from langchain_core.tools import tool
from .schemas import LowStockAlertInput,UpdateStockInput
from magento.client import get_magento_client
from utils.log import Logger

logger=Logger(name="stock_tools", log_file="Logs/app.log", level=logging.DEBUG)

magento_client=get_magento_client()

@tool(args_schema=UpdateStockInput)
def update_stock_qty(sku: str, qty: float, is_in_stock: bool = True):
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
            "message": f"Stock quantity for SKU '{sku}' updated successfully.",
            "status":"success",
            "done":True
        }

    except Exception as e:
        return {"error": f"Failed to update stock for SKU '{sku}': {str(e)}"}


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
    return {item["id"]: item["sku"] for item in items  if item.get("type_id") not in {"configurable", "bundle", "grouped"}}
    
        
@tool(args_schema=LowStockAlertInput)
def low_stock_alert(threshold: float = 10.0, scope_id: int = 0, page_size: int = 100) -> List[Dict]:
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
tools=[low_stock_alert,update_stock_qty]