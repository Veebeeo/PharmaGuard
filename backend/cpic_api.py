"""
PharmaGuard AI — Official CPIC API Client
Connects to https://api.cpicpgx.org (free, public, no key required)
Covers 34 genes and 164+ drugs — the full CPIC guideline database.

Key endpoints used:
  /v1/diplotype       — Diplotype → Phenotype (pre-joined view)
  /v1/recommendation  — Drug + Phenotype → Clinical recommendation
  /v1/pair            — All CPIC gene-drug pairs
  /v1/allele          — Star allele definitions + function assignments
  /v1/drug            — All CPIC drugs

All results are cached in memory to avoid redundant API calls.
Falls back gracefully to hardcoded data if the API is unreachable.
"""
import json
import time
from typing import Dict, List, Optional, Any
from urllib.parse import quote

try:
    import httpx
    HTTP_CLIENT = True
except ImportError:
    HTTP_CLIENT = False

try:
    import requests as req_lib
    REQUESTS_LIB = True
except ImportError:
    REQUESTS_LIB = False

CPIC_BASE = "https://api.cpicpgx.org/v1"
CACHE: Dict[str, Any] = {}
CACHE_TTL = 3600  # 1 hour cache


def _get(url: str, params: dict = None, timeout: int = 10) -> Optional[Any]:
    """Make a GET request to the CPIC API with caching."""
    cache_key = url + (json.dumps(params, sort_keys=True) if params else "")
    cached = CACHE.get(cache_key)
    if cached and (time.time() - cached["ts"]) < CACHE_TTL:
        return cached["data"]

    try:
        if HTTP_CLIENT:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        elif REQUESTS_LIB:
            resp = req_lib.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
        else:
            return None

        CACHE[cache_key] = {"data": data, "ts": time.time()}
        return data
    except Exception as e:
        print(f"[CPIC API] Request failed: {url} — {e}")
        return None


def cpic_diplotype_to_phenotype(gene: str, diplotype: str) -> Optional[Dict]:
 
    url = f"{CPIC_BASE}/diplotype"
    params = {
        "genesymbol": f"eq.{gene}",
        "diplotype": f"eq.{diplotype}",
    }
    data = _get(url, params)
    if not data and "/" in diplotype:
        a1, a2 = diplotype.split("/", 1)
        params["diplotype"] = f"eq.{a2}/{a1}"
        data = _get(url, params)

    if data and len(data) > 0:
        row = data[0]
        return {
            "gene": row.get("genesymbol", gene),
            "diplotype": row.get("diplotype", diplotype),
            "phenotype": row.get("generesult", ""),
            "activity_score": row.get("activityscore"),
            "ehr_priority": row.get("ehrpriority", ""),
            "consultation_text": row.get("consultationtext", ""),
            "allele1_function": row.get("diplotype_function1", ""),
            "allele2_function": row.get("diplotype_function2", ""),
        }
    return None


def cpic_get_recommendation(drug_name: str, gene: str, phenotype: str, population: str = "general") -> Optional[Dict]:
    """
    Query the CPIC recommendation table.
    Uses the lookupkey format: {"GENE": "Phenotype"}
    
    Returns the official CPIC recommendation including:
    - drugrecommendation (prescribing action)
    - implications (clinical impact)
    - classification (strength of recommendation)
    - comments
    """
    # First, get the drug's RxNorm ID from CPIC
    drug_info = cpic_get_drug(drug_name)
    if not drug_info:
        return None

    drugid = drug_info.get("drugid")
    if not drugid:
        return None

    # Build lookupkey — CPIC format: {"GENE": "Phenotype Text"}
    lookupkey_json = json.dumps({gene: phenotype})

    url = f"{CPIC_BASE}/recommendation"
    params = {
        "drugid": f"eq.{drugid}",
        f"lookupkey": f"cs.{lookupkey_json}",
    }

    # Try general population first, then without population filter
    data = _get(url, params)

    if data and len(data) > 0:
        # Pick the best match (prefer general population or first result)
        best = None
        for row in data:
            pop = (row.get("population") or "").lower()
            if pop in ("general", ""):
                best = row
                break
        if not best:
            best = data[0]

        return _normalize_recommendation(best, gene, drug_name)

    # Try without lookupkey containment (broader search)
    params2 = {"drugid": f"eq.{drugid}"}
    data2 = _get(url, params2)
    if data2:
        # Search through results for matching phenotype
        for row in data2:
            lk = row.get("lookupkey", {})
            if isinstance(lk, dict) and lk.get(gene, "").lower() == phenotype.lower():
                return _normalize_recommendation(row, gene, drug_name)

    return None


def _normalize_recommendation(row: Dict, gene: str, drug: str) -> Dict:
    """Normalize a CPIC API recommendation row into our standard format."""
    implications = row.get("implications", {})
    implication_text = implications.get(gene, "") if isinstance(implications, dict) else str(implications)
    
    drug_rec = row.get("drugrecommendation", "")
    classification = row.get("classification", {})
    strength = ""
    if isinstance(classification, dict):
        strength = classification.get("term", "")
    
    comments = row.get("comments", "") or ""
    
    # Derive risk label from the recommendation text
    risk_label, severity, urgency = _classify_recommendation(drug_rec, implication_text, strength)

    return {
        "risk_assessment": {
            "risk_label": risk_label,
            "confidence_score": 0.92,
            "severity": severity,
        },
        "clinical_recommendation": {
            "dosing_recommendation": drug_rec,
            "alternative_drugs": _extract_alternatives(drug_rec + " " + comments),
            "monitoring_parameters": _extract_monitoring(drug_rec + " " + comments),
            "cpic_guideline_reference": row.get("guideline", {}).get("name", "") if isinstance(row.get("guideline"), dict) else "",
            "urgency": urgency,
        },
        "cpic_metadata": {
            "implication": implication_text,
            "classification_strength": strength,
            "comments": comments,
            "population": row.get("population", "general"),
            "version": row.get("version"),
            "guideline_url": row.get("guideline", {}).get("url", "") if isinstance(row.get("guideline"), dict) else "",
        },
    }


def _classify_recommendation(rec_text: str, implication: str, strength: str) -> tuple:
    """
    Derive risk_label, severity, and urgency from CPIC recommendation text.
    Uses NLP-style keyword matching on official CPIC language.
    """
    text = (rec_text + " " + implication).lower()

    # TOXIC patterns
    if any(kw in text for kw in [
        "avoid", "contraindicated", "do not use", "not recommended",
        "fatal", "life-threatening", "severe toxicity", "significantly increased risk",
        "extremely high risk", "potentially fatal", "serious adverse",
    ]):
        if any(kw in text for kw in ["fatal", "life-threatening", "extremely", "contraindicated"]):
            return ("Toxic", "critical", "emergent")
        return ("Toxic", "high", "urgent")

    # INEFFECTIVE patterns (prodrug activation failure)
    if any(kw in text for kw in [
        "no therapeutic effect", "lack of efficacy", "reduced activation",
        "no response", "treatment failure", "insufficient response",
        "significantly reduced", "markedly reduced",
    ]):
        if "significantly" in text or "markedly" in text or "no " in text:
            return ("Ineffective", "high", "urgent")
        return ("Ineffective", "moderate", "soon")

    # ADJUST DOSAGE patterns
    if any(kw in text for kw in [
        "reduce dose", "lower dose", "decrease dose", "dose reduction",
        "increase dose", "higher dose", "alternative drug", "alternative agent",
        "consider an alternative", "select alternative", "use with caution",
        "increased risk", "moderate risk", "dose adjust", "reduced dose",
        "start with", "initiate at", "max dose", "maximum dose",
        "limit dose",
    ]):
        if any(kw in text for kw in ["50%", "80%", "significantly"]):
            return ("Adjust Dosage", "high", "urgent")
        return ("Adjust Dosage", "moderate", "soon")

    # SAFE — standard therapy
    if any(kw in text for kw in [
        "standard", "no change", "normal", "use recommended",
        "initiate therapy", "no dose adjustment", "label-recommended",
        "no actionable", "no significant",
    ]):
        return ("Safe", "none", "routine")

    # Default: if there's a recommendation, it's at least "Adjust"
    if rec_text.strip():
        return ("Adjust Dosage", "low", "routine")

    return ("Unknown", "unknown", "routine")


def _extract_alternatives(text: str) -> List[str]:
    """Extract alternative drug suggestions from CPIC recommendation text."""
    alternatives = []
    lower = text.lower()
    # Common alternative drug patterns in CPIC guidelines
    alt_markers = ["alternative:", "consider", "instead use", "switch to", "replace with"]
    for marker in alt_markers:
        if marker in lower:
            idx = lower.index(marker) + len(marker)
            snippet = text[idx:idx+200]
            # Extract drug-like words (capitalized, common drug suffixes)
            import re
            drugs = re.findall(r'\b[A-Za-z]+(?:ine|ol|pin|tan|pril|arin|ide|one|ate|cin|lin|pam)\b', snippet, re.IGNORECASE)
            alternatives.extend([d.capitalize() for d in drugs[:5]])
    return list(set(alternatives))[:5]


def _extract_monitoring(text: str) -> List[str]:
    """Extract monitoring parameters from CPIC recommendation text."""
    monitors = []
    lower = text.lower()
    monitor_terms = {
        "inr": "INR monitoring", "cbc": "Complete blood count",
        "liver function": "Liver function tests", "lft": "Liver function tests",
        "ck level": "CK levels", "creatine kinase": "CK levels",
        "platelet": "Platelet function", "bleeding": "Monitor for bleeding",
        "renal": "Renal function", "therapeutic drug monitoring": "TDM",
        "ecg": "ECG monitoring", "qtc": "QTc monitoring",
        "blood pressure": "Blood pressure", "serum level": "Serum drug levels",
        "toxicity": "Monitor for toxicity signs",
    }
    for keyword, label in monitor_terms.items():
        if keyword in lower:
            monitors.append(label)
    return list(set(monitors))[:5]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. DRUG INFO LOOKUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cpic_get_drug(drug_name: str) -> Optional[Dict]:
    """
    Look up a drug in CPIC by name. Returns drug info including drugid.
    """
    url = f"{CPIC_BASE}/drug"
    params = {"name": f"ilike.*{drug_name}*"}
    data = _get(url, params)
    if data and len(data) > 0:
        row = data[0]
        return {
            "drugid": row.get("drugid", ""),
            "name": row.get("name", drug_name),
            "rxnorm": row.get("rxnormid"),
            "atc": row.get("atcid"),
            "guideline_url": row.get("guidelineurl", ""),
        }
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. GENE-DRUG PAIRS (full catalog)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cpic_get_all_pairs(level: str = None) -> List[Dict]:
    """
    Get all CPIC gene-drug pairs. Optionally filter by level (A, B, C, D).
    Level A = most actionable, Level D = least evidence.
    """
    url = f"{CPIC_BASE}/pair"
    params = {"select": "genesymbol,drugname,cpiclevel,cpicstatus,pgkbcalevel,pgxtesting,guidelineid"}
    if level:
        params["cpiclevel"] = f"eq.{level}"
    data = _get(url, params)
    if data:
        return [
            {
                "gene": row.get("genesymbol", ""),
                "drug": row.get("drugname", ""),
                "cpic_level": row.get("cpiclevel", ""),
                "status": row.get("cpicstatus", ""),
                "evidence_level": row.get("pgkbcalevel", ""),
                "fda_pgx_testing": row.get("pgxtesting", ""),
            }
            for row in data
        ]
    return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. ALLELE FUNCTION LOOKUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cpic_get_allele_function(gene: str, allele: str) -> Optional[Dict]:
    """
    Look up the function status of a specific allele.
    Example: cpic_get_allele_function("CYP2D6", "*4")
    """
    url = f"{CPIC_BASE}/allele"
    params = {
        "genesymbol": f"eq.{gene}",
        "name": f"eq.{allele}",
    }
    data = _get(url, params)
    if data and len(data) > 0:
        row = data[0]
        return {
            "gene": gene,
            "allele": allele,
            "function": row.get("functionalstatus", ""),
            "activity_value": row.get("activityvalue"),
            "clinvar": row.get("clinvar", ""),
        }
    return None


def cpic_get_gene_alleles(gene: str) -> List[Dict]:
    """Get all known alleles for a gene from CPIC."""
    url = f"{CPIC_BASE}/allele"
    params = {
        "genesymbol": f"eq.{gene}",
        "select": "name,functionalstatus,activityvalue",
    }
    data = _get(url, params)
    if data:
        return [
            {
                "allele": row.get("name", ""),
                "function": row.get("functionalstatus", ""),
                "activity": row.get("activityvalue"),
            }
            for row in data
        ]
    return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. HIGH-LEVEL FUNCTIONS (used by risk_engine)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cpic_lookup_full(drug: str, gene: str, diplotype: str) -> Optional[Dict]:
    """
    Full CPIC lookup: diplotype → phenotype → recommendation.
    This is the main entry point used by the risk engine.
    
    Returns a dict with risk_assessment + clinical_recommendation
    in our standard format, or None if CPIC has no data.
    """
    # Step 1: Get phenotype from diplotype
    dip_result = cpic_diplotype_to_phenotype(gene, diplotype)
    phenotype = None
    if dip_result:
        phenotype = dip_result.get("phenotype")

    if not phenotype:
        return None

    # Step 2: Get recommendation for drug + phenotype
    rec = cpic_get_recommendation(drug, gene, phenotype)
    if rec:
        # Enrich with diplotype info
        rec["cpic_phenotype"] = phenotype
        rec["cpic_diplotype_data"] = dip_result
        return rec

    return None


def cpic_find_gene_for_drug(drug: str) -> Optional[str]:
    """
    Find which gene(s) CPIC associates with a drug.
    Returns the primary gene, or None.
    """
    pairs = cpic_get_all_pairs()
    drug_lower = drug.lower()
    matches = [p for p in pairs if p["drug"].lower() == drug_lower and p["cpic_level"] in ("A", "B")]
    if matches:
        return matches[0]["gene"]
    # Try broader match
    matches = [p for p in pairs if drug_lower in p["drug"].lower()]
    if matches:
        return matches[0]["gene"]
    return None


def is_cpic_available() -> bool:
    """Quick check if the CPIC API is reachable."""
    try:
        result = _get(f"{CPIC_BASE}/drug", {"limit": "1"}, timeout=5)
        return result is not None and len(result) > 0
    except:
        return False
