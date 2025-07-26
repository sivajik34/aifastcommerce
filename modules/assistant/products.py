from typing import Optional, List
from pydantic import BaseModel
from langchain_core.tools import tool
from .magento_oauth_client import MagentoOAuthClient
from utils import common


# Load Magento credentials
env_vars = common.get_required_env_vars([
    "MAGENTO_BASE_URL",
    "MAGENTO_CONSUMER_KEY",
    "MAGENTO_CONSUMER_SECRET",
    "MAGENTO_ACCESS_TOKEN",
    "MAGENTO_ACCESS_TOKEN_SECRET",
    "MAGENTO_VERIFY_SSL"
])

magento_client = MagentoOAuthClient(
    base_url=env_vars["MAGENTO_BASE_URL"],
    consumer_key=env_vars["MAGENTO_CONSUMER_KEY"],
    consumer_secret=env_vars["MAGENTO_CONSUMER_SECRET"],
    access_token=env_vars["MAGENTO_ACCESS_TOKEN"],
    access_token_secret=env_vars["MAGENTO_ACCESS_TOKEN_SECRET"],
    verify_ssl=env_vars["MAGENTO_VERIFY_SSL"].lower() == "true"
)


# -------------------------------
# Pydantic Schemas
# -------------------------------

class GetProductBySkuSchema(BaseModel):
    sku: str


class CreateProductSchema(BaseModel):
    sku: str
    name: str
    price: float
    status: int  # 1 = enabled, 0 = disabled
    type_id: str  # 'simple', 'virtual', etc.
    attribute_set_id: int
    weight: Optional[float] = None
    visibility: Optional[int] = 4
    custom_attributes: Optional[List[dict]] = []


class UpdateProductSchema(BaseModel):
    sku: str
    update_fields: dict


class DeleteProductSchema(BaseModel):
    sku: str


# -------------------------------
# Tools
# -------------------------------

@tool("get_all_products", return_direct=False)
def get_all_products_tool() -> dict:
    """Fetch all products from the Magento catalog."""
    return magento_client.get("V1/products?searchCriteria=")


@tool("get_product_by_sku", args_schema=GetProductBySkuSchema, return_direct=False)
def get_product_by_sku_tool(args: GetProductBySkuSchema) -> dict:
    """Fetch a single product using its SKU."""
    return magento_client.get(f"V1/products/{args.sku}")


@tool("create_product", args_schema=CreateProductSchema, return_direct=False)
def create_product_tool(args: CreateProductSchema) -> dict:
    """Create a new product in Magento."""
    product_payload = {
        "product": {
            "sku": args.sku,
            "name": args.name,
            "price": args.price,
            "status": args.status,
            "type_id": args.type_id,
            "attribute_set_id": args.attribute_set_id,
            "visibility": args.visibility,
            "weight": args.weight,
            "extension_attributes": {},
            "custom_attributes": args.custom_attributes or []
        }
    }
    return magento_client.post("V1/products", json=product_payload)


@tool("update_product", args_schema=UpdateProductSchema, return_direct=False)
def update_product_tool(args: UpdateProductSchema) -> dict:
    """Update an existing product in Magento by SKU."""
    product_payload = {
        "product": args.update_fields
    }
    return magento_client.put(f"V1/products/{args.sku}", json=product_payload)


@tool("delete_product", args_schema=DeleteProductSchema, return_direct=False)
def delete_product_tool(args: DeleteProductSchema) -> dict:
    """Delete a product in Magento using its SKU."""
    return magento_client.delete(f"V1/products/{args.sku}")
