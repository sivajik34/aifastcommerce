import json
import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urljoin
from enum import Enum

import requests
from langchain.tools import tool
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.schema import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, create_model, Field, ValidationError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentRole(Enum):
    """Predefined agent roles for Magento operations."""
    CATALOG_MANAGER = "catalog"
    CUSTOMER_SERVICE = "customer" 
    ORDER_MANAGER = "sales"
    INVENTORY_MANAGER = "inventory"
    CMS_MANAGER = "cms"
    MARKETING_MANAGER = "marketing"
    ADMIN_MANAGER = "admin"
    STORE_MANAGER = "store"
    TAX_MANAGER = "tax"
    SHIPPING_MANAGER = "shipping"


class MagentoAgent:
    """Represents a specialized Magento agent with specific tools and capabilities."""
    
    def __init__(
        self,
        role: AgentRole,
        name: str,
        tools: List[Callable],
        llm: ChatOpenAI,
        system_message: str = "",
        max_iterations: int = 10,
        verbose: bool = False
    ):
        self.role = role
        self.name = name
        self.tools = tools
        self.llm = llm
        self.max_iterations = max_iterations
        self.verbose = verbose
        
        # Create agent prompt
        self.prompt = self._create_agent_prompt(system_message)
        
        # Create agent executor
        self.agent = create_openai_functions_agent(llm, tools, self.prompt)
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=tools,
            verbose=verbose,
            max_iterations=max_iterations,
            handle_parsing_errors=True
        )
    
    def _create_agent_prompt(self, custom_system_message: str = "") -> ChatPromptTemplate:
        """Create a specialized prompt template for the agent."""
        
        default_messages = {
            AgentRole.CATALOG_MANAGER: (
                "You are a Magento Catalog Manager agent specialized in product management. "
                "You can create, update, retrieve, and manage products, categories, attributes, "
                "and inventory. Always validate product data before making changes."
            ),
            AgentRole.CUSTOMER_SERVICE: (
                "You are a Magento Customer Service agent specialized in customer management. "
                "You can handle customer accounts, addresses, orders, returns, and support tickets. "
                "Always prioritize customer satisfaction and data privacy."
            ),
            AgentRole.ORDER_MANAGER: (
                "You are a Magento Order Manager agent specialized in sales operations. "
                "You can process orders, manage invoices, shipments, credit memos, and payments. "
                "Always ensure order accuracy and compliance with business rules."
            ),
            AgentRole.INVENTORY_MANAGER: (
                "You are a Magento Inventory Manager agent specialized in stock management. "
                "You can manage inventory levels, stock sources, reservations, and stock movements. "
                "Always maintain accurate inventory data."
            ),
            AgentRole.CMS_MANAGER: (
                "You are a Magento CMS Manager agent specialized in content management. "
                "You can manage pages, blocks, widgets, and media content. "
                "Always ensure content quality and SEO optimization."
            ),
            AgentRole.MARKETING_MANAGER: (
                "You are a Magento Marketing Manager agent specialized in promotional activities. "
                "You can manage coupons, price rules, newsletters, and promotional campaigns. "
                "Always consider business impact and customer engagement."
            )
        }
        
        system_message = custom_system_message or default_messages.get(
            self.role, 
            f"You are a Magento {self.role.value} agent specialized in {self.role.value} operations."
        )
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
    
    async def arun(self, query: str, **kwargs) -> str:
        """Execute agent asynchronously."""
        return await self.executor.arun(input=query, **kwargs)
    
    def run(self, query: str, **kwargs) -> str:
        """Execute agent synchronously."""
        return self.executor.run(input=query, **kwargs)
    
    def get_tool_names(self) -> List[str]:
        """Get list of tool names assigned to this agent."""
        return [tool.name for tool in self.tools]


class MagentoSupervisorAgent:
    """Supervisor agent that coordinates multiple specialized Magento agents."""
    
    def __init__(
        self,
        agents: Dict[str, MagentoAgent],
        llm: ChatOpenAI,
        default_agent: str = None,
        verbose: bool = False
    ):
        self.agents = agents
        self.llm = llm
        self.default_agent = default_agent
        self.verbose = verbose
        
        # Create supervisor prompt
        self.prompt = self._create_supervisor_prompt()
    
    def _create_supervisor_prompt(self) -> ChatPromptTemplate:
        """Create prompt template for the supervisor agent."""
        
        agent_descriptions = []
        for name, agent in self.agents.items():
            tools_list = ", ".join(agent.get_tool_names())
            agent_descriptions.append(f"- {name} ({agent.role.value}): {tools_list}")
        
        agents_info = "\n".join(agent_descriptions)
        
        system_message = f"""You are a Magento Supervisor Agent that coordinates multiple specialized agents.

Available agents:
{agents_info}

Your responsibilities:
1. Analyze user requests to determine which agent(s) should handle the task
2. Route requests to the appropriate specialized agent
3. Coordinate multi-agent workflows when needed
4. Provide summaries and consolidate results from multiple agents

Guidelines:
- For product-related tasks, use the catalog agent
- For customer issues, use the customer service agent  
- For order processing, use the order manager agent
- For inventory updates, use the inventory manager agent
- For content updates, use the CMS manager agent
- For promotions and marketing, use the marketing manager agent

Always explain your routing decision and provide clear, actionable results."""

        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("user", "{input}"),
        ])
    
    def route_request(self, query: str) -> str:
        """Determine which agent should handle the request."""
        routing_keywords = {
            "catalog": ["product", "category", "attribute", "sku", "catalog", "price"],
            "customer": ["customer", "account", "profile", "address", "login"],
            "sales": ["order", "invoice", "shipment", "payment", "refund", "credit memo"],
            "inventory": ["stock", "inventory", "quantity", "reservation"],
            "cms": ["page", "block", "content", "media", "widget"],
            "marketing": ["coupon", "promotion", "newsletter", "campaign", "discount"],
            "admin": ["user", "role", "permission", "configuration"],
            "store": ["store", "website", "scope", "configuration"],
            "tax": ["tax", "rate", "rule", "class"],
            "shipping": ["shipping", "carrier", "delivery", "tracking"]
        }
        
        query_lower = query.lower()
        scores = {}
        
        for agent_type, keywords in routing_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                scores[agent_type] = score
        
        if scores:
            best_match = max(scores, key=scores.get)
            # Find agent with matching role
            for name, agent in self.agents.items():
                if agent.role.value == best_match:
                    return name
        
        return self.default_agent or list(self.agents.keys())[0]
    
    def execute(self, query: str, agent_name: str = None) -> Dict[str, Any]:
        """Execute request using specified agent or auto-route."""
        if not agent_name:
            agent_name = self.route_request(query)
        
        if agent_name not in self.agents:
            return {"error": f"Agent '{agent_name}' not found", "available_agents": list(self.agents.keys())}
        
        try:
            result = self.agents[agent_name].run(query)
            return {
                "agent_used": agent_name,
                "agent_role": self.agents[agent_name].role.value,
                "result": result,
                "success": True
            }
        except Exception as e:
            logger.error(f"Error executing request with agent {agent_name}: {e}")
            return {
                "agent_used": agent_name,
                "error": str(e),
                "success": False
            }
    
    async def aexecute(self, query: str, agent_name: str = None) -> Dict[str, Any]:
        """Execute request asynchronously."""
        if not agent_name:
            agent_name = self.route_request(query)
        
        if agent_name not in self.agents:
            return {"error": f"Agent '{agent_name}' not found", "available_agents": list(self.agents.keys())}
        
        try:
            result = await self.agents[agent_name].arun(query)
            return {
                "agent_used": agent_name,
                "agent_role": self.agents[agent_name].role.value,
                "result": result,
                "success": True
            }
        except Exception as e:
            logger.error(f"Error executing request with agent {agent_name}: {e}")
            return {
                "agent_used": agent_name,
                "error": str(e),
                "success": False
            }
    
    def execute_workflow(self, tasks: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Execute a multi-step workflow across multiple agents."""
        results = []
        
        for task in tasks:
            query = task.get("query", "")
            agent_name = task.get("agent")
            
            result = self.execute(query, agent_name)
            results.append({
                "task": task,
                "result": result
            })
            
            # Stop workflow if any task fails and it's marked as critical
            if not result.get("success") and task.get("critical", False):
                logger.error(f"Critical task failed, stopping workflow: {result}")
                break
        
        return results


class MagentoToolGenerator:
    """Enhanced Magento 2 REST API tool generator with improved error handling and configuration."""
    
    def __init__(
        self, 
        openapi_spec_path: str = "magento_openapi.json",
        base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.openapi_spec_path = openapi_spec_path
        self.base_url = base_url or "https://your-magento-instance.com/rest/default/V1"
        self.auth_token = auth_token
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize requests session with retry strategy
        self.session = self._create_session()
        
        # Load OpenAPI spec
        self.openapi_spec = self._load_openapi_spec()
        self.paths = self.openapi_spec.get("paths", {})
        
        # Tool storage
        self.tools: List[Callable] = []
        self.tools_by_name: Dict[str, Callable] = {}
        self.tools_by_tag: Dict[str, List[Callable]] = {}
        self.tools_by_method: Dict[str, List[Callable]] = {}
        
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy and authentication."""
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
        
        # Add authentication if provided
        if self.auth_token:
            session.headers['Authorization'] = f'Bearer {self.auth_token}'
            
        return session
    
    def _load_openapi_spec(self) -> Dict[str, Any]:
        """Load and validate OpenAPI specification."""
        try:
            with open(self.openapi_spec_path, 'r', encoding='utf-8') as f:
                spec = json.load(f)
            logger.info(f"Loaded OpenAPI spec from {self.openapi_spec_path}")
            return spec
        except FileNotFoundError:
            logger.error(f"OpenAPI spec file not found: {self.openapi_spec_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in OpenAPI spec: {e}")
            raise
    
    def _extract_operation_info(self, method_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant operation information from OpenAPI spec."""
        return {
            "summary": method_data.get("summary", ""),
            "description": method_data.get("description", ""),
            "parameters": method_data.get("parameters", []),
            "requestBody": method_data.get("requestBody", {}),
            "tags": method_data.get("tags", ["default"]),
            "operationId": method_data.get("operationId", ""),
            "responses": method_data.get("responses", {}),
            "security": method_data.get("security", []),
        }
    
    def _get_python_type(self, schema: Dict[str, Any]) -> type:
        """Convert OpenAPI schema type to Python type."""
        schema_type = schema.get("type", "string")
        schema_format = schema.get("format", "")
        
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        
        # Handle specific formats
        if schema_type == "string":
            if schema_format in ["date", "date-time"]:
                return str  # Could use datetime, but str is more flexible for API calls
            elif schema_format == "email":
                return str
                
        return type_mapping.get(schema_type, str)
    
    def _generate_args_schema(self, name: str, parameters: List[Dict[str, Any]]) -> BaseModel:
        """Generate Pydantic model for tool arguments."""
        fields = {}
        
        for param in parameters:
            param_name = param["name"]
            is_required = param.get("required", False)
            param_schema = param.get("schema", {})
            
            # Get Python type
            field_type = self._get_python_type(param_schema)
            
            # Handle optional fields
            if not is_required:
                field_type = Optional[field_type]
            
            # Create field with description and constraints
            field_kwargs = {}
            if "description" in param:
                field_kwargs["description"] = param["description"]
            if "example" in param_schema:
                field_kwargs["example"] = param_schema["example"]
            if "enum" in param_schema:
                field_kwargs["enum"] = param_schema["enum"]
                
            # Set default value for optional parameters
            default_value = ... if is_required else None
            if "default" in param_schema:
                default_value = param_schema["default"]
                
            fields[param_name] = (
                field_type, 
                Field(default=default_value, **field_kwargs)
            )
        
        return create_model(f"{name}Args", **fields)
    
    def _sanitize_function_name(self, method: str, path: str, operation_id: str = "") -> str:
        """Generate a clean function name from method, path, and operation ID."""
        if operation_id:
            # Prefer operationId if available
            func_name = re.sub(r'[^a-zA-Z0-9_]', '_', operation_id)
        else:
            # Generate from method and path
            path_clean = re.sub(r'[{}]', '', path)  # Remove path parameters
            func_name = f"{method.lower()}_{path_clean.strip('/').replace('/', '_')}"
            func_name = re.sub(r'[^a-zA-Z0-9_]', '_', func_name)
        
        # Ensure it starts with a letter or underscore
        if func_name and func_name[0].isdigit():
            func_name = f"api_{func_name}"
            
        return func_name.lower()
    
    def _extract_request_body_params(self, request_body: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract parameters from request body schema."""
        params = []
        content = request_body.get("content", {})
        
        # Support both application/json and application/x-www-form-urlencoded
        for content_type in ["application/json", "application/x-www-form-urlencoded"]:
            if content_type in content:
                schema = content[content_type].get("schema", {})
                if "properties" in schema:
                    required_fields = schema.get("required", [])
                    for name, prop_schema in schema["properties"].items():
                        params.append({
                            "name": name,
                            "required": name in required_fields,
                            "schema": prop_schema,
                            "description": prop_schema.get("description", ""),
                            "in": "body"
                        })
                break
        
        return params
    
    def _make_api_call(self, method: str, path: str, **kwargs) -> Union[Dict[str, Any], str]:
        """Make the actual API call to Magento."""
        try:
            # Replace path parameters
            url = path
            path_params = re.findall(r"\{([^}]+)\}", url)
            for param in path_params:
                if param in kwargs:
                    url = url.replace(f"{{{param}}}", str(kwargs.pop(param)))
                else:
                    logger.warning(f"Missing required path parameter: {param}")
            
            # Build full URL
            full_url = urljoin(self.base_url.rstrip('/') + '/', url.lstrip('/'))
            
            # Separate query params and body params
            query_params = {}
            body_data = {}
            
            for key, value in kwargs.items():
                if method.upper() in ["GET", "DELETE"] or key in ["limit", "offset", "page"]:
                    query_params[key] = value
                else:
                    body_data[key] = value
            
            # Make request
            if method.upper() in ["GET", "DELETE"]:
                response = self.session.request(
                    method, full_url, 
                    params=query_params, 
                    timeout=self.timeout
                )
            else:
                response = self.session.request(
                    method, full_url, 
                    params=query_params,
                    json=body_data if body_data else None,
                    timeout=self.timeout
                )
            
            # Handle response
            response.raise_for_status()
            
            try:
                return response.json()
            except ValueError:
                # Response is not JSON
                return response.text
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API call failed: {e}")
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}
        except Exception as e:
            logger.error(f"Unexpected error during API call: {e}")
            return {"error": f"Unexpected error: {str(e)}"}
    
    def _generate_tool(self, method: str, path: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a single tool from OpenAPI specification."""
        op_info = self._extract_operation_info(spec)
        func_name = self._sanitize_function_name(method, path, op_info["operationId"])
        tag = op_info["tags"][0].lower() if op_info["tags"] else "default"
        
        # Combine parameters from URL params and request body
        all_params = op_info["parameters"].copy()
        
        # Add request body parameters for POST/PUT/PATCH methods
        if method.upper() in ["POST", "PUT", "PATCH"] and op_info["requestBody"]:
            body_params = self._extract_request_body_params(op_info["requestBody"])
            all_params.extend(body_params)
        
        # Generate schema
        args_schema = self._generate_args_schema(func_name.title(), all_params)
        
        # Create the tool function
        def create_tool_function(method: str, path: str) -> Callable:
            def tool_function(**kwargs) -> Union[Dict[str, Any], str]:
                """Dynamically generated tool function for Magento API."""
                return self._make_api_call(method, path, **kwargs)
            
            # Set function metadata
            tool_function.__name__ = func_name
            doc_parts = []
            if op_info["summary"]:
                doc_parts.append(op_info["summary"])
            if op_info["description"]:
                doc_parts.append(op_info["description"])
            if all_params:
                doc_parts.append(f"\nParameters: {', '.join([p['name'] for p in all_params])}")
            
            tool_function.__doc__ = "\n\n".join(doc_parts) if doc_parts else f"Magento API: {method.upper()} {path}"
            
            return tool_function
        
        # Create and wrap the tool
        tool_func = create_tool_function(method, path)
        wrapped_tool = tool(args_schema=args_schema)(tool_func)
        
        return {
            "name": func_name,
            "tool": wrapped_tool,
            "tag": tag,
            "method": method.upper(),
            "path": path,
            "operation_id": op_info["operationId"],
        }
    
    def generate_all_tools(self) -> None:
        """Generate all tools from the OpenAPI specification."""
        logger.info("Generating tools from OpenAPI specification...")
        
        for path, methods in self.paths.items():
            for method, spec in methods.items():
                try:
                    tool_info = self._generate_tool(method, path, spec)
                    
                    # Store the tool in various collections
                    self.tools.append(tool_info["tool"])
                    self.tools_by_name[tool_info["name"]] = tool_info["tool"]
                    
                    # Group by tag
                    if tool_info["tag"] not in self.tools_by_tag:
                        self.tools_by_tag[tool_info["tag"]] = []
                    self.tools_by_tag[tool_info["tag"]].append(tool_info["tool"])
                    
                    # Group by HTTP method
                    if tool_info["method"] not in self.tools_by_method:
                        self.tools_by_method[tool_info["method"]] = []
                    self.tools_by_method[tool_info["method"]].append(tool_info["tool"])
                    
                    logger.debug(f"Generated tool: {tool_info['name']} ({method.upper()} {path})")
                    
                except Exception as e:
                    logger.error(f"Failed to generate tool for {method.upper()} {path}: {e}")
                    continue
        
        logger.info(f"Generated {len(self.tools)} tools across {len(self.tools_by_tag)} categories")
    
    def get_tools_by_category(self, category: str) -> List[Callable]:
        """Get tools filtered by category/tag."""
        return self.tools_by_tag.get(category, [])
    
    def get_tools_by_method(self, method: str) -> List[Callable]:
        """Get tools filtered by HTTP method."""
        return self.tools_by_method.get(method.upper(), [])
    
    def list_available_tools(self) -> Dict[str, List[str]]:
        """List all available tools organized by category."""
        return {
            tag: [tool.name for tool in tools] 
            for tag, tools in self.tools_by_tag.items()
        }
    
    def create_specialized_agents(
        self,
        llm: ChatOpenAI,
        agent_configs: Optional[Dict[str, Dict[str, Any]]] = None,
        create_all: bool = True
    ) -> Dict[str, MagentoAgent]:
        """Create specialized agents with assigned tools."""
        if not self.tools:
            self.generate_all_tools()
        
        agents = {}
        default_configs = agent_configs or {}
        
        # Define which tool categories map to which agent roles
        role_tool_mapping = {
            AgentRole.CATALOG_MANAGER: ["catalog", "product", "category", "configurable"],
            AgentRole.CUSTOMER_SERVICE: ["customer", "customergroup"],
            AgentRole.ORDER_MANAGER: ["sales", "order", "invoice", "shipment", "creditmemo"],
            AgentRole.INVENTORY_MANAGER: ["inventory", "stock", "source"],
            AgentRole.CMS_MANAGER: ["cms", "content", "media"],
            AgentRole.MARKETING_MANAGER: ["marketing", "coupon", "salesrule", "newsletter"],
            AgentRole.ADMIN_MANAGER: ["admin", "user", "role", "integration"],
            AgentRole.STORE_MANAGER: ["store", "website", "config"],
            AgentRole.TAX_MANAGER: ["tax", "taxrate", "taxrule"],
            AgentRole.SHIPPING_MANAGER: ["shipping", "carrier", "delivery"]
        }
        
        for role, tool_categories in role_tool_mapping.items():
            if not create_all and role.value not in default_configs:
                continue
                
            # Get tools for this role
            role_tools = []
            for category in tool_categories:
                role_tools.extend(self.tools_by_tag.get(category, []))
            
            # If no specific tools found, get tools by method (for generic operations)
            if not role_tools:
                role_tools = self.tools_by_method.get("GET", [])[:5]  # Limit to 5 tools
            
            if role_tools:
                config = default_configs.get(role.value, {})
                agent_name = config.get("name", f"{role.value}_agent")
                
                agent = MagentoAgent(
                    role=role,
                    name=agent_name,
                    tools=role_tools,
                    llm=llm,
                    system_message=config.get("system_message", ""),
                    max_iterations=config.get("max_iterations", 10),
                    verbose=config.get("verbose", False)
                )
                
                agents[agent_name] = agent
                logger.info(f"Created {role.value} agent with {len(role_tools)} tools")
        
        return agents
    
    def create_supervisor(
        self,
        agents: Dict[str, MagentoAgent],
        llm: ChatOpenAI,
        default_agent: str = None,
        verbose: bool = False
    ) -> MagentoSupervisorAgent:
        """Create a supervisor agent to coordinate specialized agents."""
        return MagentoSupervisorAgent(
            agents=agents,
            llm=llm,
            default_agent=default_agent,
            verbose=verbose
        )
    
    def create_multi_agent_system(
        self,
        llm: ChatOpenAI,
        agent_configs: Optional[Dict[str, Dict[str, Any]]] = None,
        supervisor_config: Optional[Dict[str, Any]] = None
    ) -> MagentoSupervisorAgent:
        """Create a complete multi-agent system with supervisor."""
        # Create specialized agents
        agents = self.create_specialized_agents(llm, agent_configs)
        
        if not agents:
            raise ValueError("No agents were created. Check your tool generation and agent configuration.")
        
        # Create supervisor
        supervisor_config = supervisor_config or {}
        supervisor = self.create_supervisor(
            agents=agents,
            llm=llm,
            default_agent=supervisor_config.get("default_agent"),
            verbose=supervisor_config.get("verbose", False)
        )
        
        logger.info(f"Created multi-agent system with {len(agents)} specialized agents")
        return supervisor


    def update_authentication(self, auth_token: str) -> None:
        """Update authentication token."""
        self.auth_token = auth_token
        self.session.headers['Authorization'] = f'Bearer {auth_token}'
        logger.info("Authentication token updated")


# === Factory Functions ===
def create_magento_multi_agent_system(
    openapi_spec_path: str = "magento_openapi.json",
    base_url: Optional[str] = None,
    auth_token: Optional[str] = None,
    llm: Optional[ChatOpenAI] = None,
    agent_configs: Optional[Dict[str, Dict[str, Any]]] = None,
    supervisor_config: Optional[Dict[str, Any]] = None
) -> MagentoSupervisorAgent:
    """
    Factory function to create a complete Magento multi-agent system.
    
    Args:
        openapi_spec_path: Path to the Magento OpenAPI specification file
        base_url: Base URL for the Magento instance
        auth_token: Authentication token for API access
        llm: Language model instance (creates default if not provided)
        agent_configs: Configuration for individual agents
        supervisor_config: Configuration for the supervisor agent
        
    Returns:
        MagentoSupervisorAgent instance coordinating all specialized agents
    """
    # Create default LLM if not provided
    if llm is None:
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.1,
            max_tokens=1000
        )
    
    # Create tool generator
    generator = MagentoToolGenerator(
        openapi_spec_path=openapi_spec_path,
        base_url=base_url,
        auth_token=auth_token
    )
    
    # Create multi-agent system
    supervisor = generator.create_multi_agent_system(
        llm=llm,
        agent_configs=agent_configs,
        supervisor_config=supervisor_config
    )
    
    return supervisor


# === Usage Examples and Templates ===
def get_default_agent_configs() -> Dict[str, Dict[str, Any]]:
    """Get default configuration templates for agents."""
    return {
        "catalog": {
            "name": "catalog_manager",
            "max_iterations": 15,
            "verbose": True,
            "system_message": (
                "You are a Magento Catalog Manager. You excel at managing products, "
                "categories, attributes, and inventory. Always validate data before "
                "making changes and provide detailed feedback on operations."
            )
        },
        "customer": {
            "name": "customer_service",
            "max_iterations": 12,
            "verbose": False,
            "system_message": (
                "You are a Magento Customer Service Agent. You handle customer "
                "accounts, orders, and support with empathy and efficiency. "
                "Always prioritize customer satisfaction and data privacy."
            )
        },
        "sales": {
            "name": "order_manager",
            "max_iterations": 15,
            "verbose": True,
            "system_message": (
                "You are a Magento Order Manager. You process orders, invoices, "
                "shipments, and payments with precision. Always verify order "
                "details and maintain accurate records."
            )
        },
        "inventory": {
            "name": "inventory_manager",
            "max_iterations": 10,
            "verbose": False,
            "system_message": (
                "You are a Magento Inventory Manager. You maintain accurate stock "
                "levels and manage inventory across multiple sources. Always "
                "ensure data consistency and prevent overselling."
            )
        }
    }


# === Example Usage Script ===
async def example_usage():
    """Example of how to use the multi-agent system."""
    
    # Configuration
    agent_configs = get_default_agent_configs()
    supervisor_config = {
        "default_agent": "catalog_manager",
        "verbose": True
    }
    
    # Create multi-agent system
    supervisor = create_magento_multi_agent_system(
        openapi_spec_path="magento_openapi.json",
        base_url="https://your-magento-store.com/rest/default/V1",
        auth_token="your-auth-token",
        agent_configs=agent_configs,
        supervisor_config=supervisor_config
    )
    
    # Single agent execution
    result = supervisor.execute("Get all products in category 5")
    print(f"Result: {result}")
    
    # Multi-step workflow
    workflow_tasks = [
        {
            "query": "Create a new product with SKU 'TEST-001'",
            "agent": "catalog_manager",
            "critical": True
        },
        {
            "query": "Set inventory for SKU 'TEST-001' to 100 units",
            "agent": "inventory_manager",
            "critical": True
        },
        {
            "query": "Create a 10% discount coupon for the new product",
            "agent": "marketing_manager",
            "critical": False
        }
    ]
    
    workflow_results = supervisor.execute_workflow(workflow_tasks)
    print(f"Workflow results: {workflow_results}")
    
    # Async execution
    async_result = await supervisor.aexecute("Get customer by email john@example.com")
    print(f"Async result: {async_result}")


# === Main Factory Function (Backward Compatibility) ===
def create_magento_tools(
    openapi_spec_path: str = "magento_openapi.json",
    base_url: Optional[str] = None,
    auth_token: Optional[str] = None
) -> MagentoToolGenerator:
    """
    Factory function to create and initialize Magento tools.
    
    Args:
        openapi_spec_path: Path to the Magento OpenAPI specification file
        base_url: Base URL for the Magento instance (e.g., 'https://your-store.com/rest/default/V1')
        auth_token: Authentication token for API access
        
    Returns:
        MagentoToolGenerator instance with all tools generated
    """
    generator = MagentoToolGenerator(
        openapi_spec_path=openapi_spec_path,
        base_url=base_url,
        auth_token=auth_token
    )
    generator.generate_all_tools()
    return generator


# === Export the main interface ===
__all__ = [
    "MagentoToolGenerator", 
    "MagentoAgent",
    "MagentoSupervisorAgent", 
    "AgentRole",
    "create_magento_tools",
    "create_magento_multi_agent_system",
    "get_default_agent_configs"
]
if __name__ == "__main__":
    import asyncio
    
    # Example usage - Traditional tool generation
    try:
        magento_tools = create_magento_tools(
            openapi_spec_path="magento_openapi.json",
            base_url="https://your-magento-instance.com/rest/default/V1",
            auth_token="your-auth-token-here"
        )
        
        print(f"Generated {len(magento_tools.tools)} tools")
        print("Available categories:", list(magento_tools.tools_by_tag.keys()))
        
    except Exception as e:
        logger.error(f"Failed to initialize Magento tools: {e}")
    
    # Example usage - Multi-agent system
    try:
        supervisor = create_magento_multi_agent_system(
            openapi_spec_path="magento_openapi.json",
            base_url="https://your-magento-instance.com/rest/default/V1",
            auth_token="your-auth-token-here",
            agent_configs=get_default_agent_configs()
        )
        
        print(f"Created multi-agent system with agents: {list(supervisor.agents.keys())}")
        
        # Test single execution
        # result = supervisor.execute("List all active products")
        # print(f"Execution result: {result}")
        
        # Test async execution (commented out - requires proper async context)
        # asyncio.run(example_usage())
        
    except Exception as e:
        logger.error(f"Failed to create multi-agent system: {e}")
