"""
PharmaGuard AI — Supabase Client
Handles all Supabase interactions:
  1. DB queries for phenotype mappings & CPIC guidelines (rule engine)
  2. Storage bucket for VCF file uploads
  3. Patient report persistence
  4. Auth token verification

Falls back gracefully to hardcoded data when Supabase is not configured.
"""
import os
import json
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from supabase import create_client, Client
    SUPABASE_SDK = True
except ImportError:
    SUPABASE_SDK = False

_client: Optional[Any] = None
_enabled: bool = False


def init_supabase() -> bool:
    """Initialize Supabase client. Returns True if successful."""
    global _client, _enabled
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")  # This should be the service_role key for backend
    if not url or not key or not SUPABASE_SDK:
        _enabled = False
        return False
    try:
        _client = create_client(url, key)
        _enabled = True
        return True
    except Exception as e:
        print(f"[Supabase] Init failed: {e}")
        _enabled = False
        return False


def is_enabled() -> bool:
    return _enabled and _client is not None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. RULE ENGINE QUERIES (replaces hardcoded dicts)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def db_get_known_variant(rsid: str) -> Optional[Dict]:
    """Look up a variant by rsID from the known_variants table."""
    if not is_enabled():
        return None
    try:
        resp = _client.table("known_variants").select("*").eq("rsid", rsid).limit(1).execute()
        if resp.data:
            row = resp.data[0]
            return {
                "gene": row["gene"],
                "star": row["star_allele"],
                "effect": row["functional_effect"],
                "desc": row.get("description", ""),
            }
    except Exception as e:
        print(f"[Supabase] known_variants query error: {e}")
    return None


def db_get_allele_activity(gene: str, star: str) -> Optional[float]:
    """Get activity score for a gene + star allele pair."""
    if not is_enabled():
        return None
    try:
        resp = (_client.table("allele_activity")
                .select("activity_score")
                .eq("gene", gene)
                .eq("star_allele", star)
                .limit(1).execute())
        if resp.data:
            return float(resp.data[0]["activity_score"])
    except Exception as e:
        print(f"[Supabase] allele_activity query error: {e}")
    return None


def db_get_cpic_guideline(drug: str, phenotype: str) -> Optional[Dict]:
    """
    Get CPIC guideline for a drug + phenotype combo.
    Returns dict matching assess_risk() output format.
    """
    if not is_enabled():
        return None
    try:
        resp = (_client.table("cpic_guidelines")
                .select("*")
                .eq("drug", drug.upper())
                .eq("phenotype", phenotype)
                .limit(1).execute())
        if resp.data:
            row = resp.data[0]
            return {
                "risk_assessment": {
                    "risk_label": row["risk_label"],
                    "confidence_score": float(row["confidence"]),
                    "severity": row["severity"],
                },
                "clinical_recommendation": {
                    "dosing_recommendation": row["dosing_recommendation"],
                    "alternative_drugs": row.get("alternative_drugs") or [],
                    "monitoring_parameters": row.get("monitoring_parameters") or [],
                    "cpic_guideline_reference": row.get("cpic_reference", ""),
                    "urgency": row.get("urgency", "routine"),
                },
            }
    except Exception as e:
        print(f"[Supabase] cpic_guidelines query error: {e}")
    return None


def db_get_drug_gene(drug: str) -> Optional[Dict]:
    """Get drug → gene mapping from DB."""
    if not is_enabled():
        return None
    try:
        resp = (_client.table("drug_gene_map")
                .select("*")
                .eq("drug", drug.upper())
                .limit(1).execute())
        if resp.data:
            row = resp.data[0]
            return {
                "gene": row["gene"],
                "pathway": row.get("pathway", ""),
                "drug_class": row.get("drug_class", ""),
            }
    except Exception as e:
        print(f"[Supabase] drug_gene_map query error: {e}")
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. VCF STORAGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def upload_vcf(user_id: str, filename: str, content: bytes) -> Optional[str]:
    """
    Upload a VCF file to Supabase Storage.
    Returns the storage path on success, None on failure.
    Files are stored under: {user_id}/{timestamp}_{filename}
    """
    if not is_enabled():
        return None
    try:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = f"{user_id}/{ts}_{filename}"
        _client.storage.from_("vcf-uploads").upload(
            path, content,
            file_options={"content-type": "text/plain"}
        )
        return path
    except Exception as e:
        print(f"[Supabase] VCF upload error: {e}")
        return None


def download_vcf(path: str) -> Optional[bytes]:
    """Download a VCF file from Supabase Storage."""
    if not is_enabled() or not path:
        return None
    try:
        data = _client.storage.from_("vcf-uploads").download(path)
        return data
    except Exception as e:
        print(f"[Supabase] VCF download error: {e}")
        return None


def delete_vcf(path: str) -> bool:
    """Delete a VCF file from Supabase Storage after processing."""
    if not is_enabled() or not path:
        return False
    try:
        _client.storage.from_("vcf-uploads").remove([path])
        return True
    except Exception as e:
        print(f"[Supabase] VCF delete error: {e}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. PATIENT REPORTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def save_report(user_id: str, report: Dict, vcf_path: Optional[str] = None) -> Optional[str]:
    """
    Save a completed analysis report to the patient_reports table.
    Returns the report UUID on success.
    """
    if not is_enabled():
        return None
    try:
        report_id = str(uuid.uuid4())
        row = {
            "id": report_id,
            "user_id": user_id,
            "patient_id": report.get("patient_id", ""),
            "drug": report.get("drug", ""),
            "risk_label": report.get("risk_assessment", {}).get("risk_label", ""),
            "severity": report.get("risk_assessment", {}).get("severity", ""),
            "phenotype": report.get("pharmacogenomic_profile", {}).get("phenotype", ""),
            "gene": report.get("pharmacogenomic_profile", {}).get("primary_gene", ""),
            "diplotype": report.get("pharmacogenomic_profile", {}).get("diplotype", ""),
            "report_json": report,
            "vcf_storage_path": vcf_path,
        }
        _client.table("patient_reports").insert(row).execute()
        return report_id
    except Exception as e:
        print(f"[Supabase] save_report error: {e}")
        return None


def get_user_reports(user_id: str, limit: int = 50) -> List[Dict]:
    """Get all reports for a user, most recent first."""
    if not is_enabled():
        return []
    try:
        resp = (_client.table("patient_reports")
                .select("id, patient_id, drug, risk_label, severity, phenotype, gene, diplotype, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute())
        return resp.data or []
    except Exception as e:
        print(f"[Supabase] get_user_reports error: {e}")
        return []


def get_report_detail(user_id: str, report_id: str) -> Optional[Dict]:
    """Get a single full report (with JSONB) for a user."""
    if not is_enabled():
        return None
    try:
        resp = (_client.table("patient_reports")
                .select("*")
                .eq("user_id", user_id)
                .eq("id", report_id)
                .limit(1)
                .execute())
        if resp.data:
            return resp.data[0]
    except Exception as e:
        print(f"[Supabase] get_report_detail error: {e}")
    return None


def delete_report(user_id: str, report_id: str) -> bool:
    """Delete a report."""
    if not is_enabled():
        return False
    try:
        _client.table("patient_reports").delete().eq("user_id", user_id).eq("id", report_id).execute()
        return True
    except Exception as e:
        print(f"[Supabase] delete_report error: {e}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. AUTH — Verify Supabase JWT tokens
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def verify_token(access_token: str) -> Optional[Dict]:
    """
    Verify a Supabase access token and return user info.
    Returns {"id": user_id, "email": email} or None.
    """
    if not is_enabled():
        return None
    try:
        user_resp = _client.auth.get_user(access_token)
        if user_resp and user_resp.user:
            return {
                "id": str(user_resp.user.id),
                "email": user_resp.user.email or "",
            }
    except Exception as e:
        print(f"[Supabase] verify_token error: {e}")
    return None
