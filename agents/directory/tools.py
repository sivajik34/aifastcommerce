import logging
from langchain_core.tools import tool
from .schemas import GetCountryInput
from magento.client import get_magento_client
from typing import  Optional
from utils.log import Logger

logger=Logger(name="directory_tools", log_file="Logs/app.log", level=logging.DEBUG)

magento_client=get_magento_client()


@tool
def list_countries() -> list:
    """List all countries available in Magento"""
    endpoint="directory/countries"
    response = magento_client.send_request(endpoint=endpoint, method="GET")
   
    return response

@tool(args_schema=GetCountryInput)
def get_country_details(country_id: str) -> dict:
    """
    Get country and region information for the store.
    Retrieves details of a specific country using a country ID (e.g., IN, US).
    you can get region_id under regions section
    """
    logger.info(f"get_country_details invoked with country_id={country_id}")
    try:
        endpoint = f"directory/countries/{country_id}"
        response = magento_client.send_request(endpoint=endpoint, method="GET")

        # Extract and format important fields
        result = {
            "country_id": response.get("id"),
            "two_letter_abbreviation": response.get("two_letter_abbreviation"),
            "three_letter_abbreviation": response.get("three_letter_abbreviation"),
            "full_name_locale": response.get("full_name_locale"),
            "full_name_english": response.get("full_name_english"),
            "regions": [
                {
                    "id": region.get("id"),
                    "code": region.get("code"),
                    "name": region.get("name")
                }
                for region in response.get("available_regions", [])
            ],
            "status": "success",
            "done": True
        }

        logger.info(f"Country details retrieved for {country_id}")
        return result

    except Exception as e:
        logger.error(f"Error retrieving country details for {country_id}: {e}")
        return {"error": f"Failed to retrieve country details for '{country_id}'", "done": True}

@tool
def get_currency_info() -> dict:
    """Get the base, default and current currencies."""
    endpoint="directory/currency"
    response = magento_client.send_request(endpoint=endpoint, method="GET")
    
    return response

tools=[list_countries,get_country_details,get_currency_info]