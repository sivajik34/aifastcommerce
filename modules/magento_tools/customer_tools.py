from langchain_core.tools import tool
from .schemas import ViewCustomerInput,CreateCustomerInput,AddressInput
from .client import magento_client
from typing import  Optional

@tool(args_schema=ViewCustomerInput)
async def get_customer_info(email: str):
    """Retrieve detailed information about a specific customer.
    
    Args:
        email: Customer email
        
    Returns:
        Customer details including name, email.        
    """
    try:        
        endpoint=f'/rest/V1/customers/search?searchCriteria[filterGroups][0][filters][0][field]=email&searchCriteria[filterGroups][0][filters][0][value]={email}'
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
async def create_customer(
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
    Create a new customer account in Magento (Admin context).
    Password is optional. Address can also be added optionally.
    """

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
            endpoint="/rest/V1/customers",
            method="POST",
            data=payload
        )
        return {
            "message": "Customer created successfully",
            "customer_id": response.get("id"),
            "email": response.get("email"),
            "name": f"{response.get('firstname')} {response.get('lastname')}"
        }
    except Exception as e:
        return {"error": f"Failed to create customer: {str(e)}"}
tools=[get_customer_info,create_customer]        