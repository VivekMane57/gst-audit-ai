from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.compliance_rag import explain_transaction_compliance

router = APIRouter(prefix="/api/v1/compliance", tags=["Compliance Interpreter"])

class ComplianceExplainRequest(BaseModel):
    category: str
    error_flag: str
    description: str

class ComplianceExplainResponse(BaseModel):
    grounded: bool
    cited_rule_ids: list[str]
    explanation: str
    actionable_fix: str

@router.post("/explain", response_model=ComplianceExplainResponse)
async def explain_compliance(payload: ComplianceExplainRequest):
    try:
        result = await explain_transaction_compliance(
            category=payload.category,
            error_flag=payload.error_flag,
            description=payload.description
        )
        return ComplianceExplainResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))