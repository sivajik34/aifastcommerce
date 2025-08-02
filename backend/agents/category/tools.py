import logging
from typing import  List,Dict
from langchain_core.tools import tool
from .schemas import CreateCategoryInput,AssignCategoryInput,CategoryMetadata,DeleteCategoryInput 
from magento.client import get_magento_client
from utils.log import Logger
from magento_tools.human import add_human_in_the_loop
from langchain_core.output_parsers import PydanticOutputParser

logger=Logger(name="category_tools", log_file="Logs/app.log", level=logging.DEBUG)

magento_client=get_magento_client()

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
    logger.info("create_category tool invoked")
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
        category_id=response.get("id")
        return {"category_id": category_id, "name": response.get("name"), "status": "success", "message": f"Category {name} created successfully with ID {category_id}"}
    except Exception as e:
        return {"error": str(e)} 

@tool(args_schema=AssignCategoryInput)
def assign_product_to_categories(sku: str, category_ids: List[int]):
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
@tool
def get_category_by_id(category_id: int) -> dict:
    """
    Get category details by ID.
    """
    logger.info("get_category_by_id tool invoked")
    try:
        endpoint = f"categories/{category_id}"
        response = magento_client.send_request(endpoint, method="GET")
        return response
    except Exception as e:
        return {"error": str(e)}
@tool
def update_category(category_id: int, updates: Dict) -> dict:
    """
    Update an existing category using its ID and update fields.
    
    Example 'updates' can include:
    {
        "name": "New Name",
        "is_active": False,
        "include_in_menu": True
    }
    """
    logger.info("update_category tool invoked")
    try:
        payload = {
            "category": updates
        }
        endpoint = f"categories/{category_id}"
        response = magento_client.send_request(endpoint, method="PUT", data=payload)
        return {
            "category_id": category_id,
            "updated_fields": updates,
            "status": "success",
            "message": f"Category {category_id} updated successfully"
        }
    except Exception as e:
        return {"error": str(e)}

@tool(args_schema=DeleteCategoryInput)
def delete_category(category_id: int) -> dict:
    """
    Delete a category by its ID.
    """
    logger.info("delete_category tool invoked")
    try:
        endpoint = f"categories/{category_id}"
        response = magento_client.send_request(endpoint, method="DELETE")
        return {
            "status": "success",
            "message": f"Category {category_id} deleted successfully"
        }
    except Exception as e:
        return {"error": str(e)}

@tool
def get_products_by_category_id(category_id: int) -> dict:
    """
    Get all products assigned to a specific category by ID.
    """
    logger.info("get_products_by_category_id tool invoked")
    try:
        endpoint = f"categories/{category_id}/products"
        response = magento_client.send_request(endpoint, method="GET")
        return {
            "category_id": category_id,
            "products": response
        }
    except Exception as e:
        return {"error": str(e)}

@tool
def find_category_by_name(name: str) -> dict:
    """
    Find a category by its name and return its ID and path.
    """
    logger.info(f"Searching for category by name: {name}")
    try:
        all_categories = magento_client.send_request("categories", method="GET")
        
        def search_category_tree(node):
            if node["name"].lower() == name.lower():
                return node
            for child in node.get("children_data", []):
                result = search_category_tree(child)
                if result:
                    return result
            return None
        
        matched = search_category_tree(all_categories)
        if matched:
            return {
                "id": matched["id"],
                "name": matched["name"],
                "path": matched.get("path"),
                "level": matched.get("level"),
                "is_active": matched.get("is_active")
            }
        else:
            return {"error": f"Category '{name}' not found"}
    except Exception as e:
        return {"error": str(e)}
@tool
def update_category_by_name(name: str, updates: Dict) -> dict:
    """
    Update a category by its name instead of ID.
    """
    logger.info(f"update_category_by_name invoked for {name}")
    try:
        match = find_category_by_name(name)
        if "error" in match:
            return match

        category_id = match["id"]
        return update_category(category_id, updates)
    except Exception as e:
        return {"error": str(e)}
@tool
def delete_category_by_name(name: str) -> dict:
    """
    Delete a category by its name instead of ID.
    """
    logger.info(f"delete_category_by_name invoked for {name}")
    try:
        match = find_category_by_name(name)
        if "error" in match:
            return match

        category_id = match["id"]
        return delete_category({"category_id": category_id})
    except Exception as e:
        return {"error": str(e)}
    
from langchain_core.tools import Tool
from langchain_core.prompts import ChatPromptTemplate



def get_category_seo_by_name_tool(llm):
    """
    Generate category seo such as description,meta_title,meta_keywords,meta_description by its name instead of ID.
    """
    parser = PydanticOutputParser(pydantic_object=CategoryMetadata)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an SEO expert for an e-commerce platform. Return metadata as JSON."),
        ("human", "Generate SEO metadata for the category '{category_name}'.\n\n{format_instructions}")
    ])

    chain = prompt.partial(format_instructions=parser.get_format_instructions()) | llm | parser

    def _update_category_seo(category_name: str) -> dict:
        try:
            logger.info(f"Generating metadata for category: {category_name}")

            # Step 1: Find category by name
            match = find_category_by_name(category_name)
            if "error" in match:
                return match
            category_id = match["id"]

            # Step 2: Generate metadata via LLM
            metadata: CategoryMetadata = chain.invoke({"category_name": category_name})
            logger.info(f"Generated metadata: {metadata.model_dump()}")
            return metadata
            # Step 3: Prepare payload for Magento
            payload = {
                "category": {
                    "description": metadata.description,
                    "meta_title": metadata.meta_title,
                    "meta_keywords": metadata.meta_keywords,
                    "meta_description": metadata.meta_description
                }
            }

            logger.info(f"payload category seo: {payload}")

            # Step 4: Update category
            endpoint = f"categories/{category_id}"
            response = magento_client.send_request(endpoint, method="PUT", data=payload)

            return {
                "message": f"Metadata updated for category '{category_name}' (ID: {category_id})",
                "metadata": metadata.model_dump(),
                "magento_response": response
            }

        except Exception as e:
            logger.error(f"Error updating SEO metadata: {str(e)}")
            return {"error": str(e)}

    return Tool.from_function(
        name="generate_category_seo_by_name",
        description="Generates  SEO metadata for a Magento category based on its name.",
        func=_update_category_seo
    )


    
tools=[list_all_categories,create_category,assign_product_to_categories,get_category_by_id,
    update_category,
    add_human_in_the_loop(delete_category),
    get_products_by_category_id, find_category_by_name,
    update_category_by_name,
    add_human_in_the_loop(delete_category_by_name)]           