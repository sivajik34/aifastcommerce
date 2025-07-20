"""
Magento Multi-Agent System - Usage Examples and Configuration Templates

This file demonstrates how to use the enhanced Magento tool generator with multi-agent capabilities.
"""

import asyncio
import os
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI

# Import the main classes (assuming they're in magento_tools.py)
from magento_tools import (
    create_magento_multi_agent_system,
    get_default_agent_configs,
    MagentoSupervisorAgent,
    AgentRole
)


# === Configuration Examples ===

def get_production_config() -> Dict[str, Any]:
    """Get production-ready configuration."""
    return {
        "openapi_spec_path": "magento_openapi.json",
        "base_url": os.getenv("MAGENTO_BASE_URL", "https://your-store.com/rest/default/V1"),
        "auth_token": os.getenv("MAGENTO_AUTH_TOKEN"),
        "llm_config": {
            "model": "gpt-4",
            "temperature": 0.1,
            "max_tokens": 2000,
            "request_timeout": 60
        }
    }


def get_custom_agent_configs() -> Dict[str, Dict[str, Any]]:
    """Get customized agent configurations for specific business needs."""
    return {
        "catalog": {
            "name": "product_specialist",
            "max_iterations": 20,
            "verbose": True,
            "system_message": """
            You are a Magento Product Specialist with deep expertise in:
            - Product catalog management and optimization
            - Category hierarchy and navigation
            - Product attributes and variations
            - Inventory management and stock control
            - Price management and tier pricing
            
            Always validate product data thoroughly before making changes.
            Consider SEO implications for product updates.
            Maintain data consistency across all product variants.
            """
        },
        "customer": {
            "name": "customer_success_agent",
            "max_iterations": 15,
            "verbose": False,
            "system_message": """
            You are a Customer Success Agent focused on:
            - Customer account management and support
            - Order history and status inquiries
            - Address and profile management
            - Loyalty program management
            - Customer segmentation and targeting
            
            Always prioritize customer privacy and data protection.
            Provide empathetic and helpful responses.
            Escalate complex issues when necessary.
            """
        },
        "sales": {
            "name": "order_fulfillment_specialist",
            "max_iterations": 25,
            "verbose": True,
            "system_message": """
            You are an Order Fulfillment Specialist responsible for:
            - Order processing and lifecycle management
            - Invoice generation and management
            - Shipment tracking and delivery
            - Returns and refund processing
            - Payment processing and reconciliation
            
            Always ensure accuracy in financial transactions.
            Maintain detailed audit trails for all operations.
            Follow compliance requirements for payment processing.
            """
        },
        "marketing": {
            "name": "campaign_manager",
            "max_iterations": 12,
            "verbose": True,
            "system_message": """
            You are a Marketing Campaign Manager specializing in:
            - Promotional campaign creation and management
            - Coupon and discount rule setup
            - Customer segmentation for targeting
            - Newsletter and email marketing
            - A/B testing for promotions
            
            Always consider business impact and ROI.
            Ensure promotional rules don't conflict.
            Monitor campaign performance and effectiveness.
            """
        }
    }


# === Basic Usage Examples ===

async def basic_single_agent_example():
    """Example of using a single specialized agent."""
    
    # Create multi-agent system
    supervisor = create_magento_multi_agent_system(
        openapi_spec_path="magento_openapi.json",
        base_url="https://demo-store.com/rest/default/V1",
        auth_token="your-token-here"
    )
    
    # Use specific agent directly
    catalog_agent = supervisor.agents.get("catalog_agent")
    if catalog_agent:
        result = catalog_agent.run("Get all products with SKU starting with 'DEMO'")
        print(f"Catalog Agent Result: {result}")


async def supervisor_routing_example():
    """Example of automatic request routing by supervisor."""
    
    supervisor = create_magento_multi_agent_system(
        openapi_spec_path="magento_openapi.json",
        agent_configs=get_custom_agent_configs()
    )
    
    # Let supervisor automatically route requests
    queries = [
        "Show me all products in the electronics category",
        "Find customer information for john@example.com", 
        "Process refund for order #12345",
        "Create a 20% discount coupon for VIP customers"
    ]
    
    for query in queries:
        result = await supervisor.aexecute(query)
        print(f"Query: {query}")
        print(f"Routed to: {result['agent_used']}")
        print(f"Result: {result['result'][:200]}...")
        print("-" * 50)


async def complex_workflow_example():
    """Example of multi-step workflow execution."""
    
    supervisor = create_magento_multi_agent_system(
        openapi_spec_path="magento_openapi.json",
        agent_configs=get_custom_agent_configs()
    )
    
    # Define a complex product launch workflow
    product_launch_workflow = [
        {
            "query": "Create new category 'Summer Collection 2024'",
            "agent": "product_specialist",
            "critical": True,
            "description": "Create product category"
        },
        {
            "query": "Create product 'Summer Beach Shirt' in the new category",
            "agent": "product_specialist", 
            "critical": True,
            "description": "Create main product"
        },
        {
            "query": "Set initial inventory of 500 units for the new product",
            "agent": "inventory_manager",
            "critical": True,
            "description": "Set initial stock"
        },
        {
            "query": "Create launch promotion: 15% off for first week",
            "agent": "campaign_manager",
            "critical": False,
            "description": "Create promotional campaign"
        },
        {
            "query": "Set up email notification for stock alerts",
            "agent": "campaign_manager",
            "critical": False,
            "description": "Set up notifications"
        }
    ]
    
    print("Executing Product Launch Workflow...")
    results = supervisor.execute_workflow(product_launch_workflow)
    
    for i, step_result in enumerate(results, 1):
        task = step_result["task"]
        result = step_result["result"]
        status = "✅ SUCCESS" if result.get("success") else "❌ FAILED"
        
        print(f"Step {i}: {task['description']} - {status}")
        if not result.get("success"):
            print(f"  Error: {result.get('error')}")
        print()


# === Advanced Usage Examples ===

class MagentoWorkflowManager:
    """Advanced workflow manager for complex Magento operations."""
    
    def __init__(self, supervisor: MagentoSupervisorAgent):
        self.supervisor = supervisor
    
    async def bulk_product_import(self, product_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Import multiple products with validation and error handling."""
        results = {
            "successful": [],
            "failed": [],
            "total": len(product_data)
        }
        
        for product in product_data:
            try:
                query = f"Create product with data: {product}"
                result = await self.supervisor.aexecute(query, "product_specialist")
                
                if result.get("success"):
                    results["successful"].append({
                        "sku": product.get("sku"),
                        "result": result
                    })
                else:
                    results["failed"].append({
                        "sku": product.get("sku"),
                        "error": result.get("error")
                    })
                    
            except Exception as e:
                results["failed"].append({
                    "sku": product.get("sku"),
                    "error": str(e)
                })
        
        return results
    
    async def customer_service_ticket_resolution(self, ticket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle complex customer service scenarios."""
        
        ticket_type = ticket_data.get("type", "general")
        customer_email = ticket_data.get("customer_email")
        issue_description = ticket_data.get("description")
        
        # Multi-step resolution process
        steps = []
        
        # Step 1: Get customer information
        customer_query = f"Retrieve customer information for {customer_email}"
        customer_info = await self.supervisor.aexecute(customer_query, "customer_success_agent")
        steps.append({"step": "customer_lookup", "result": customer_info})
        
        # Step 2: Based on ticket type, route to appropriate resolution
        if ticket_type == "order_issue":
            order_query = f"Get recent orders for customer {customer_email}"
            order_info = await self.supervisor.aexecute(order_query, "order_fulfillment_specialist")
            steps.append({"step": "order_lookup", "result": order_info})
            
        elif ticket_type == "product_inquiry":
            product_query = f"Search products related to: {issue_description}"
            product_info = await self.supervisor.aexecute(product_query, "product_specialist")
            steps.append({"step": "product_search", "result": product_info})
        
        # Step 3: Generate resolution recommendations
        resolution_query = f"""
        Based on customer info and issue type '{ticket_type}', 
        provide resolution recommendations for: {issue_description}
        """
        resolution = await self.supervisor.aexecute(resolution_query)
        steps.append({"step": "resolution", "result": resolution})
        
        return {
            "ticket_id": ticket_data.get("id"),
            "resolution_steps": steps,
            "status": "processed"
        }
    
    async def inventory_rebalancing(self, low_stock_threshold: int = 10) -> Dict[str, Any]:
        """Automated inventory rebalancing across multiple sources."""
        
        # Step 1: Identify low stock items
        low_stock_query = f"Find all products with inventory below {low_stock_threshold}"
        low_stock_result = await self.supervisor.aexecute(low_stock_query, "inventory_manager")
        
        # Step 2: For each low stock item, suggest rebalancing
        rebalancing_actions = []
        
        # This would typically parse the low stock result and generate specific actions
        # For demo purposes, we'll simulate the process
        
        sample_actions = [
            "Transfer 50 units of SKU-001 from Warehouse A to Warehouse B",
            "Reorder 100 units of SKU-002 from supplier",
            "Set automatic reorder point for SKU-003 to 25 units"
        ]
        
        for action in sample_actions:
            result = await self.supervisor.aexecute(action, "inventory_manager")
            rebalancing_actions.append({
                "action": action,
                "result": result
            })
        
        return {
            "low_stock_items_found": low_stock_result,
            "rebalancing_actions": rebalancing_actions,
            "timestamp": "2024-01-20T10:30:00Z"
        }


# === Performance and Monitoring Examples ===

class MagentoAgentMonitor:
    """Monitor agent performance and usage patterns."""
    
    def __init__(self, supervisor: MagentoSupervisorAgent):
        self.supervisor = supervisor
        self.execution_stats = {
            "total_requests": 0,
            "agent_usage": {},
            "avg_response_times": {},
            "error_rates": {}
        }
    
    async def monitored_execute(self, query: str, agent_name: str = None) -> Dict[str, Any]:
        """Execute with performance monitoring."""
        import time
        
        start_time = time.time()
        
        try:
            result = await self.supervisor.aexecute(query, agent_name)
            execution_time = time.time() - start_time
            
            # Update statistics
            self.execution_stats["total_requests"] += 1
            
            used_agent = result.get("agent_used", "unknown")
            if used_agent not in self.execution_stats["agent_usage"]:
                self.execution_stats["agent_usage"][used_agent] = 0
            self.execution_stats["agent_usage"][used_agent] += 1
            
            if used_agent not in self.execution_stats["avg_response_times"]:
                self.execution_stats["avg_response_times"][used_agent] = []
            self.execution_stats["avg_response_times"][used_agent].append(execution_time)
            
            return {
                **result,
                "execution_time": execution_time,
                "monitoring_stats": self.get_current_stats()
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time
            }
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        avg_times = {}
        for agent, times in self.execution_stats["avg_response_times"].items():
            avg_times[agent] = sum(times) / len(times) if times else 0
        
        return {
            "total_requests": self.execution_stats["total_requests"],
            "agent_usage_distribution": self.execution_stats["agent_usage"],
            "average_response_times": avg_times
        }


# === Main Demo Function ===

async def comprehensive_demo():
    """Comprehensive demonstration of the multi-agent system."""
    
    print("🚀 Starting Magento Multi-Agent System Demo")
    print("=" * 60)
    
    # Initialize system with custom configuration
    supervisor = create_magento_multi_agent_system(
        openapi_spec_path="magento_openapi.json",
        base_url="https://demo-magento.com/rest/default/V1",
        auth_token="demo-token",
        agent_configs=get_custom_agent_configs()
    )
    
    print(f"✅ Created system with {len(supervisor.agents)} specialized agents:")
    for name, agent in supervisor.agents.items():
        print(f"  - {name} ({agent.role.value}): {len(agent.tools)} tools")
    
    print("\n" + "=" * 60)
    print("🎯 Demo 1: Automatic Request Routing")
    print("=" * 60)
    
    demo_queries = [
        "What products do we have in the electronics category?",
        "Find the customer account for sarah@example.com",
        "Process a refund for order number ORD-2024-001",
        "Create a flash sale with 25% off all summer items"
    ]
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\nQuery {i}: {query}")
        # result = await supervisor.aexecute(query)  # Commented for demo
        # print(f"→ Routed to: {result.get('agent_used')}")
        print(f"→ Would route to: {supervisor.route_request(query)} agent")
    
    print("\n" + "=" * 60)
    print("⚙️ Demo 2: Workflow Execution")
    print("=" * 60)
    
    # Create workflow manager
    workflow_manager = MagentoWorkflowManager(supervisor)
    
    print("Simulating customer service ticket resolution...")
    ticket = {
        "id": "TICKET-001",
        "type": "order_issue",
        "customer_email": "customer@example.com",
        "description": "Product arrived damaged, need replacement"
    }
    # result = await workflow_manager.customer_service_ticket_resolution(ticket)
    print("✅ Would process multi-step customer service resolution")
    
    print("\n" + "=" * 60)
    print("📊 Demo 3: Performance Monitoring")
    print("=" * 60)
    
    monitor = MagentoAgentMonitor(supervisor)
    print("✅ Performance monitoring initialized")
    print("Would track: execution times, agent usage, error rates")
    
    print("\n🎉 Demo completed successfully!")


# === Quick Start Templates ===

def quick_start_basic():
    """Quick start with basic configuration."""
    return create_magento_multi_agent_system(
        openapi_spec_path="magento_openapi.json",
        base_url="https://your-store.com/rest/default/V1",
        auth_token="your-token"
    )


def quick_start_production():
    """Quick start with production configuration."""
    config = get_production_config()
    
    llm = ChatOpenAI(
        model=config["llm_config"]["model"],
        temperature=config["llm_config"]["temperature"],
        max_tokens=config["llm_config"]["max_tokens"],
        request_timeout=config["llm_config"]["request_timeout"]
    )
    
    return create_magento_multi_agent_system(
        openapi_spec_path=config["openapi_spec_path"],
        base_url=config["base_url"],
        auth_token=config["auth_token"],
        llm=llm,
        agent_configs=get_custom_agent_configs()
    )


# === Main Execution ===

if __name__ == "__main__":
    # Run the comprehensive demo
    asyncio.run(comprehensive_demo())
    
    # Examples of quick start functions
    print("\n" + "=" * 60)
    print("📋 Quick Start Examples:")
    print("=" * 60)
    
    print("""
# Basic setup
supervisor = quick_start_basic()

# Production setup  
supervisor = quick_start_production()

# Custom setup
supervisor = create_magento_multi_agent_system(
    openapi_spec_path="your_spec.json",
    base_url="https://your-store.com/rest/default/V1", 
    auth_token="your-token",
    agent_configs=get_custom_agent_configs()
)

# Execute queries
result = supervisor.execute("List all products")
async_result = await supervisor.aexecute("Get customer orders")

# Execute workflows
workflow_results = supervisor.execute_workflow(your_workflow_tasks)
    """)
    
# Create specialized agents automatically
agents = generator.create_specialized_agents(llm=llm)

# Create supervisor to coordinate them
supervisor = generator.create_supervisor(agents, llm)

# Or create everything at once
supervisor = create_magento_multi_agent_system(
    openapi_spec_path="magento_openapi.json",
    base_url="https://your-store.com/rest/default/V1",
    auth_token="your-token"
)





# Simple execution with auto-routing
result = supervisor.execute("Get all products in electronics category")

# Specific agent execution
result = supervisor.execute("Create new customer account", "customer_service")





# Customer service ticket resolution
workflow_manager = MagentoWorkflowManager(supervisor)
resolution = await workflow_manager.customer_service_ticket_resolution(ticket_data)

# Bulk product import with validation
results = await workflow_manager.bulk_product_import(product_list)





monitor = MagentoAgentMonitor(supervisor)
result = await monitor.monitored_execute("Process order #12345")
stats = monitor.get_current_stats()    
    
