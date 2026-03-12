"""
aiNOC MCP Server — tool registration entry point.

This module is intentionally thin. All business logic lives in:
  transport/   — vendor-specific network transports (SSH, RESTCONF)
  tools/       — MCP tool handler functions
  core/inventory.py    — device inventory (NETWORK.json)
  core/settings.py     — credentials and transport configuration
"""
import logging
from fastmcp import FastMCP

from core.logging_config import setup_logging

setup_logging()
log = logging.getLogger("ainoc")

from tools.protocol    import get_ospf, get_bgp
from tools.routing     import get_routing, get_routing_policies
from tools.operational import get_interfaces, ping, traceroute, run_show
from tools.state       import get_intent, assess_risk
from tools.config      import push_config
from tools.jira_tools  import jira_add_comment, jira_resolve_issue
from tools.approval    import request_approval, post_approval_outcome


mcp = FastMCP("mcp_automation")

mcp.tool(name="get_ospf")(get_ospf)
mcp.tool(name="get_bgp")(get_bgp)
mcp.tool(name="get_routing")(get_routing)
mcp.tool(name="get_routing_policies")(get_routing_policies)
mcp.tool(name="get_interfaces")(get_interfaces)
mcp.tool(name="ping")(ping)
mcp.tool(name="traceroute")(traceroute)
mcp.tool(name="run_show")(run_show)
mcp.tool(name="get_intent")(get_intent)
mcp.tool(name="assess_risk")(assess_risk)
mcp.tool(name="push_config")(push_config)
mcp.tool(name="jira_add_comment")(jira_add_comment)
mcp.tool(name="jira_resolve_issue")(jira_resolve_issue)
mcp.tool(name="request_approval")(request_approval)
mcp.tool(name="post_approval_outcome")(post_approval_outcome)

log.info("aiNOC MCP Server started — 15 tools registered")

if __name__ == "__main__":
    mcp.run()
