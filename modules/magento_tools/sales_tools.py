from langchain_core.tools import tool
from .schemas import CreateOrderInput,OrderItem,AddressInput
from .client import magento_client
from typing import  List
import logging
from utils.log import Logger
logger=Logger(name="sales_tools", log_file="Logs/app.log", level=logging.DEBUG)
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
tools=[create_order_for_customer]    