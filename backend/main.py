"""
PharmaGuard AI — FastAPI Application (v2 with Supabase)
Endpoints:
  POST /api/analyze          — Public analysis (no auth)
  POST /api/analyze-secure   — Auth + storage + report saving
  POST /api/auth/signup      — Create account
  POST /api/auth/login       — Login
  POST /api/auth/logout      — Logout
  GET  /api/auth/user        — Current user
  GET  /api/dashboard        — User's saved reports
  GET  /api/dashboard/{id}   — Report detail
  DELETE /api/dashboard/{id} — Delete report
  GET  /api/health           — Health check
  GET  /api/supported-drugs  — Supported drugs
  GET  /                     — Serve frontend
"""
import os, uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Request
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
from risk_engine import assess_risk, resolve_drug, SUPPORTED_DRUGS, DRUG_GENE_MAP, DRUG_ALIASES
from gemini_service import generate_explanation
import supabase_client

load_dotenv()
supabase_ok = supabase_client.init_supabase()

app = FastAPI(title="PharmaGuard AI", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# ── Helpers ───────────────────────────────────────────────────────
def get_user(auth: Optional[str]) -> Optional[dict]:
    if not auth: return None
    token = auth.replace("Bearer ", "") if auth.startswith("Bearer ") else auth
    return supabase_client.verify_token(token) if token else None

def validate_vcf(f: UploadFile):
    if not f.filename: raise HTTPException(400, "No file uploaded")
    if not f.filename.lower().endswith(".vcf"):
        raise HTTPException(400, f"Invalid file type: {f.filename}. Only .vcf accepted.")

async def read_vcf(f: UploadFile) -> tuple:
    try:
        content = await f.read()
        if len(content) > 5*1024*1024: raise HTTPException(400, "File too large. Max 5 MB.")
        text = content.decode("utf-8", errors="replace")
    except UnicodeDecodeError:
        raise HTTPException(400, "File encoding error.")
    if not text.strip(): raise HTTPException(400, "VCF file is empty.")
    return content, text

def parse_drugs(drugs: str) -> List[str]:
    dl = [d.strip().upper() for d in drugs.split(",") if d.strip()]
    if not dl: raise HTTPException(400, "No drugs specified.")
    return dl


# ── Core analysis pipeline ────────────────────────────────────────
def run_pipeline(vcf_text: str, drug_list: List[str]) -> dict:
    parsed = parse_vcf(vcf_text)
    if not parsed["vcf_valid"] and not parsed["pgx_variants"]:
        errs = "; ".join(parsed["errors"]) if parsed["errors"] else "Could not parse."
        raise HTTPException(400, f"Invalid VCF: {errs}")

    aid = str(uuid.uuid4())[:8]
    results = []
    for drug_raw in drug_list:
        drug = resolve_drug(drug_raw)
        ts = datetime.utcnow().isoformat() + "Z"
        profile = build_profile_for_drug(parsed, drug)
        risk = assess_risk(drug, profile["phenotype"], gene=profile["primary_gene"], diplotype=profile["diplotype"])
        dvs = [DetectedVariant(**v) for v in profile["detected_variants"]]
        llm = generate_explanation(
            drug=drug, gene=profile["primary_gene"], diplotype=profile["diplotype"],
            phenotype=profile["phenotype"], risk_label=risk["risk_assessment"]["risk_label"],
            severity=risk["risk_assessment"]["severity"], variants=profile["detected_variants"],
            dosing_rec=risk["clinical_recommendation"]["dosing_recommendation"],
        )
        r = PharmaGuardResponse(
            patient_id=parsed["patient_id"], drug=drug, timestamp=ts,
            risk_assessment=RiskAssessment(**risk["risk_assessment"]),
            pharmacogenomic_profile=PharmacogenomicProfile(
                primary_gene=profile["primary_gene"], diplotype=profile["diplotype"],
                phenotype=profile["phenotype"], detected_variants=dvs,
            ),
            clinical_recommendation=ClinicalRecommendation(**risk["clinical_recommendation"]),
            llm_generated_explanation=LLMExplanation(**llm),
            quality_metrics=QualityMetrics(
                vcf_parsing_success=parsed["vcf_valid"], total_variants_parsed=parsed["total_variants"],
                pharmacogenomic_variants_found=len(parsed["pgx_variants"]),
                gene_coverage=parsed["genes_found"], analysis_timestamp=ts,
                llm_response_received=llm.get("model_used","").startswith("gemini"),
            ),
        )
        results.append(r)
    return {"results": results, "parsed": parsed, "analysis_id": aid}


# ━━━ HEALTH ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.get("/api/health")
async def health():
    return {"status":"healthy","version":"2.0.0",
            "gemini_configured":bool(os.environ.get("GOOGLE_API_KEY")),
            "supabase_configured":supabase_client.is_enabled(),
            "supported_drugs":SUPPORTED_DRUGS}

@app.get("/api/supported-drugs")
async def drugs_list():
    return {"drugs":SUPPORTED_DRUGS,"aliases":DRUG_ALIASES,
            "drug_details":{d:{"gene":i["gene"],"drug_class":i["drug_class"]} for d,i in DRUG_GENE_MAP.items()}}

@app.get("/api/cpic-pairs")
async def cpic_pairs():
    """Get ALL gene-drug pairs from the official CPIC database (34 genes, 164+ drugs)."""
    try:
        from cpic_api import cpic_get_all_pairs, is_cpic_available
        if not is_cpic_available():
            return {"pairs":[], "cpic_available": False, "message": "CPIC API unreachable. Using local database."}
        level_a = cpic_get_all_pairs("A")
        level_b = cpic_get_all_pairs("B")
        return {
            "pairs": level_a + level_b,
            "total_level_a": len(level_a),
            "total_level_b": len(level_b),
            "total": len(level_a) + len(level_b),
            "cpic_available": True,
            "source": "https://api.cpicpgx.org",
        }
    except Exception as e:
        return {"pairs":[], "cpic_available": False, "error": str(e)}


# ━━━ PUBLIC ANALYSIS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.post("/api/analyze", response_model=MultiDrugResponse)
async def analyze(vcf_file: UploadFile=File(...), drugs: str=Form(...)):
    validate_vcf(vcf_file)
    _, text = await read_vcf(vcf_file)
    dl = parse_drugs(drugs)
    r = run_pipeline(text, dl)
    return MultiDrugResponse(results=r["results"], total_drugs_analyzed=len(r["results"]), analysis_id=r["analysis_id"])


# ━━━ SECURE ANALYSIS (auth + storage + save) ━━━━━━━━━━━━━━━━━━━━
@app.post("/api/analyze-secure")
async def analyze_secure(vcf_file: UploadFile=File(...), drugs: str=Form(...), authorization: Optional[str]=Header(None)):
    user = get_user(authorization)
    if not user: raise HTTPException(401, "Authentication required.")
    validate_vcf(vcf_file)
    content, text = await read_vcf(vcf_file)
    dl = parse_drugs(drugs)

    # Upload VCF to Supabase Storage
    vcf_path = supabase_client.upload_vcf(user["id"], vcf_file.filename, content)

    # Run analysis
    r = run_pipeline(text, dl)

    # Save reports
    saved = []
    for res in r["results"]:
        rd = res.model_dump() if hasattr(res, "model_dump") else res.dict()
        rid = supabase_client.save_report(user["id"], rd, vcf_path)
        if rid: saved.append(rid)

    return {
        "results": [res.model_dump() if hasattr(res,"model_dump") else res.dict() for res in r["results"]],
        "total_drugs_analyzed": len(r["results"]),
        "analysis_id": r["analysis_id"],
        "saved_report_ids": saved,
        "vcf_stored": vcf_path is not None,
    }


# ━━━ AUTH ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.post("/api/auth/signup")
async def signup(request: Request):
    if not supabase_client.is_enabled(): raise HTTPException(503, "Auth not configured.")
    body = await request.json()
    email, pw = body.get("email","").strip(), body.get("password","")
    if not email or not pw: raise HTTPException(400, "Email and password required.")
    if len(pw) < 6: raise HTTPException(400, "Password must be 6+ characters.")
    try:
        resp = supabase_client._client.auth.sign_up({"email":email,"password":pw})
        if resp.user:
            return {"success":True,"user_id":str(resp.user.id),"email":resp.user.email,
                    "message":"Account created. Check email if confirmation is enabled."}
        raise HTTPException(400, "Signup failed.")
    except Exception as e: raise HTTPException(400, f"Signup error: {e}")

@app.post("/api/auth/login")
async def login(request: Request):
    if not supabase_client.is_enabled(): raise HTTPException(503, "Auth not configured.")
    body = await request.json()
    email, pw = body.get("email","").strip(), body.get("password","")
    if not email or not pw: raise HTTPException(400, "Email and password required.")
    try:
        resp = supabase_client._client.auth.sign_in_with_password({"email":email,"password":pw})
        if resp.session:
            return {"success":True,"access_token":resp.session.access_token,
                    "refresh_token":resp.session.refresh_token,
                    "user":{"id":str(resp.user.id),"email":resp.user.email}}
        raise HTTPException(401, "Invalid credentials.")
    except Exception as e:
        if "invalid" in str(e).lower(): raise HTTPException(401, "Invalid email or password.")
        raise HTTPException(400, f"Login error: {e}")

@app.post("/api/auth/logout")
async def logout(): return {"success":True,"message":"Logged out."}

@app.get("/api/auth/user")
async def current_user(authorization: Optional[str]=Header(None)):
    user = get_user(authorization)
    if not user: raise HTTPException(401, "Not authenticated.")
    return {"user":user}


# ━━━ DASHBOARD ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@app.get("/api/dashboard")
async def dashboard(authorization: Optional[str]=Header(None)):
    user = get_user(authorization)
    if not user: raise HTTPException(401, "Auth required.")
    reports = supabase_client.get_user_reports(user["id"])
    return {"reports":reports,"total":len(reports)}

@app.get("/api/dashboard/{report_id}")
async def dashboard_detail(report_id: str, authorization: Optional[str]=Header(None)):
    user = get_user(authorization)
    if not user: raise HTTPException(401, "Auth required.")
    report = supabase_client.get_report_detail(user["id"], report_id)
    if not report: raise HTTPException(404, "Report not found.")
    return report

@app.delete("/api/dashboard/{report_id}")
async def dashboard_delete(report_id: str, authorization: Optional[str]=Header(None)):
    user = get_user(authorization)
    if not user: raise HTTPException(401, "Auth required.")
    if not supabase_client.delete_report(user["id"], report_id):
        raise HTTPException(404, "Not found or could not delete.")
    return {"success":True}


# ── Frontend ──────────────────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/")
async def serve_frontend():
    p = os.path.join(FRONTEND_DIR, "index.html")
    return FileResponse(p) if os.path.exists(p) else JSONResponse({"message":"PharmaGuard AI API running."})

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
