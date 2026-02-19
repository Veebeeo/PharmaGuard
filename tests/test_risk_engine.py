import pytest
from backend.risk_engine import determine_phenotype, assess_risk

def test_determine_phenotype_cyp2d6():
    # Test known edge cases and standard paths
    assert determine_phenotype("*4", "*6", "CYP2D6") == "PM"
    assert determine_phenotype("*1", "*1", "CYP2D6") == "NM"
    assert determine_phenotype("*10", "*10", "CYP2D6") == "IM"

def test_determine_phenotype_cyp2c19():
    assert determine_phenotype("*2", "*2", "CYP2C19") == "PM"
    assert determine_phenotype("*17", "*17", "CYP2C19") == "URM"

def test_assess_risk_logic():
    # PMs should not get Codeine
    result = assess_risk("CODEINE", "PM")
    assert result["risk_assessment"]["risk_label"] == "Ineffective"
    assert result["risk_assessment"]["severity"] == "high"
    
    # NMs are safe with Warfarin
    result_warfarin = assess_risk("WARFARIN", "NM")
    assert result_warfarin["risk_assessment"]["risk_label"] == "Safe"

def test_unsupported_drug_handling():
    result = assess_risk("TYLENOL", "NM")
    assert result["risk_assessment"]["risk_label"] == "Unknown"