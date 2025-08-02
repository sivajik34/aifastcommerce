import logging
from typing import  Optional,Dict
from langchain_core.tools import tool
from langchain.tools import Tool
from langchain_core.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from datetime import datetime, timedelta,timezone
import urllib.parse
from .schemas import ProductDescription,TopSellingProductsInput,CreateProductInput,ViewProductInput,SearchProductsInput,UpdateProductInput,DeleteProductInput
from modules.magento.client import magento_client
from utils.log import Logger
from modules.magento_tools.human import add_human_in_the_loop

logger=Logger(name="product_tools", log_file="Logs/app.log", level=logging.DEBUG)

def error_response(action: str, error: Exception) -> Dict:
    return {"error": f"Failed to {action}: {str(error)}"}

@tool(args_schema=ViewProductInput)
def view_product(sku: str):
    """Retrieve detailed information about a specific product, including associated products if applicable."""
    logger.info("view_product tool invoked")
    try:
        # Step 1: Get main product
        endpoint = f"products/{sku}"
        product = magento_client.send_request(endpoint=endpoint, method="GET")

        name = product.get("name")
        price = product.get("price", 0.0)
        stock_item = product.get("extension_attributes", {}).get("stock_item", {})
        stock_qty = stock_item.get("qty", 0)
        is_in_stock = stock_item.get("is_in_stock", False)
        type_id = product.get("type_id")

        result = {
            "sku": sku,
            "name": name,
            "type": type_id,
            "price": float(price),
            "stock": stock_qty,
            "status": "available" if is_in_stock else "out_of_stock"
        }

        detailed_associated = []

        # Configurable Products
        if type_id == "configurable":
            children_endpoint = f"configurable-products/{sku}/children"
            children = magento_client.send_request(endpoint=children_endpoint, method="GET")

            for child in children:
                child_sku = child.get("sku")
                child_details = magento_client.send_request(endpoint=f"products/{child_sku}", method="GET")
                child_stock = child_details.get("extension_attributes", {}).get("stock_item", {})
                detailed_associated.append({
                    "sku": child_sku,
                    "name": child_details.get("name"),
                    "price": float(child_details.get("price", 0.0)),
                    "stock": child_stock.get("qty", 0),
                    "status": "available" if child_stock.get("is_in_stock", False) else "out_of_stock"
                })

        # Grouped Products
        elif type_id == "grouped":
            links_endpoint = f"products/{sku}/links/associated"
            links = magento_client.send_request(endpoint=links_endpoint, method="GET")

            for item in links:
                child_sku = item.get("linked_product_sku")
                child_details = magento_client.send_request(endpoint=f"products/{child_sku}", method="GET")
                child_stock = child_details.get("extension_attributes", {}).get("stock_item", {})
                detailed_associated.append({
                    "sku": child_sku,
                    "name": child_details.get("name"),
                    "price": float(child_details.get("price", 0.0)),
                    "stock": child_stock.get("qty", 0),
                    "status": "available" if child_stock.get("is_in_stock", False) else "out_of_stock"
                })

        # Bundle Products
        elif type_id == "bundle":
            options_endpoint = f"bundle-products/{sku}/options/all"
            options = magento_client.send_request(endpoint=options_endpoint, method="GET")

            for option in options:
                for link in option.get("product_links", []):
                    child_sku = link.get("sku")
                    child_details = magento_client.send_request(endpoint=f"products/{child_sku}", method="GET")
                    child_stock = child_details.get("extension_attributes", {}).get("stock_item", {})
                    detailed_associated.append({
                        "sku": child_sku,
                        "name": child_details.get("name"),
                        "price": float(child_details.get("price", 0.0)),
                        "stock": child_stock.get("qty", 0),
                        "status": "available" if child_stock.get("is_in_stock", False) else "out_of_stock"
                    })

        if detailed_associated:
            result["associated_products"] = detailed_associated

        return result

    except Exception as e:
        logger.error("Failed to retrieve product details")
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
    logger.info("search_products tool invoked")
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
    logger.info("create_product tool invoked")
   
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
        return {"product_id": response.get("id"), "sku": response.get("sku"),"status":"success","message": f"Product {name} ({sku}) created successfully."}
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

@tool(args_schema=DeleteProductInput)
def delete_product(sku: str):
    """Delete a product from Magento using its SKU.

    This action is irreversible. Use only if you're sure the product should be removed.
    """
    logger.info("delete_product tool invoked")  

    try:
        endpoint = f"products/{sku}"
        magento_client.send_request(endpoint, method="DELETE")
        return {"sku": sku, "status": "deleted", "message": f"Product with SKU '{sku}' deleted successfully."}
    except Exception as e:
        return {"error": f"Failed to delete product {sku}: {str(e)}"}
    
delete_product_with_hitl = add_human_in_the_loop(delete_product) 


def enhance_product_description_tool(llm):
    """
    Creates a tool that enhances or generates product descriptions using an LLM.
    """

    parser = PydanticOutputParser(pydantic_object=ProductDescription)

    prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a product copywriting expert for an e-commerce store."),
    ("human", (
        "Write short_description and full description for product with SKU '{sku}'.\n"
        "Product name: {name}\n"
        "Existing description: {description}\n"
        "Existing short description: {short_description}\n\n"
        "{format_instructions}"
    ))
])

    chain = prompt.partial(format_instructions=parser.get_format_instructions()) | llm | parser

    def _enhance_description(sku: str) -> dict:
        try:
            logger.info(f"Enhancing product description for SKU: {sku}")

            # Step 1: Fetch existing product
            product = magento_client.send_request(f"products/{sku}", method="GET")
            if not product:
                return {"error": f"Product with SKU '{sku}' not found"}

            # Step 2: If descriptions exist, send to LLM to enhance
            def extract_custom_attribute(custom_attributes, code):
                for attr in custom_attributes:
                    if attr.get("attribute_code") == code:
                        return attr.get("value", "")
                return ""

            custom_attrs = product.get("custom_attributes", [])
            short_desc = extract_custom_attribute(custom_attrs, "short_description")
            desc = extract_custom_attribute(custom_attrs, "description")
            name =product.get("name")

            input_data = {
                "name":name,
                "sku": sku,
                "short_description": short_desc,
                "description": desc,
            }

            # Step 3: LLM generates new content
            enhanced: ProductDescription = chain.invoke(input_data)
            logger.info(f"Generated descriptions: {enhanced.model_dump()}")

            # Step 4: Update product in Magento
            payload = {
                "product": {
                    "sku": sku,
                    "custom_attributes": [
                        {"attribute_code": "description", "value": enhanced.description},
                        {"attribute_code": "short_description", "value": enhanced.short_description}
                    ]
                }
            }

            response = magento_client.send_request(f"products/{sku}", method="PUT", data=payload)

            return {
                "message": f"Descriptions updated for SKU '{sku}'",
                "generated": enhanced.model_dump(),
                "magento_response": response
            }

        except Exception as e:
            logger.error(f"Error enhancing product description: {str(e)}")
            return {"error": str(e)}

    return Tool.from_function(
        name="enhance_product_description_by_sku",
        description="Enhances or generates product short_description and description based on SKU using LLM.",
        func=_enhance_description
    )

@tool(args_schema=TopSellingProductsInput)
def top_selling_products(limit: int = 10, last_n_days: Optional[int] = 7,rank_by: str = "quantity") -> list:
    """
    Fetches top-selling product SKUs from Magento orders within the last N days.

    Args:
        limit (int): Number of top-selling products to return. Defaults to 10.
        last_n_days (int): Time window in days to consider orders from. Defaults to 7.
        rank_by (str): Rank products by 'quantity' or 'revenue'. Defaults to 'quantity'.

    Returns:
        List[Dict[str, Any]]: List of top-selling SKUs with total quantity or revenue.
    """
    try:
        now = datetime.now(timezone.utc)
        from_date = (now - timedelta(days=last_n_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Encode searchCriteria into query string
        filters = {
            "searchCriteria[filterGroups][0][filters][0][field]": "created_at",
            "searchCriteria[filterGroups][0][filters][0][value]": from_date,
            "searchCriteria[filterGroups][0][filters][0][conditionType]": "gteq",
            "searchCriteria[pageSize]": "100"
        }
        query_string = urllib.parse.urlencode(filters)

        endpoint = f"orders?{query_string}"

        response = magento_client.send_request(
            method="GET",
            endpoint=endpoint
        )

        items = response.get("items", [])
        product_sales = {}

        for order in items:
            for item in order.get("items", []):
                sku = item.get("sku")
                qty = item.get("qty_ordered", 0)
                price = item.get("price", 0.0)
                if not sku:
                    continue

                if rank_by == "revenue":
                    # Sum revenue: price * qty
                    product_sales[sku] = product_sales.get(sku, 0.0) + (price * qty)
                else:
                    # Default: sum quantity ordered
                    product_sales[sku] = product_sales.get(sku, 0) + qty

        sorted_sales = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)

        if rank_by == "revenue":
            return [
                {"sku": sku, "total_revenue": round(revenue, 2)}
                for sku, revenue in sorted_sales[:limit]
            ]
        else:
            return [
                {"sku": sku, "quantity_ordered": qty}
                for sku, qty in sorted_sales[:limit]
            ]

    except Exception as e:
        return [{"error": f"Failed to retrieve top-selling products: {str(e)}"}]
               
tools=[top_selling_products,view_product,search_products,update_product,create_product,delete_product_with_hitl]     