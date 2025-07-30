from langchain_core.tools import tool
from .schemas import ShipmentItem,ShipmentInput
from .client import magento_client
from typing import  List
import logging
from utils.log import Logger
from typing import Optional
from datetime import datetime, timedelta
logger=Logger(name="shipment_tools", log_file="Logs/app.log", level=logging.DEBUG)


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
    
    result = magento_client.send_request(f"order/{order_id}/ship", method="POST",data=payload)
    return result