from typing import Callable, List
from agents.customer.agent import get_customer_agent
from agents.order.agent import get_order_agent
from agents.product.agent import get_product_agent
from agents.stock.agent import get_stock_agent
from agents.category.agent import get_category_agent
from agents.invoice.agent import get_invoice_agent
from agents.shipment.agent import get_shipment_agent
from agents.directory.agent import get_directory_agent

from supervisors.catalog_supervisor import get_catalog_supervisor
from supervisors.customer_supervisor import get_customer_supervisor
from supervisors.sales_supervisor import get_sales_supervisor
from supervisors.directory_supervisor import get_directory_supervisor

class TeamConfig:
    def __init__(self, name: str, agent_loaders: List[Callable], team_loader: Callable):
        self.name = name
        self.agent_loaders = agent_loaders
        self.team_loader = team_loader

    def load_team(self, llm):
        agents = [loader(llm) for loader in self.agent_loaders]
        return self.team_loader(llm, agents=agents)

TEAM_REGISTRY = [
    TeamConfig("sales_supervisor", [get_order_agent, get_shipment_agent, get_invoice_agent], get_sales_supervisor),
    TeamConfig("catalog_team", [get_product_agent, get_category_agent, get_stock_agent], get_catalog_supervisor),
    TeamConfig("customer_supervisor", [get_customer_agent], get_customer_supervisor),
    TeamConfig("directory_supervisor", [get_directory_agent], get_directory_supervisor),
]
