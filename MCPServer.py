"""
aiNOC MCP Server — tool registration entry point.

This module is intentionally thin. All business logic lives in:
  transport/   — vendor-specific network transports (SSH, RESTCONF)
  tools/       — MCP tool handler functions
  core/inventory.py    — device inventory (NETWORK.json)
  core/settings.py     — credentials and transport configuration
"""
import logging
from contextlib import asynccontextmanager
from fastmcp import FastMCP

from core.logging_config import setup_logging
from transport.pool import close_sessions

setup_logging()
log = logging.getLogger("ainoc")

from tools.protocol    import get_ospf, get_bgp
from tools.routing     import get_routing, get_routing_policies
from tools.operational import get_interfaces, ping, traceroute, run_show
from tools.state       import get_intent, check_maintenance_window, assess_risk
from tools.config      import push_config
from tools.jira_tools  import jira_add_comment, jira_resolve_issue


@asynccontextmanager
async def _lifespan(app):
    """Clean up transport resources on MCP server shutdown."""
    yield
    await close_sessions()


mcp = FastMCP("mcp_automation", lifespan=_lifespan)

mcp.tool(name="get_ospf")(get_ospf)
mcp.tool(name="get_bgp")(get_bgp)
mcp.tool(name="get_routing")(get_routing)
mcp.tool(name="get_routing_policies")(get_routing_policies)
mcp.tool(name="get_interfaces")(get_interfaces)
mcp.tool(name="ping")(ping)
mcp.tool(name="traceroute")(traceroute)
mcp.tool(name="run_show")(run_show)
mcp.tool(name="get_intent")(get_intent)
mcp.tool(name="check_maintenance_window")(check_maintenance_window)
mcp.tool(name="assess_risk")(assess_risk)
mcp.tool(name="push_config")(push_config)
mcp.tool(name="jira_add_comment")(jira_add_comment)
mcp.tool(name="jira_resolve_issue")(jira_resolve_issue)

log.info("aiNOC MCP Server started — 14 tools registered")

if __name__ == "__main__":
    mcp.run()
