"""
backend/app/evals/eval_suite.py
Automated evaluation suite benchmarking statutory grounding and hallucination rate
"""
import os
from dotenv import load_dotenv

# Load .env before importing any application code
load_dotenv()

import asyncio
from app.services.compliance_rag import explain_transaction_compliance

BENCHMARK_TESTSET = [
    {
        "category": "ITC Eligibility",
        "error_flag": "BLOCKED_CREDIT_SEC_17_5",
        "description": "Purchase of corporate motor car for employee transport.",
        "expected_legal_term": "17(5)"
    },
    {
        "category": "Reverse Charge",
        "error_flag": "UNPAID_RCM_TRANSPORT",
        "description": "Payment made to GTA transporter without reverse charge line item.",
        "expected_legal_term": "rcm"
    },
    {
        "category": "General Discrepancy",
        "error_flag": "UNREGISTERED_PROVISION_XYZ",
        "description": "Completely random fabricated transaction without statutory basis.",
        "expected_legal_term": "unable to ground explanation"
    }
]


async def run_audit_eval_suite():
    total = len(BENCHMARK_TESTSET)
    passed_citations = 0
    grounding_enforced = 0

    print("\n🚀 Starting GST-Audit-AI Offline Evaluation Suite...\n" + "=" * 50)

    for idx, test in enumerate(BENCHMARK_TESTSET):
        res = await explain_transaction_compliance(
            category=test["category"],
            error_flag=test["error_flag"],
            description=test["description"]
        )

        expected = test["expected_legal_term"].lower()
        full_text = (res.get("explanation", "") + " " + res.get("actionable_fix", "")).lower()

        # Verify hallucination refusal
        if expected == "unable to ground explanation":
            if not res.get("grounded", True):
                grounding_enforced += 1
                status = "PASS (Correctly Refused Hallucination)"
            else:
                status = "FAIL (Hallucinated Grounding)"
        else:
            if expected in full_text:
                passed_citations += 1
                status = "PASS (Accurate Statutory Grounding)"
            else:
                status = "FAIL (Missing Section Citation)"

        print(f"[{idx+1}/{total}] {test['error_flag']} -> {status}")

    accuracy = (passed_citations + grounding_enforced) / total
    print("=" * 50)
    print(f"✅ Final Evaluation Score: {accuracy:.1%}")
    print(f"• Statutory Citation Accuracy: {passed_citations}/2")
    print(f"• Hallucination Guardrail Enforcement: {grounding_enforced}/1\n")


if __name__ == "__main__":
    asyncio.run(run_audit_eval_suite())