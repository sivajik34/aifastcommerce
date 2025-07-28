import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin, urlencode
from requests_oauthlib import OAuth1
import os
import logging
import json
from typing import List, Optional, Dict, Any,Union

import logging
from utils.log import Logger
logger=Logger(name="magento_oauth_client", log_file="Logs/app.log", level=logging.DEBUG)

class MagentoOAuthClient:

    REST_ENDPOINT_TEMPLATE = "/rest/{store_view_code}/{api_version}/{endpoint}"
    DEFAULT_STORE_VIEW_CODE = "default"
    DEFAULT_API_VERSION = "V1"

    def __init__(
        self,
        base_url: Optional[str] = None,
        consumer_key: Optional[str] = None,
        consumer_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        verify_ssl: bool = False        
    ):
        
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
     
        
        # OAuth1 credentials - try parameters first, then environment variables
        self.consumer_key = consumer_key or os.getenv("MAGENTO_CONSUMER_KEY")
        self.consumer_secret = consumer_secret or os.getenv("MAGENTO_CONSUMER_SECRET")
        self.access_token = access_token or os.getenv("MAGENTO_ACCESS_TOKEN")
        self.access_token_secret = access_token_secret or os.getenv("MAGENTO_ACCESS_TOKEN_SECRET")
        
        # Validate OAuth credentials
        self._validate_oauth_credentials()
        
        # Configure OAuth1 authentication
        self._configure_oauth()
        
        # Initialize requests session with OAuth1 and retry strategy
        self.session = self._create_session()   
       
    
    def _validate_oauth_credentials(self):
        """Validate that all necessary OAuth1 credentials are provided."""
        required_credentials = {
            "consumer_key": self.consumer_key,
            "consumer_secret": self.consumer_secret,
            "access_token": self.access_token,
            "access_token_secret": self.access_token_secret
        }
        
        missing_credentials = [name for name, value in required_credentials.items() if not value]
        
        if missing_credentials:
            raise ValueError(
                f"Missing OAuth1 credentials: {', '.join(missing_credentials)}. "
                f"Please provide them as parameters or set environment variables: "
                f"MAGENTO_CONSUMER_KEY, MAGENTO_CONSUMER_SECRET, MAGENTO_ACCESS_TOKEN, MAGENTO_ACCESS_TOKEN_SECRET"
            )
        
    
    def _configure_oauth(self):
        """Configure OAuth1 authentication for Magento API requests."""
        try:
            self.oauth = OAuth1(
                self.consumer_key,
                self.consumer_secret,
                self.access_token,
                self.access_token_secret,
                signature_method='HMAC-SHA256'
            )
            logger.info("OAuth1 authentication configured successfully")
        except Exception as e:
            raise ValueError(f"Failed to configure OAuth1: {str(e)}")   
   
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with OAuth1 authentication and retry strategy."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Magento-Tool-Generator/1.0'
        })
     
        
        # Configure SSL verification
        session.verify = self.verify_ssl
        #session.auth = self.oauth
    
        return session
    
    def build_endpoint(self, endpoint: str, store_view_code: Optional[str] = None,
                       api_version: Optional[str] = None) -> str:
        """
        Build the full endpoint by injecting the store view code and API version.
        """
        store_view_code = store_view_code or self.DEFAULT_STORE_VIEW_CODE
        api_version = api_version or self.DEFAULT_API_VERSION
        # Make sure endpoint does not start with a slash to avoid duplication
        endpoint = endpoint.lstrip('/')
        return self.REST_ENDPOINT_TEMPLATE.format(
            store_view_code=store_view_code,
            api_version=api_version,
            endpoint=endpoint
        )
    
    def send_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None, 
                    headers: Optional[Dict] = None, extra_options: Optional[Dict] = None,token=None, store_view_code: Optional[str] = None,
                     api_version: Optional[str] = None) -> Union[Dict, str]:
        """Send an HTTP request to the Magento API with OAuth1 authentication."""
        if extra_options is None:
            extra_options = {}

        if headers is None:
            headers = {}
         

        # Set the Content-Type to application/json if not already set
        headers.setdefault('Content-Type', 'application/json')
        if token:
            headers["Authorization"] = f"Bearer {token}"
        # Convert data to JSON if data is provided and method requires body
        json_data = None
        if data and method.upper() in ['POST', 'PUT', 'PATCH', 'DELETE']:
            try:
                json_data =  data  # requests will handle JSON serialization
            except Exception as e:
                raise ValueError(f"Failed to prepare data for request: {str(e)}")

        try:
            formatted_endpoint = self.build_endpoint(endpoint, store_view_code, api_version)
            full_url = urljoin(self.base_url.rstrip('/') + '/', formatted_endpoint.lstrip('/'))
            
            # Make the request with OAuth1 authentication
            response = self.session.request(
                method=method.upper(),
                url=full_url,
                json=json_data,
                headers=headers,
                timeout=self.timeout,
                verify=extra_options.get('verify', self.verify_ssl),
                auth=None if 'Authorization' in headers else self.oauth
            )
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as http_err:
                try:
                    error_body = response.json()
                except Exception:
                    error_body = response.text
                logger.error(f"HTTPError: {response.status_code} — {error_body}")
                raise ValueError(f"Request failed: {http_err} — Magento says: {error_body}")          
            
            
            try:
                result = response.json()
                logger.debug("Parsed JSON Response: %s", result)
                return result
            except json.JSONDecodeError:
                logger.warning("Response is not in JSON format. Returning raw text.")
                return response.text
            

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise ValueError(f"Request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to send request: {str(e)}")
            raise ValueError(f"Failed to send request: {str(e)}")