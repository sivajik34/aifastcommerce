import logging
from typing import  List,Optional
from langchain_core.tools import tool
from agents.order.schemas import OrderItem,GetOrderByIncrementIdInput,GetOrderIdInput
from magento.client import magento_client
from utils.log import Logger

logger=Logger(name="shared_order_tools", log_file="Logs/app.log", level=logging.DEBUG)

@tool(args_schema=GetOrderByIncrementIdInput)
def get_order_info_by_increment_id(increment_id: str) -> dict:
    """Get full order details using the order increment ID (like 000000123)."""

    logger.info("get_order_info_by_increment_id tool invoked")
    try:
        query_string = (
            "searchCriteria[filterGroups][0][filters][0][field]=increment_id&"
            f"searchCriteria[filterGroups][0][filters][0][value]={increment_id}&"
            "searchCriteria[filterGroups][0][filters][0][conditionType]=eq"
        )
        endpoint = f"orders?{query_string}"
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
    """Fetch internal order ID using the order increment ID."""

    logger.info("get_order_id_by_increment tool invoked")
    try:
        query_string = (
            "searchCriteria[filterGroups][0][filters][0][field]=increment_id&"
            f"searchCriteria[filterGroups][0][filters][0][value]={increment_id}&"
            "searchCriteria[filterGroups][0][filters][0][conditionType]=eq"
        )
        endpoint = f"orders?{query_string}"
        response = magento_client.send_request(endpoint, method="GET")
        items = response.get("items", [])
        if not items:
            return {"error": f"No order found for increment ID {increment_id}"}
        
        return {"order_id": items[0]["entity_id"], "status": items[0]["status"]}
    except Exception as e:
        return {"error": str(e)}

tools=[get_order_info_by_increment_id,get_order_id_by_increment]    