import logging
from langchain_core.tools import tool
from .schemas import ViewCustomerInput,CreateCustomerInput,AddressInput
from magento.client import get_magento_client
from typing import  Optional
from utils.log import Logger

logger=Logger(name="customer_tools", log_file="Logs/app.log", level=logging.DEBUG)

magento_client=get_magento_client()

@tool(args_schema=ViewCustomerInput)
def get_customer_info(email: str):
    """Retrieve detailed information about a specific customer by email.
    If order creation request  received, pass retrieved customer information to sales_team, do not stop the flow.
    
    Args:
        email: Customer email
        
    Returns:
        Customer details including name, email,customer_id.        
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
                customer_id=customer.get("id")
            return {
                "email": email,
                "firstname": first_name,
                "lastname":last_name,
                "customer_id":customer_id,
                "status": "success",
                "done": True                
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
            "message": f"✅ Customer {response.get('firstname')} {response.get('lastname')} with email {email} created successfully.",
            "customer_id": response.get("id"),
            "email": response.get("email"),
            "name": f"{response.get('firstname')} {response.get('lastname')}",
            "firstname": response.get("firstname"),
            "lastname": response.get("lastname"),
            "status":"success","done": True

        }
    except Exception as e:
        return {"error": f"Failed to create customer: {str(e)}"}
tools=[get_customer_info,create_customer]        