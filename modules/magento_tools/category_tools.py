import logging
from typing import  List,Dict
from langchain_core.tools import tool
from .schemas import CreateCategoryInput,AssignCategoryInput
from .client import magento_client
from utils.log import Logger

logger=Logger(name="category_tools", log_file="Logs/app.log", level=logging.DEBUG)

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
    
tools=[list_all_categories,create_category,assign_product_to_categories]           