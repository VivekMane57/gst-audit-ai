from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.hsn_classifier import classify_item_description

router = APIRouter(prefix="/api/v1/hsn", tags=["HSN Auto-Classifier"])


class HSNClassifyRequest(BaseModel):
    description: str


class HSNMatch(BaseModel):
    hsn_code: str
    description: str
    gst_rate: float
    confidence: float


@router.post("/classify", response_model=list[HSNMatch])
async def classify_hsn(payload: HSNClassifyRequest):
    cleaned = payload.description.strip()
    if len(cleaned) < 2:
        raise HTTPException(status_code=400, detail="Description is too short for semantic matching.")

    return await classify_item_description(cleaned, top_k=3)