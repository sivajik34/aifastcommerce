from langchain_core.tools import tool
from .schemas import CreateOrderInput,OrderItem,InvoiceInput,InvoiceItem,ShipmentItem,ShipmentInput,GetOrderByIncrementIdInput,GetOrderIdInput,CancelOrderInput,GetOrdersInput
from .client import magento_client
from typing import  List
import logging
from utils.log import Logger
from typing import Optional
from datetime import datetime, timedelta
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

@tool(args_schema=CreateOrderInput)
async def create_order_for_guest(
    customer_email: str,
    firstname: str,
    lastname: str,
    items: List[OrderItem],
    payment_method: str = "checkmo"
):
    """
    Place an order for a guest (non-registered) customer using Magento 2 REST guest-carts APIs.
    """
    try:
        # Step 1: Create a guest cart
        cart_id = magento_client.send_request(
            endpoint="/rest/V1/guest-carts",
            method="POST"
        )
        if not cart_id:
            return {"error": "Failed to create guest cart."}
        logger.info(f"Guest cart ID: {cart_id}")

        # Step 2: Add items to the guest cart
        for item in items:
            add_item_payload = {
                "cartItem": {
                    "quote_id": cart_id,
                    "sku": item.sku,
                    "qty": item.qty
                }
            }
            magento_client.send_request(
                endpoint=f"/rest/V1/guest-carts/{cart_id}/items",
                method="POST",
                data=add_item_payload
            )

        # Step 3: Prepare shipping & billing address
        address = {
            "region": "NY",
            "region_id": 43,
            "region_code": "NY",
            "country_id": "US",
            "street": ["456 Guest St"],
            "telephone": "9876543210",
            "postcode": "10002",
            "city": "Brooklyn",
            "firstname": firstname,
            "lastname": lastname,
            "email": customer_email
        }

        # Step 4: Set shipping and billing info
        shipping_info_payload = {
            "addressInformation": {
                "shipping_address": address,
                "billing_address": address,
                "shipping_method_code": "flatrate",
                "shipping_carrier_code": "flatrate"
            }
        }
        magento_client.send_request(
            endpoint=f"/rest/V1/guest-carts/{cart_id}/shipping-information",
            method="POST",
            data=shipping_info_payload
        )

        # Step 5: Set payment method and place the order
        payment_payload = {
            "paymentMethod": {
                "method": payment_method
            },
            "billing_address": address,
            "email": customer_email
        }

        order_response = magento_client.send_request(
            endpoint=f"/rest/V1/guest-carts/{cart_id}/payment-information",
            method="POST",
            data=payment_payload
        )

        order_increment_id = order_response
        logger.info(f"Guest order_increment_id: {order_increment_id}")

        return {
            "order_increment_id": order_increment_id,
            "guest_email": customer_email
        }

    except Exception as e:
        logger.error(f"Error placing guest order: {str(e)}")
        return {"error": f"Failed to create guest order: {str(e)}"}

@tool(args_schema=InvoiceInput)
async def create_invoice(order_id: int, items: List[InvoiceItem], comment: str = "Invoice created", notify: bool = True):
    """
    Create an invoice for a Magento order.
    """
    try:
        payload = {
            "capture": True,
            "items": [
                {
                    "order_item_id": item.order_item_id,
                    "qty": item.qty,
                    "extension_attributes": {}
                }
                for item in items
            ],
            "notify": notify,
            "appendComment": True,
            "comment": {
                "comment": comment,
                "is_visible_on_front": 0,
                "extension_attributes": {}
            },
            "arguments": {
                "extension_attributes": {}
            }
        }

        invoice_response = magento_client.send_request(
            endpoint=f"/rest/V1/order/{order_id}/invoice",
            method="POST",
            data=payload
        )
        return {"invoice_id": invoice_response}
    except Exception as e:
        logger.error(f"Error creating invoice: {str(e)}")
        return {"error": str(e)}

@tool(args_schema=ShipmentInput)
def create_shipment(order_id: int, items: List[ShipmentItem], notify: bool = True,
                    carrier_code: str = "custom", track_number: str = "N/A", title: str = "Standard Shipping"):
    """Create a shipment for an order. Provide order_id and items (order_item_id, qty)."""
    logger.info(f"🚚 Creating shipment for order_id={order_id} with items={items}")
    payload = {
        "items": [item.dict() for item in items],
        "notify": notify,
        "appendComment": True,
        "comment": {
            "comment": "Auto-generated shipment",
            "is_visible_on_front": 0
        },
        "tracks": [{
            "track_number": track_number,
            "title": title,
            "carrier_code": carrier_code
        }],
        "packages": [],
        "arguments": {
            "extension_attributes": {
                "source_code": "default"
            }
        }
    }
    
    result = magento_client.send_request(f"/rest/V1/order/{order_id}/ship", method="POST",data=payload)
    return result


@tool(args_schema=GetOrderByIncrementIdInput)
def get_order_info_by_increment_id(increment_id: str) -> dict:
    """Get full order details using the order increment ID (like 000000123)."""
    try:
        query_string = (
            "searchCriteria[filterGroups][0][filters][0][field]=increment_id&"
            f"searchCriteria[filterGroups][0][filters][0][value]={increment_id}&"
            "searchCriteria[filterGroups][0][filters][0][conditionType]=eq"
        )
        endpoint = f"/rest/V1/orders?{query_string}"
        response = magento_client.send_request(endpoint, method="GET")
        if response.get("items"):
            return response["items"][0]
        else:
            raise Exception(f"No order found with increment ID {increment_id}")
    except Exception as e:
        logger.error(f"Failed to get order by increment_id: {e}")
        raise Exception("Failed to retrieve order using increment ID")
    
@tool(args_schema=GetOrderIdInput)
def get_order_id_by_increment(increment_id: str) -> dict:
    """Fetch internal order ID using the increment ID."""
    try:
        query_string = (
            "searchCriteria[filterGroups][0][filters][0][field]=increment_id&"
            f"searchCriteria[filterGroups][0][filters][0][value]={increment_id}&"
            "searchCriteria[filterGroups][0][filters][0][conditionType]=eq"
        )
        endpoint = f"/rest/V1/orders?{query_string}"
        response = magento_client.send_request(endpoint, method="GET")
        items = response.get("items", [])
        if not items:
            return {"error": f"No order found for increment ID {increment_id}"}
        return {"order_id": items[0]["entity_id"], "status": items[0]["status"]}
    except Exception as e:
        return {"error": str(e)}

@tool(args_schema=CancelOrderInput)
def cancel_order(order_id: int, comment: Optional[str] = None) -> dict:
    """Cancel an order in Magento by order ID."""
    try:
        endpoint = f"/rest/V1/orders/{order_id}/cancel"
        response = magento_client.send_request(endpoint, method="POST")
        return {
            "success": True,
            "order_id": order_id,
            "message": comment or "Order cancelled"
        }
    except Exception as e:
        return {"error": str(e)} 

@tool(args_schema=GetOrdersInput)
def get_orders(status: Optional[str] = None,
               payment_method: Optional[str] = None,
               page_size: int = 10,
               current_page: int = 1,
               last_n_days: Optional[int] = None) -> dict:
    """
    Retrieve a list of Magento orders with dynamic filters.
    
    Filters supported:
    - status: Filter by order status such as pending , processing etc.
    - payment_method: Filter by payment method
    - last_n_days: Filter by creation date
    """
    try:
        filters = []

        filter_index = 0
        if status:
            filters.append(
                f"searchCriteria[filterGroups][{filter_index}][filters][0][field]=status"
            )
            filters.append(
                f"searchCriteria[filterGroups][{filter_index}][filters][0][value]={status}"
            )
            filters.append(
                f"searchCriteria[filterGroups][{filter_index}][filters][0][conditionType]=eq"
            )
            filter_index += 1

        if payment_method:
            filters.append(
                f"searchCriteria[filterGroups][{filter_index}][filters][0][field]=payment.method"
            )
            filters.append(
                f"searchCriteria[filterGroups][{filter_index}][filters][0][value]={payment_method}"
            )
            filters.append(
                f"searchCriteria[filterGroups][{filter_index}][filters][0][conditionType]=eq"
            )
            filter_index += 1

        if last_n_days:
            date_str = (datetime.utcnow() - timedelta(days=last_n_days)).strftime('%Y-%m-%d %H:%M:%S')
            filters.append(
                f"searchCriteria[filterGroups][{filter_index}][filters][0][field]=created_at"
            )
            filters.append(
                f"searchCriteria[filterGroups][{filter_index}][filters][0][value]={date_str}"
            )
            filters.append(
                f"searchCriteria[filterGroups][{filter_index}][filters][0][conditionType]=gteq"
            )
            filter_index += 1

        # Pagination
        filters.append(f"searchCriteria[pageSize]={page_size}")
        filters.append(f"searchCriteria[currentPage]={current_page}")

        query_string = "&".join(filters)
        endpoint = f"/rest/V1/orders?{query_string}"

        response = magento_client.send_request(endpoint, method="GET")
        return {
            "orders": response.get("items", []),
            "total_count": response.get("total_count", 0)
        }
    except Exception as e:
        return {"error": str(e)}         


            
tools=[get_orders,create_order_for_customer,create_order_for_guest,create_invoice,create_shipment,get_order_info_by_increment_id,get_order_id_by_increment,cancel_order]    