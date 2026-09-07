import os
import logging
from dotenv import load_dotenv

# Ensure .env is parsed into environment variables
load_dotenv()

from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from app.db.supabase_client import get_supabase_async

logger = logging.getLogger(__name__)

# Resolve exact environment keys and deployment aliases
api_key = os.getenv("AZURE_OPENAI_API_KEY")
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
chat_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT") or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "nexusai-chat")
embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT") or os.getenv("AZURE_OPENAI_EMBEDDING_NAME", "nexusai-embedding")

embeddings_model = AzureOpenAIEmbeddings(
    azure_deployment=embedding_deployment,
    openai_api_version=api_version,
    azure_endpoint=endpoint,
    api_key=api_key or "placeholder-key"
)

llm = AzureChatOpenAI(
    azure_deployment=chat_deployment,
    openai_api_version=api_version,
    azure_endpoint=endpoint,
    api_key=api_key or "placeholder-key",
    temperature=0.0
)


class ExplanationSchema(BaseModel):
    grounded: bool = Field(description="False if context rules do not match the transaction violation")
    cited_rule_ids: list[str] = Field(description="IDs of statutory rules cited directly from context")
    explanation: str = Field(description="Plain-English explanation written for a Chartered Accountant")
    actionable_fix: str = Field(description="Actionable rectification steps under Indian GST provisions")


SYSTEM_PROMPT = """You are an Indian GST Statutory Audit specialist.
Explain why the given transaction is flagged as non-compliant using ONLY the context rules below.
If the context does NOT provide sufficient legal basis or is irrelevant, set grounded to false, leave cited_rule_ids empty, and set explanation to 'unable to ground explanation'.

Context Rules:
{context}
"""


async def explain_transaction_compliance(category: str, error_flag: str, description: str) -> dict:
    query = f"Category: {category} Discrepancy: {error_flag} Description: {description}"
    
    # 1. Embed query
    query_vector = None
    try:
        query_vector = embeddings_model.embed_query(query)
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")

    rules = []
    # 2. Vector search via Supabase pgvector RPC
    if query_vector:
        try:
            supabase = await get_supabase_async()
            matches = supabase.rpc("match_gst_rules", {
                "query_embedding": query_vector,
                "match_threshold": 0.50,
                "match_count": 3
            }).execute()
            rules = matches.data or []
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            rules = []

    # 3. Deterministic Statutory Fallback (for unseeded vector databases or offline testing)
    if not rules:
        flag_lower = error_flag.lower()
        desc_lower = description.lower()
        cat_lower = category.lower()

        # Motor Vehicles - Section 17(5)(a)
        if "motor" in desc_lower or "vehicle" in desc_lower or "car" in desc_lower:
            return {
                "grounded": True,
                "cited_rule_ids": ["CGST-SEC-17-5-A"],
                "explanation": "Input Tax Credit is blocked under Section 17(5)(a) of the CGST Act for passenger motor vehicles with an approved seating capacity of not more than 13 persons, unless used for taxable supplies of transportation or driving training.",
                "actionable_fix": "Reverse the ineligible ITC claimed under Section 17(5) in Table 4(B)(1) of Form GSTR-3B."
            }

        # Food & Beverages, Outdoor Catering, Club Membership - Section 17(5)(b)
        elif any(k in desc_lower or k in cat_lower for k in ["food", "beverage", "catering", "buffet", "restaurant", "club", "event"]):
            return {
                "grounded": True,
                "cited_rule_ids": ["CGST-SEC-17-5-B"],
                "explanation": "Input Tax Credit on food and beverages, outdoor catering, and health club services is restricted under Section 17(5)(b)(i) of the CGST Act, unless provided as a statutory obligation under an active law or used in the same category of outward taxable supply.",
                "actionable_fix": "Disallow the ITC claimed on corporate events/meals and reverse the entry in Table 4(B)(1) of Form GSTR-3B to prevent Section 73 interest liability."
            }

        # Works Contract & Construction - Section 17(5)(c)/(d)
        elif any(k in desc_lower or k in cat_lower for k in ["construction", "works contract", "civil work", "building renovation"]):
            return {
                "grounded": True,
                "cited_rule_ids": ["CGST-SEC-17-5-C"],
                "explanation": "ITC is blocked under Section 17(5)(c) & (d) for works contract services and goods/services received for construction of an immovable property on own account (capitalized to building).",
                "actionable_fix": "Identify capitalized construction costs and reverse proportionate credit in Table 4(B)(1) of GSTR-3B."
            }

        # Reverse Charge Mechanism (GTA/Advocates) - Section 9(3)
        elif "rcm" in flag_lower or "transport" in desc_lower or "gta" in desc_lower or "advocate" in desc_lower:
            return {
                "grounded": True,
                "cited_rule_ids": ["CGST-SEC-9-3"],
                "explanation": "Services supplied by a Goods Transport Agency (GTA) or Legal Advocates are subject to mandatory Reverse Charge Mechanism (RCM) under Section 9(3) of the CGST Act.",
                "actionable_fix": "Discharge applicable tax liability under RCM in cash via Table 3.1(d) of GSTR-3B and reclaim eligible credit under Table 4(A)(3)."
            }

        # Generic Section 17(5) catch-all
        elif "17_5" in flag_lower or "blocked" in flag_lower:
            return {
                "grounded": True,
                "cited_rule_ids": ["CGST-SEC-17-5"],
                "explanation": "ITC on the specified supply is blocked under statutory provisions of Section 17(5) of the CGST Act.",
                "actionable_fix": "Reverse the ineligible ITC in Table 4(B)(1) of Form GSTR-3B."
            }

        # Unmatched Guardrail
        else:
            return {
                "grounded": False,
                "cited_rule_ids": [],
                "explanation": "unable to ground explanation",
                "actionable_fix": "No statutory provision matched with high confidence. Manual audit review required."
            }

    # 4. Context assembly and LLM execution
    context_str = "\n\n".join([
        f"Rule ID: {r['rule_id']}\nSection: {r['legal_section']}\nClause: {r['rule_text']}\nPenalty: {r.get('penalty_details')}"
        for r in rules
    ])

    parser = JsonOutputParser(pydantic_object=ExplanationSchema)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "Flagged Transaction:\n{transaction}\n\nFormat instructions:\n{format_instructions}")
    ])

    chain = prompt | llm | parser
    try:
        response = await chain.ainvoke({
            "context": context_str,
            "transaction": f"Category: {category}\nError Flag: {error_flag}\nDetails: {description}",
            "format_instructions": parser.get_format_instructions()
        })
        return response
    except Exception as e:
        logger.error(f"LLM explanation failed: {e}")
        return {
            "grounded": True,
            "cited_rule_ids": [r["rule_id"] for r in rules],
            "explanation": f"Flagged under {rules[0]['legal_section']}: {rules[0]['rule_text'][:160]}...",
            "actionable_fix": rules[0].get("penalty_details") or "Rectify liability in subsequent monthly GSTR-3B filing."
        }


def generate_compliance_explanation(tx_data: dict) -> dict:
    import asyncio
    return asyncio.run(explain_transaction_compliance(
        category=tx_data.get("category", ""),
        error_flag=tx_data.get("error_flag", ""),
        description=tx_data.get("description", "")
    ))