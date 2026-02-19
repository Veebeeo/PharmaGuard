import json
import pytest
from backend.gemini_service import generate_explanation

# Note: This test actually calls the Gemini API. 
# In a CI/CD pipeline, you'd mock this, but for model validation, run it locally.
@pytest.mark.asyncio
async def test_gemini_clinical_correctness():
    # Input a high-risk scenario
    result = generate_explanation(
        drug="CODEINE",
        gene="CYP2D6",
        diplotype="*4/*6",
        phenotype="PM",
        risk_label="Ineffective",
        severity="high",
        variants=[{"rsid": "rs3892097", "functional_effect": "no_function"}],
        dosing_rec="AVOID codeine."
    )
    
    # 1. Test Schema Adherence
    assert "summary" in result
    assert "mechanism" in result
    assert "patient_friendly_summary" in result
    
    # 2. Test Factuality (Keyword Assertion)
    summary_lower = result["summary"].lower()
    friendly_lower = result["patient_friendly_summary"].lower()
    
    # It must mention that it is a poor metabolizer
    assert "poor metabolizer" in summary_lower or "pm" in summary_lower
    # It must NOT contradict the clinical recommendation
    assert "safe" not in friendly_lower
    assert "avoid" in friendly_lower or "alternative" in friendly_lower

    # 3. Test biological mechanism hallucination
    mech_lower = result["mechanism"].lower()
    assert "morphine" in mech_lower # Must mention conversion to morphine