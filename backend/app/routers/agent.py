"""
backend/app/routers/agent.py
REST endpoint for CA Natural Language Interactive Agent
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from app.agent.graph import audit_agent_executor
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["Autonomous Auditor Agent"])


class AgentQueryRequest(BaseModel):
    query: str
    session_id: str | None = None


class AgentQueryResponse(BaseModel):
    query: str
    response: str
    steps_taken: int


SYSTEM_INSTRUCTION = """You are AuditAI's Principal Chartered Accountant Assistant.
You have access to tools for checking Supplier ML Trust Scores, retrieving Grounded GST Legal Rules, and Classifying HSN codes.
When asked a question:
1. Identify what tools are necessary (call only what is required).
2. Execute tool calls and parse facts.
3. Synthesize a concise, professional answer tailored for an Indian Chartered Accountant, highlighting legal sections and specific numeric risks clearly.
"""


@router.post("/query", response_model=AgentQueryResponse)
async def query_audit_agent(payload: AgentQueryRequest):
    try:
        messages = [
            SystemMessage(content=SYSTEM_INSTRUCTION),
            HumanMessage(content=payload.query)
        ]
        
        # Invoke LangGraph agent loop (with safety recursion limit = 6)
        state_output = await audit_agent_executor.ainvoke(
            {"messages": messages},
            config={"recursion_limit": 6}
        )

        final_msg = state_output["messages"][-1]
        total_steps = len(state_output["messages"]) - 2  # subtract system & initial human prompt

        return AgentQueryResponse(
            query=payload.query,
            response=final_msg.content,
            steps_taken=max(1, total_steps)
        )

    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Agent workflow error: {str(e)}"
        )