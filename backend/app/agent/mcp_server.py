"""
backend/app/agent/mcp_server.py
Exposes GST-Audit-AI tools over Standard Model Context Protocol (stdio/SSE)
"""
from mcp.server.fastmcp import FastMCP
from app.agent.graph import lookup_supplier_trust_score, explain_gst_compliance_rule, suggest_hsn_code

mcp = FastMCP("AuditAI-MCP-Tools")

@mcp.tool()
async def supplier_trust(supplier_id: str) -> str:
    """Fetches ML trust score (0-100) and SHAP risk factors for a supplier ID."""
    return await lookup_supplier_trust_score.ainvoke({"supplier_id": supplier_id})

@mcp.tool()
async def legal_compliance_lookup(category: str, error_flag: str, description: str) -> str:
    """Explains GST non-compliance grounded in statutory Act provisions."""
    return await explain_gst_compliance_rule.ainvoke({
        "category": category,
        "error_flag": error_flag,
        "description": description
    })

@mcp.tool()
async def hsn_classifier(item_description: str) -> str:
    """Predicts statutory HSN codes and GST rates for line items."""
    return await suggest_hsn_code.ainvoke({"item_description": item_description})

if __name__ == "__main__":
    mcp.run()