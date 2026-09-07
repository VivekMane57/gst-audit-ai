"""
backend/app/agent/graph.py
Autonomous Multi-Tool LangGraph Agent for GST CA Advisory
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

from typing import Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.ml.trust_scoring.service import trust_service
from app.services.compliance_rag import explain_transaction_compliance
from app.services.hsn_classifier import classify_item_description
from app.db.supabase_client import get_supabase_async


# ── Statutory System Prompt ──

AGENT_SYSTEM_PROMPT = """You are AuditAI's Principal CA Advisor.
When presenting data comparisons, supplier risk metrics, SHAP impact factors, tax slabs, or HSN predictions, ALWAYS structure key metrics using clean Markdown Tables.
Use standalone bold text for headings and bullet points for narrative advice.
Ensure all statutory sections under the CGST Act are explicitly cited where applicable. Keep explanations clear, rigorous, and actionable for a Chartered Accountant."""


# ── Define Agent Callable Tools ──

@tool
async def lookup_supplier_trust_score(supplier_id: str) -> str:
    """Useful to check credit risk, filing delay, and ML trust score (0-100) of a GST supplier by ID."""
    try:
        supabase = await get_supabase_async()
        res = supabase.table("supplier_features").select("*").eq("supplier_id", supplier_id).limit(1).execute()
        features = res.data[0] if res.data else {
            "filing_frequency_ratio": 0.95,
            "avg_filing_delay_days": 2.0,
            "gstr_mismatch_count": 0,
            "hsn_consistency_score": 1.0,
            "historical_flag_count": 0
        }
        score, factors = trust_service.predict(features)
        return json.dumps({
            "supplier_id": supplier_id,
            "trust_score": score,
            "primary_risk_drivers": factors
        })
    except Exception as e:
        return json.dumps({"error": f"Failed to retrieve trust score: {str(e)}"})


@tool
async def explain_gst_compliance_rule(category: str, error_flag: str, description: str) -> str:
    """Useful to find statutory GST Act legal sections, penalty clauses, and fixes for a flagged compliance issue."""
    try:
        result = await explain_transaction_compliance(
            category=category,
            error_flag=error_flag,
            description=description
        )
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": f"Failed to explain compliance: {str(e)}"})


@tool
async def suggest_hsn_code(item_description: str) -> str:
    """Useful to predict the correct 6-digit statutory HSN code and GST tax slab for an item or service description."""
    try:
        matches = await classify_item_description(item_description, top_k=2)
        return json.dumps(matches)
    except Exception as e:
        return json.dumps({"error": f"Failed to classify HSN: {str(e)}"})


AVAILABLE_TOOLS = [lookup_supplier_trust_score, explain_gst_compliance_rule, suggest_hsn_code]


# ── Configure LLM with Tool Binding ──

def get_agent_llm():
    chat_dep = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "nexusai-chat")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

    llm = AzureChatOpenAI(
        azure_deployment=chat_dep,
        openai_api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key or "placeholder-key",
        temperature=0.0
    )
    return llm.bind_tools(AVAILABLE_TOOLS)


# ── State Graph Architecture with add_messages Reducer ──

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


async def call_model_node(state: AgentState):
    llm = get_agent_llm()
    # Inject CA Advisory formatting instructions before the ongoing conversation
    messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + state["messages"]
    response = await llm.ainvoke(messages)
    return {"messages": [response]}


def route_decision(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# ── Build & Compile Graph ──

workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model_node)
workflow.add_node("tools", ToolNode(AVAILABLE_TOOLS))

workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", route_decision, {
    "tools": "tools",
    END: END
})
workflow.add_edge("tools", "agent")

audit_agent_executor = workflow.compile()