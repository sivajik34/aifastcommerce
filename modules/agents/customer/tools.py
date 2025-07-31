import logging
from langchain_core.tools import tool
from .schemas import ViewCustomerInput,CreateCustomerInput,AddressInput
from modules.magento.client import magento_client
from typing import  Optional
from utils.log import Logger
logger=Logger(name="customer_tools", log_file="Logs/app.log", level=logging.DEBUG)

@tool(args_schema=ViewCustomerInput)
def get_customer_info(email: str):
    """Retrieve detailed information about a specific customer.
    
    Args:
        email: Customer email
        
    Returns:
        Customer details including name, email.        
    """
    logger.info("get_customer_info tool invoked")
    try:        
        endpoint=f'customers/search?searchCriteria[filterGroups][0][filters][0][field]=email&searchCriteria[filterGroups][0][filters][0][value]={email}'
        data=magento_client.send_request(endpoint=endpoint, method="GET")
        customers=data.get("items",[])
        if customers:
            for customer in customers:
                first_name = customer.get("firstname")
                last_name = customer.get("lastname")
            return {
                "email": email,
                "firstname": first_name,
                "lastname":last_name                
            }    
        else:
            return ("No Customer found with this email")       
        
    except Exception as e:
        return {"error": f"Failed to retrieve customer with email '{email}': {str(e)}"}

@tool(args_schema=CreateCustomerInput)
def create_customer(
    email: str,
    firstname: str,
    lastname: str,
    password: Optional[str] = None,
    website_id: int = 1,
    group_id: int = 1,
    store_id: int = 1,
    address: Optional[AddressInput] = None
):
    """
    Create a new customer account in Magento.
    Password is optional. Address can also be added optionally.
    """
    logger.info("create_customer tool invoked")
    payload = {
        "customer": {
            "email": email,
            "firstname": firstname,
            "lastname": lastname,
            "website_id": website_id,
            "store_id": store_id,
            "group_id": group_id
        }
    }

    if password:
        payload["password"] = password

    if address:
        payload["customer"]["addresses"] = [address.dict(exclude_none=True)]

    try:
        response = magento_client.send_request(
            endpoint="customers",
            method="POST",
            data=payload
        )
        return {
            "message": "Customer created successfully",
            "customer_id": response.get("id"),
            "email": response.get("email"),
            "name": f"{response.get('firstname')} {response.get('lastname')}",
            "status":"success"

        }
    except Exception as e:
        return {"error": f"Failed to create customer: {str(e)}"}
tools=[get_customer_info,create_customer]        