from pathlib import Path
import importlib
from langchain_core.tools import BaseTool

tools = []

tool_dir = Path(__file__).parent
for file in tool_dir.glob("*.py"):
    if file.stem == "__init__":
        continue
    module = importlib.import_module(f"{__name__}.{file.stem}")
    mod_tools = getattr(module, "tools", [])
    tools.extend(mod_tools)

tools_by_name = {tool.name: tool for tool in tools if isinstance(tool, BaseTool)}
