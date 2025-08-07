import logging
from typing import  List, Optional
from langchain_core.tools import tool
from .schemas import ShipmentItem,ShipmentInput,ShipmentTrackInput
from magento.client import get_magento_client
from utils.log import Logger

logger=Logger(name="shipment_tools", log_file="Logs/app.log", level=logging.DEBUG)

magento_client=get_magento_client()

@tool(args_schema=ShipmentInput)
def create_shipment(order_id: int, items: List[ShipmentItem], notify: bool = True,
                    carrier_code: str = "custom", track_number: str = "N/A", title: str = "Standard Shipping"):
    """Create a shipment for an order. If shipment items information required, first try to get order information from order agent."""

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
    return {"shipment_id": result,"done":True,"status":"success","message":"shipment created successfully."}

@tool(args_schema=ShipmentTrackInput)
def create_shipment_tracking(
    order_id: int,
    parent_id: int,
    track_number: str,
    title: str,
    carrier_code: str,
    weight: float = 0.0,
    qty: int = 1,
    description: str = "",
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None
):
    """Create a tracking record for an existing shipment. Use this after shipment is created."""
    logger.info(f"📦 Creating tracking for order_id={order_id}, shipment_id={parent_id}, track_number={track_number}")

    payload = {
        "entity": {
            "order_id": order_id,
            "parent_id": parent_id,
            "track_number": track_number,
            "title": title,
            "carrier_code": carrier_code,
            "weight": weight,
            "qty": qty,
            "description": description,
            "extension_attributes": {},
        }
    }

    if created_at:
        payload["entity"]["created_at"] = created_at
    if updated_at:
        payload["entity"]["updated_at"] = updated_at

    result = magento_client.send_request("shipment/track", method="POST", data=payload)

    return {
        "status": "success",
        "message": "Tracking created successfully.",
        "tracking_result": result
    }

tools = [create_shipment, create_shipment_tracking]