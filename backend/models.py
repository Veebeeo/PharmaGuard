"""
PharmaGuard AI — Pydantic Models
Exact JSON output schema per RIFT 2026 spec.
"""
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class DetectedVariant(BaseModel):
    rsid: str
    gene: str
    chromosome: str = ""
    position: int = 0
    ref_allele: str = ""
    alt_allele: str = ""
    star_allele: str = ""
    genotype: str = ""
    functional_effect: str = ""
    quality: float = 0.0


class RiskAssessment(BaseModel):
    risk_label: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    severity: str


class PharmacogenomicProfile(BaseModel):
    primary_gene: str
    diplotype: str
    phenotype: str
    detected_variants: List[DetectedVariant] = []


class ClinicalRecommendation(BaseModel):
    dosing_recommendation: str
    alternative_drugs: List[str] = []
    monitoring_parameters: List[str] = []
    cpic_guideline_reference: str = ""
    urgency: str = "routine"


class LLMExplanation(BaseModel):
    summary: str
    mechanism: str = ""
    variant_specific_effects: List[str] = []
    patient_friendly_summary: str = ""
    citations: List[str] = []
    model_used: str = "gemini-2.0-flash"


class QualityMetrics(BaseModel):
    vcf_parsing_success: bool = True
    total_variants_parsed: int = 0
    pharmacogenomic_variants_found: int = 0
    gene_coverage: List[str] = []
    analysis_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    llm_response_received: bool = False


class PharmaGuardResponse(BaseModel):
    patient_id: str
    drug: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    risk_assessment: RiskAssessment
    pharmacogenomic_profile: PharmacogenomicProfile
    clinical_recommendation: ClinicalRecommendation
    llm_generated_explanation: LLMExplanation
    quality_metrics: QualityMetrics


class MultiDrugResponse(BaseModel):
    results: List[PharmaGuardResponse]
    total_drugs_analyzed: int
    analysis_id: str = ""
