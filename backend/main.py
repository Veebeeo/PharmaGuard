"""
PharmaGuard AI — FastAPI Application
Main entry point: handles VCF upload, drug analysis, and serves the frontend.

Endpoints:
  POST /api/analyze       — Upload VCF + drug names → full analysis
  GET  /api/health        — Health check
  GET  /api/supported-drugs — List supported drugs
  GET  /                   — Serve frontend
"""
import os
import uuid
from datetime import datetime
from typing import List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from dotenv import load_dotenv

from models import (
    PharmaGuardResponse, MultiDrugResponse, RiskAssessment,
    PharmacogenomicProfile, ClinicalRecommendation, LLMExplanation,
    QualityMetrics, DetectedVariant,
)
from vcf_parser import parse_vcf, build_profile_for_drug
from risk_engine import (
    assess_risk, resolve_drug, SUPPORTED_DRUGS, DRUG_GENE_MAP, DRUG_ALIASES,
)
from gemini_service import generate_explanation

load_dotenv()

# ── App setup ─────────────────────────────────────────────────────
app = FastAPI(
    title="PharmaGuard AI",
    description="AI-powered pharmacogenomic risk analysis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    has_key = bool(os.environ.get("GOOGLE_API_KEY"))
    return {
        "status": "healthy",
        "version": "1.0.0",
        "gemini_configured": has_key,
        "supported_drugs": SUPPORTED_DRUGS,
    }


@app.get("/api/supported-drugs")
async def supported_drugs():
    return {
        "drugs": SUPPORTED_DRUGS,
        "aliases": DRUG_ALIASES,
        "drug_details": {
            drug: {"gene": info["gene"], "drug_class": info["drug_class"]}
            for drug, info in DRUG_GENE_MAP.items()
        },
    }


# ── Main analysis endpoint ────────────────────────────────────────
@app.post("/api/analyze", response_model=MultiDrugResponse)
async def analyze(
    vcf_file: UploadFile = File(...),
    drugs: str = Form(...),
):
    """
    Analyze a VCF file against one or more drugs.

    - **vcf_file**: VCF file upload (.vcf format)
    - **drugs**: Comma-separated drug names (e.g., "CODEINE,WARFARIN")
    """

    # ── Validate file ─────────────────────────────────────────
    if not vcf_file.filename:
        raise HTTPException(400, "No file uploaded")

    if not vcf_file.filename.lower().endswith(".vcf"):
        raise HTTPException(400, f"Invalid file type: {vcf_file.filename}. Only .vcf files are accepted.")

    # Read file content
    try:
        content = await vcf_file.read()
        if len(content) > 5 * 1024 * 1024:  # 5 MB limit
            raise HTTPException(400, "File too large. Maximum size is 5 MB.")
        vcf_text = content.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        raise HTTPException(400, "File encoding error. VCF must be UTF-8 text.")

    if not vcf_text.strip():
        raise HTTPException(400, "VCF file is empty.")

    # ── Parse VCF ─────────────────────────────────────────────
    parsed = parse_vcf(vcf_text)

    if not parsed["vcf_valid"] and not parsed["pgx_variants"]:
        raise HTTPException(
            400,
            f"Invalid VCF file. Errors: {'; '.join(parsed['errors']) if parsed['errors'] else 'Could not parse variant data.'}"
        )

    # ── Parse drug list ───────────────────────────────────────
    drug_list = [d.strip().upper() for d in drugs.split(",") if d.strip()]
    if not drug_list:
        raise HTTPException(400, "No drugs specified. Provide at least one drug name.")

    # ── Analyze each drug ─────────────────────────────────────
    analysis_id = str(uuid.uuid4())[:8]
    results: List[PharmaGuardResponse] = []

    for drug_raw in drug_list:
        drug = resolve_drug(drug_raw)
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Build pharmacogenomic profile
        profile_data = build_profile_for_drug(parsed, drug)

        # Get risk assessment + clinical rec
        risk_data = assess_risk(drug, profile_data["phenotype"])

        # Build detected variants list for response
        detected_variants = [
            DetectedVariant(**v) for v in profile_data["detected_variants"]
        ]

        # Generate LLM explanation
        llm_result = generate_explanation(
            drug=drug,
            gene=profile_data["primary_gene"],
            diplotype=profile_data["diplotype"],
            phenotype=profile_data["phenotype"],
            risk_label=risk_data["risk_assessment"]["risk_label"],
            severity=risk_data["risk_assessment"]["severity"],
            variants=profile_data["detected_variants"],
            dosing_rec=risk_data["clinical_recommendation"]["dosing_recommendation"],
        )

        # Assemble response
        response = PharmaGuardResponse(
            patient_id=parsed["patient_id"],
            drug=drug,
            timestamp=timestamp,
            risk_assessment=RiskAssessment(**risk_data["risk_assessment"]),
            pharmacogenomic_profile=PharmacogenomicProfile(
                primary_gene=profile_data["primary_gene"],
                diplotype=profile_data["diplotype"],
                phenotype=profile_data["phenotype"],
                detected_variants=detected_variants,
            ),
            clinical_recommendation=ClinicalRecommendation(**risk_data["clinical_recommendation"]),
            llm_generated_explanation=LLMExplanation(**llm_result),
            quality_metrics=QualityMetrics(
                vcf_parsing_success=parsed["vcf_valid"],
                total_variants_parsed=parsed["total_variants"],
                pharmacogenomic_variants_found=len(parsed["pgx_variants"]),
                gene_coverage=parsed["genes_found"],
                analysis_timestamp=timestamp,
                llm_response_received=llm_result.get("model_used", "").startswith("gemini"),
            ),
        )
        results.append(response)

    return MultiDrugResponse(
        results=results,
        total_drugs_analyzed=len(results),
        analysis_id=analysis_id,
    )


# ── Serve frontend ────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/")
async def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "PharmaGuard AI API is running. Frontend not found at /frontend/index.html"})


# Serve static assets
if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
