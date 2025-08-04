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
    """Get details of a specific country by countryId like IN, US, etc."""
    endpoint=f"directory/countries/{country_id}"
    response = magento_client.send_request(endpoint=endpoint, method="GET")
   
    return response

@tool
def get_currency_info() -> dict:
    """Get the base, default and current currencies."""
    endpoint="directory/currency"
    response = magento_client.send_request(endpoint=endpoint, method="GET")
    
    return response

tools=[list_countries,get_country_details,get_currency_info]