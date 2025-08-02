import logging
from typing import  List
from langchain_core.tools import tool
from .schemas import InvoiceInput,InvoiceItem
from magento.client import get_magento_client
from utils.log import Logger

logger=Logger(name="invoice_tools", log_file="Logs/app.log", level=logging.DEBUG)

magento_client=get_magento_client()

@tool(args_schema=InvoiceInput)
def create_invoice(order_id: int, items: List[InvoiceItem], comment: str = "Invoice created", notify: bool = True):
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
            endpoint=f"order/{order_id}/invoice",
            method="POST",
            data=payload
        )
        return {"invoice_id": invoice_response}
    except Exception as e:
        logger.error(f"Error creating invoice: {str(e)}")
        return {"error": str(e)}
            
tools=[create_invoice]    