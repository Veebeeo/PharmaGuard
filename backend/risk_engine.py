"""
PharmaGuard AI — Risk Engine (Knowledge Base)
All pharmacogenomic logic: variants, drug-gene maps, diplotype→phenotype,
CPIC-aligned risk matrix, clinical recommendations.
"""
from typing import Dict, Optional

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. KNOWN PHARMACOGENOMIC VARIANTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KNOWN_VARIANTS: Dict[str, Dict] = {
    # CYP2D6
    "rs3892097":  {"gene": "CYP2D6",  "star": "*4",  "effect": "no_function",       "desc": "Splicing defect; most common null allele in Europeans"},
    "rs5030655":  {"gene": "CYP2D6",  "star": "*6",  "effect": "no_function",       "desc": "Frameshift deletion"},
    "rs1065852":  {"gene": "CYP2D6",  "star": "*10", "effect": "decreased_function", "desc": "Pro34Ser; common in Asians"},
    "rs16947":    {"gene": "CYP2D6",  "star": "*2",  "effect": "normal",            "desc": "Normal function"},
    "rs1135840":  {"gene": "CYP2D6",  "star": "*2B", "effect": "normal",            "desc": "Ser486Thr; normal function"},
    "rs28371725": {"gene": "CYP2D6",  "star": "*41", "effect": "decreased_function", "desc": "Reduced splicing"},
    "rs5030656":  {"gene": "CYP2D6",  "star": "*9",  "effect": "decreased_function", "desc": "Lys281del"},
    "rs28371706": {"gene": "CYP2D6",  "star": "*17", "effect": "decreased_function", "desc": "Thr107Ile; common in Africans"},
    # CYP2C19
    "rs4244285":  {"gene": "CYP2C19", "star": "*2",  "effect": "no_function",       "desc": "Splicing defect; most common LOF"},
    "rs4986893":  {"gene": "CYP2C19", "star": "*3",  "effect": "no_function",       "desc": "Premature stop codon"},
    "rs12248560": {"gene": "CYP2C19", "star": "*17", "effect": "increased_function", "desc": "Enhanced promoter; ultra-rapid"},
    "rs28399504": {"gene": "CYP2C19", "star": "*4",  "effect": "no_function",       "desc": "Rare LOF allele"},
    "rs56337013": {"gene": "CYP2C19", "star": "*5",  "effect": "no_function",       "desc": "Arg433Trp"},
    "rs72552267": {"gene": "CYP2C19", "star": "*6",  "effect": "no_function",       "desc": "Arg132Gln"},
    "rs72558186": {"gene": "CYP2C19", "star": "*7",  "effect": "no_function",       "desc": "Splicing defect"},
    "rs41291556": {"gene": "CYP2C19", "star": "*8",  "effect": "no_function",       "desc": "Trp120Arg"},
    # CYP2C9
    "rs1799853":  {"gene": "CYP2C9",  "star": "*2",  "effect": "decreased_function", "desc": "Arg144Cys; ~30% reduced warfarin metabolism"},
    "rs1057910":  {"gene": "CYP2C9",  "star": "*3",  "effect": "decreased_function", "desc": "Ile359Leu; ~80% reduced warfarin metabolism"},
    "rs28371686": {"gene": "CYP2C9",  "star": "*5",  "effect": "decreased_function", "desc": "Asp360Glu"},
    "rs9332131":  {"gene": "CYP2C9",  "star": "*6",  "effect": "no_function",       "desc": "Frameshift; LOF"},
    "rs7900194":  {"gene": "CYP2C9",  "star": "*8",  "effect": "decreased_function", "desc": "Arg150His; common in African Americans"},
    "rs2256871":  {"gene": "CYP2C9",  "star": "*9",  "effect": "decreased_function", "desc": "His251Arg"},
    "rs28371685": {"gene": "CYP2C9",  "star": "*11", "effect": "decreased_function", "desc": "Arg335Trp"},
    # SLCO1B1
    "rs4149056":  {"gene": "SLCO1B1", "star": "*5",  "effect": "decreased_function", "desc": "Val174Ala; impaired statin uptake"},
    "rs2306283":  {"gene": "SLCO1B1", "star": "*1B", "effect": "normal",            "desc": "Asn130Asp; normal function"},
    "rs4149015":  {"gene": "SLCO1B1", "star": "*1A", "effect": "normal",            "desc": "Reference allele"},
    "rs11045819": {"gene": "SLCO1B1", "star": "*14", "effect": "decreased_function", "desc": "Pro155Thr"},
    # TPMT
    "rs1800460":  {"gene": "TPMT",    "star": "*3B", "effect": "no_function",       "desc": "Ala154Thr; non-functional"},
    "rs1142345":  {"gene": "TPMT",    "star": "*3C", "effect": "no_function",       "desc": "Tyr240Cys; most common globally"},
    "rs1800462":  {"gene": "TPMT",    "star": "*2",  "effect": "no_function",       "desc": "Ala80Pro; non-functional"},
    "rs1800584":  {"gene": "TPMT",    "star": "*4",  "effect": "no_function",       "desc": "Rare non-functional"},
    # DPYD
    "rs3918290":  {"gene": "DPYD",    "star": "*2A", "effect": "no_function",       "desc": "IVS14+1G>A; exon 14 skipping"},
    "rs67376798": {"gene": "DPYD",    "star": "*13", "effect": "decreased_function", "desc": "Ile560Ser; ~50% reduced DPD"},
    "rs55886062": {"gene": "DPYD",    "star": "c.1679T>G",         "effect": "no_function",       "desc": "Complete DPD loss"},
    "rs75017182": {"gene": "DPYD",    "star": "c.1129-5923C>G",     "effect": "decreased_function", "desc": "HapB3 intronic"},
    "rs56038477": {"gene": "DPYD",    "star": "c.1129-5923C>G_tag", "effect": "decreased_function", "desc": "HapB3 tag SNP"},
}

TARGET_GENES = {"CYP2D6", "CYP2C19", "CYP2C9", "SLCO1B1", "TPMT", "DPYD"}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. DRUG → GENE MAPPING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DRUG_GENE_MAP: Dict[str, Dict] = {
    "CODEINE":      {"gene": "CYP2D6",  "pathway": "CYP2D6 O-demethylates codeine to morphine. URMs produce excess morphine; PMs get no effect.", "drug_class": "Opioid analgesic"},
    "WARFARIN":     {"gene": "CYP2C9",  "pathway": "CYP2C9 metabolizes S-warfarin. Reduced function → elevated levels → bleeding risk.", "drug_class": "Anticoagulant"},
    "CLOPIDOGREL":  {"gene": "CYP2C19", "pathway": "CYP2C19 bioactivates the prodrug. PMs cannot activate → treatment failure.", "drug_class": "Antiplatelet"},
    "SIMVASTATIN":  {"gene": "SLCO1B1", "pathway": "SLCO1B1 mediates hepatic uptake. Decreased function → elevated plasma → myopathy.", "drug_class": "Statin"},
    "AZATHIOPRINE": {"gene": "TPMT",    "pathway": "TPMT methylates thiopurines. Deficiency → toxic TGN accumulation → myelosuppression.", "drug_class": "Immunosuppressant"},
    "FLUOROURACIL": {"gene": "DPYD",    "pathway": "DPD catabolizes >80% of 5-FU. Deficiency → drug accumulation → fatal toxicity.", "drug_class": "Antineoplastic"},
}

DRUG_ALIASES: Dict[str, str] = {
    "5-FU": "FLUOROURACIL", "5-FLUOROURACIL": "FLUOROURACIL", "CAPECITABINE": "FLUOROURACIL",
    "6-MP": "AZATHIOPRINE", "MERCAPTOPURINE": "AZATHIOPRINE",
    "PLAVIX": "CLOPIDOGREL", "COUMADIN": "WARFARIN", "ZOCOR": "SIMVASTATIN",
}

SUPPORTED_DRUGS = list(DRUG_GENE_MAP.keys())

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. ACTIVITY SCORES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GAIN_OF_FUNCTION = {"*17"}


def get_allele_activity(star: str, gene: str) -> float:
    """
    Gene-specific activity scores. Each gene has its own mapping because
    the same star number can mean different things in different genes.
    """
    if gene == "CYP2D6":
        return {
            "*1": 1.0, "*2": 1.0, "*2B": 1.0, "*4": 0.0, "*6": 0.0,
            "*9": 0.5, "*10": 0.25, "*17": 0.5, "*41": 0.5,
        }.get(star, 1.0)

    if gene == "CYP2C19":
        return {
            "*1": 1.0, "*2": 0.0, "*3": 0.0, "*4": 0.0, "*5": 0.0,
            "*6": 0.0, "*7": 0.0, "*8": 0.0, "*17": 1.5,
        }.get(star, 1.0)

    if gene == "CYP2C9":
        return {
            "*1": 1.0, "*2": 0.5, "*3": 0.25, "*5": 0.0, "*6": 0.0,
            "*8": 0.5, "*9": 0.5, "*11": 0.5,
        }.get(star, 1.0)

    if gene == "SLCO1B1":
        return {
            "*1": 1.0, "*1A": 1.0, "*1B": 1.0, "*5": 0.0, "*14": 0.5,
        }.get(star, 1.0)

    if gene == "TPMT":
        return {
            "*1": 1.0, "*2": 0.0, "*3B": 0.0, "*3C": 0.0, "*4": 0.0,
        }.get(star, 1.0)

    if gene == "DPYD":
        return {
            "*1": 1.0, "*2A": 0.0, "*13": 0.5,
            "c.1679T>G": 0.0, "c.1129-5923C>G": 0.5, "c.1129-5923C>G_tag": 0.5,
        }.get(star, 1.0)

    # Fallback for unknown genes
    return 1.0


def determine_phenotype(allele1: str, allele2: str, gene: str) -> str:
    s1 = get_allele_activity(allele1, gene)
    s2 = get_allele_activity(allele2, gene)
    total = s1 + s2

    if gene in ("TPMT", "DPYD"):
        if total == 0: return "PM"
        elif total <= 1.0: return "IM"
        else: return "NM"

    if gene == "SLCO1B1":
        if total == 0: return "PM"
        elif total < 2.0: return "IM"
        else: return "NM"

    # CYP genes
    if total == 0: return "PM"
    elif total < 1.0: return "IM"
    elif total <= 2.0:
        if (allele1 in GAIN_OF_FUNCTION or allele2 in GAIN_OF_FUNCTION) and gene == "CYP2C19":
            if total >= 2.5: return "RM"
        return "NM"
    elif total <= 2.5: return "RM"
    else: return "URM"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. RISK MATRIX
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RISK_MATRIX = {
    "CODEINE": {
        "URM": {"risk_label": "Toxic",       "severity": "critical", "confidence": 0.95},
        "RM":  {"risk_label": "Toxic",       "severity": "high",     "confidence": 0.88},
        "NM":  {"risk_label": "Safe",        "severity": "none",     "confidence": 0.92},
        "IM":  {"risk_label": "Ineffective", "severity": "moderate", "confidence": 0.85},
        "PM":  {"risk_label": "Ineffective", "severity": "high",     "confidence": 0.95},
    },
    "WARFARIN": {
        "URM": {"risk_label": "Adjust Dosage", "severity": "low",      "confidence": 0.80},
        "RM":  {"risk_label": "Adjust Dosage", "severity": "low",      "confidence": 0.80},
        "NM":  {"risk_label": "Safe",          "severity": "none",     "confidence": 0.90},
        "IM":  {"risk_label": "Adjust Dosage", "severity": "high",     "confidence": 0.92},
        "PM":  {"risk_label": "Toxic",         "severity": "critical", "confidence": 0.95},
    },
    "CLOPIDOGREL": {
        "URM": {"risk_label": "Safe",        "severity": "none",     "confidence": 0.85},
        "RM":  {"risk_label": "Safe",        "severity": "none",     "confidence": 0.88},
        "NM":  {"risk_label": "Safe",        "severity": "none",     "confidence": 0.92},
        "IM":  {"risk_label": "Adjust Dosage","severity": "moderate", "confidence": 0.88},
        "PM":  {"risk_label": "Ineffective", "severity": "critical", "confidence": 0.95},
    },
    "SIMVASTATIN": {
        "URM": {"risk_label": "Safe",          "severity": "none",     "confidence": 0.80},
        "RM":  {"risk_label": "Safe",          "severity": "none",     "confidence": 0.85},
        "NM":  {"risk_label": "Safe",          "severity": "none",     "confidence": 0.92},
        "IM":  {"risk_label": "Adjust Dosage", "severity": "moderate", "confidence": 0.88},
        "PM":  {"risk_label": "Toxic",         "severity": "high",     "confidence": 0.92},
    },
    "AZATHIOPRINE": {
        "URM": {"risk_label": "Safe",          "severity": "none",     "confidence": 0.80},
        "RM":  {"risk_label": "Safe",          "severity": "none",     "confidence": 0.85},
        "NM":  {"risk_label": "Safe",          "severity": "none",     "confidence": 0.92},
        "IM":  {"risk_label": "Adjust Dosage", "severity": "high",     "confidence": 0.90},
        "PM":  {"risk_label": "Toxic",         "severity": "critical", "confidence": 0.97},
    },
    "FLUOROURACIL": {
        "URM": {"risk_label": "Safe",          "severity": "none",     "confidence": 0.80},
        "RM":  {"risk_label": "Safe",          "severity": "none",     "confidence": 0.85},
        "NM":  {"risk_label": "Safe",          "severity": "none",     "confidence": 0.92},
        "IM":  {"risk_label": "Adjust Dosage", "severity": "high",     "confidence": 0.90},
        "PM":  {"risk_label": "Toxic",         "severity": "critical", "confidence": 0.97},
    },
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. CLINICAL RECOMMENDATIONS (CPIC)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CLINICAL_RECS = {
    "CODEINE": {
        "URM": {"dosing": "AVOID codeine. Ultra-rapid CYP2D6 metabolism → excess morphine → respiratory depression risk.", "alternatives": ["Morphine (with caution)", "Non-opioid analgesics (NSAIDs, acetaminophen)"], "monitoring": ["Respiratory rate", "Sedation level", "O2 saturation"], "cpic_ref": "CPIC Guideline for CYP2D6 and Codeine Therapy (2019)", "urgency": "emergent"},
        "RM":  {"dosing": "AVOID codeine. Rapid metabolism may cause excess morphine.", "alternatives": ["Morphine (dose-adjusted)", "Non-opioid analgesics"], "monitoring": ["Respiratory rate", "Sedation"], "cpic_ref": "CPIC Guideline for CYP2D6 and Codeine Therapy (2019)", "urgency": "urgent"},
        "NM":  {"dosing": "Use codeine at standard dose. Normal CYP2D6 metabolism.", "alternatives": [], "monitoring": ["Pain assessment", "Adverse effects"], "cpic_ref": "CPIC Guideline for CYP2D6 and Codeine Therapy (2019)", "urgency": "routine"},
        "IM":  {"dosing": "Reduced efficacy expected. Consider alternative analgesic.", "alternatives": ["Morphine", "Hydromorphone", "Non-opioid analgesics"], "monitoring": ["Pain control adequacy"], "cpic_ref": "CPIC Guideline for CYP2D6 and Codeine Therapy (2019)", "urgency": "soon"},
        "PM":  {"dosing": "AVOID codeine. PMs cannot convert codeine to morphine — no analgesic effect.", "alternatives": ["Morphine", "Hydromorphone", "Non-opioid analgesics"], "monitoring": ["Pain control with alternative"], "cpic_ref": "CPIC Guideline for CYP2D6 and Codeine Therapy (2019)", "urgency": "urgent"},
    },
    "WARFARIN": {
        "NM":  {"dosing": "Standard dose (5 mg/day). Adjust per INR.", "alternatives": [], "monitoring": ["INR (2.0–3.0)", "Bleeding signs"], "cpic_ref": "CPIC Guideline for Warfarin Dosing (2017)", "urgency": "routine"},
        "IM":  {"dosing": "Reduce dose 25–50%. Intermediate CYP2C9 metabolism.", "alternatives": ["Apixaban", "Rivaroxaban"], "monitoring": ["INR (frequent)", "Bleeding", "Hemoglobin"], "cpic_ref": "CPIC Guideline for Warfarin Dosing (2017)", "urgency": "soon"},
        "PM":  {"dosing": "Reduce dose 50–80%. HIGH BLEEDING RISK. Consider DOAC.", "alternatives": ["Apixaban", "Rivaroxaban", "Edoxaban"], "monitoring": ["INR 2–3x/week", "CBC", "Bleeding signs"], "cpic_ref": "CPIC Guideline for Warfarin Dosing (2017)", "urgency": "urgent"},
        "RM":  {"dosing": "May need higher dose. INR-guided titration.", "alternatives": [], "monitoring": ["INR"], "cpic_ref": "CPIC Guideline for Warfarin Dosing (2017)", "urgency": "routine"},
        "URM": {"dosing": "May need higher dose. INR-guided titration.", "alternatives": [], "monitoring": ["INR"], "cpic_ref": "CPIC Guideline for Warfarin Dosing (2017)", "urgency": "routine"},
    },
    "CLOPIDOGREL": {
        "NM":  {"dosing": "Standard dose (75 mg/day). Normal bioactivation.", "alternatives": [], "monitoring": ["Platelet function", "CV events"], "cpic_ref": "CPIC Guideline for CYP2C19 and Clopidogrel (2022)", "urgency": "routine"},
        "RM":  {"dosing": "Standard dose. Adequate activation.", "alternatives": [], "monitoring": ["CV monitoring"], "cpic_ref": "CPIC Guideline for CYP2C19 and Clopidogrel (2022)", "urgency": "routine"},
        "URM": {"dosing": "Standard dose. Slightly increased bleeding risk possible.", "alternatives": [], "monitoring": ["Bleeding signs"], "cpic_ref": "CPIC Guideline for CYP2C19 and Clopidogrel (2022)", "urgency": "routine"},
        "IM":  {"dosing": "Reduced activation. Consider alternative or double dose with monitoring.", "alternatives": ["Prasugrel", "Ticagrelor"], "monitoring": ["Platelet function", "CV events"], "cpic_ref": "CPIC Guideline for CYP2C19 and Clopidogrel (2022)", "urgency": "soon"},
        "PM":  {"dosing": "AVOID clopidogrel. Cannot activate prodrug — HIGH treatment failure risk.", "alternatives": ["Prasugrel", "Ticagrelor"], "monitoring": ["Platelet function", "Stent thrombosis"], "cpic_ref": "CPIC Guideline for CYP2C19 and Clopidogrel (2022)", "urgency": "emergent"},
    },
    "SIMVASTATIN": {
        "NM":  {"dosing": "Standard dose. Normal SLCO1B1 function.", "alternatives": [], "monitoring": ["LDL-C", "LFTs", "Muscle symptoms"], "cpic_ref": "CPIC Guideline for SLCO1B1 and Statins (2022)", "urgency": "routine"},
        "RM":  {"dosing": "Standard dose.", "alternatives": [], "monitoring": ["LDL-C", "Muscle symptoms"], "cpic_ref": "CPIC Guideline for SLCO1B1 and Statins (2022)", "urgency": "routine"},
        "URM": {"dosing": "Standard dose.", "alternatives": [], "monitoring": ["LDL-C"], "cpic_ref": "CPIC Guideline for SLCO1B1 and Statins (2022)", "urgency": "routine"},
        "IM":  {"dosing": "Limit to ≤20 mg/day. Increased myopathy risk.", "alternatives": ["Pravastatin", "Rosuvastatin"], "monitoring": ["CK levels", "Muscle pain", "LDL-C"], "cpic_ref": "CPIC Guideline for SLCO1B1 and Statins (2022)", "urgency": "soon"},
        "PM":  {"dosing": "AVOID simvastatin. High myopathy/rhabdomyolysis risk.", "alternatives": ["Pravastatin", "Rosuvastatin", "Fluvastatin"], "monitoring": ["CK", "Renal function", "Muscle symptoms"], "cpic_ref": "CPIC Guideline for SLCO1B1 and Statins (2022)", "urgency": "urgent"},
    },
    "AZATHIOPRINE": {
        "NM":  {"dosing": "Standard dose (2–3 mg/kg/day). Normal TPMT.", "alternatives": [], "monitoring": ["CBC", "LFTs"], "cpic_ref": "CPIC Guideline for TPMT and Thiopurines (2018)", "urgency": "routine"},
        "RM":  {"dosing": "Standard dose.", "alternatives": [], "monitoring": ["CBC", "LFTs"], "cpic_ref": "CPIC Guideline for TPMT and Thiopurines (2018)", "urgency": "routine"},
        "URM": {"dosing": "May need higher dose. Monitor response.", "alternatives": [], "monitoring": ["TGN levels", "CBC"], "cpic_ref": "CPIC Guideline for TPMT and Thiopurines (2018)", "urgency": "routine"},
        "IM":  {"dosing": "Reduce dose 30–80%. Start 0.5–1.5 mg/kg/day.", "alternatives": ["Mycophenolate mofetil"], "monitoring": ["CBC weekly then biweekly", "LFTs", "TGN levels"], "cpic_ref": "CPIC Guideline for TPMT and Thiopurines (2018)", "urgency": "urgent"},
        "PM":  {"dosing": "AVOID or reduce 90%. LIFE-THREATENING myelosuppression risk.", "alternatives": ["Mycophenolate mofetil"], "monitoring": ["CBC 2–3x/week", "ANC", "TGN levels"], "cpic_ref": "CPIC Guideline for TPMT and Thiopurines (2018)", "urgency": "emergent"},
    },
    "FLUOROURACIL": {
        "NM":  {"dosing": "Standard dose. Normal DPD activity.", "alternatives": [], "monitoring": ["CBC", "Mucositis", "Hand-foot syndrome"], "cpic_ref": "CPIC Guideline for DPYD and Fluoropyrimidines (2017)", "urgency": "routine"},
        "RM":  {"dosing": "Standard dose.", "alternatives": [], "monitoring": ["CBC", "Toxicity"], "cpic_ref": "CPIC Guideline for DPYD and Fluoropyrimidines (2017)", "urgency": "routine"},
        "URM": {"dosing": "Standard dose. May have reduced efficacy.", "alternatives": [], "monitoring": ["Treatment response", "CBC"], "cpic_ref": "CPIC Guideline for DPYD and Fluoropyrimidines (2017)", "urgency": "routine"},
        "IM":  {"dosing": "Reduce dose 25–50%. Intermediate DPD activity.", "alternatives": ["Dose-reduced capecitabine"], "monitoring": ["CBC 2x/week", "Mucositis", "Diarrhea", "Neurotoxicity"], "cpic_ref": "CPIC Guideline for DPYD and Fluoropyrimidines (2017)", "urgency": "urgent"},
        "PM":  {"dosing": "AVOID all fluoropyrimidines. Complete DPD deficiency → FATAL toxicity.", "alternatives": ["Non-fluoropyrimidine chemo (consult oncology)"], "monitoring": ["If given: emergent CBC, renal, electrolytes, ICU"], "cpic_ref": "CPIC Guideline for DPYD and Fluoropyrimidines (2017)", "urgency": "emergent"},
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. MAIN RISK ASSESSMENT FUNCTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def resolve_drug(drug: str) -> str:
    d = drug.upper().strip()
    return DRUG_ALIASES.get(d, d)


def get_drug_gene_info(drug: str) -> Dict:
    """Get drug→gene info. Tries hardcoded first (fast), then CPIC API for unknown drugs."""
    drug_upper = resolve_drug(drug)
    # Fast path: check hardcoded
    if drug_upper in DRUG_GENE_MAP:
        return DRUG_GENE_MAP[drug_upper]
    # Try Supabase
    from supabase_client import db_get_drug_gene
    db_result = db_get_drug_gene(drug_upper)
    if db_result:
        return db_result
    # Try official CPIC API (covers 164+ drugs)
    try:
        from cpic_api import cpic_find_gene_for_drug, cpic_get_drug
        gene = cpic_find_gene_for_drug(drug_upper)
        if gene:
            drug_info = cpic_get_drug(drug_upper) or {}
            return {
                "gene": gene,
                "pathway": f"CPIC Level A/B gene-drug pair",
                "drug_class": drug_info.get("atc", ""),
            }
    except Exception as e:
        print(f"[CPIC API] Gene lookup failed for {drug_upper}: {e}")
    return {}


def get_allele_activity_db(star: str, gene: str) -> Optional[float]:
    """Try Supabase for activity score, return None if unavailable."""
    from supabase_client import db_get_allele_activity
    return db_get_allele_activity(gene, star)


def assess_risk(drug: str, phenotype: str, gene: str = "", diplotype: str = "") -> dict:
    """
    Get risk assessment + clinical recommendation.
    Priority chain:
      1. Official CPIC API (api.cpicpgx.org — 34 genes, 164+ drugs)
      2. Supabase cpic_guidelines table (local DB)
      3. Hardcoded fallback (6 core drugs)
    """
    drug_upper = resolve_drug(drug)

    # ── 1. Try official CPIC API (covers ALL CPIC drugs) ──
    if gene and diplotype:
        try:
            from cpic_api import cpic_lookup_full
            cpic_result = cpic_lookup_full(drug_upper, gene, diplotype)
            if cpic_result and cpic_result.get("risk_assessment"):
                cpic_result["source"] = "cpic_api"
                return cpic_result
        except Exception as e:
            print(f"[CPIC API] Lookup failed for {drug_upper}: {e}")

    # ── 2. Try Supabase DB ──
    from supabase_client import db_get_cpic_guideline
    db_result = db_get_cpic_guideline(drug_upper, phenotype)
    if db_result:
        db_result["source"] = "supabase_db"
        return db_result

    # ── 3. Fallback to hardcoded ──
    if drug_upper not in RISK_MATRIX:
        return {
            "risk_assessment": {"risk_label": "Unknown", "confidence_score": 0.0, "severity": "low"},
            "clinical_recommendation": {
                "dosing_recommendation": f"No pharmacogenomic data for {drug}.",
                "alternative_drugs": [], "monitoring_parameters": [],
                "cpic_guideline_reference": "", "urgency": "routine",
            },
        }

    pheno = phenotype if phenotype in RISK_MATRIX[drug_upper] else "Unknown"
    if pheno == "Unknown":
        return {
            "risk_assessment": {"risk_label": "Unknown", "confidence_score": 0.5, "severity": "moderate"},
            "clinical_recommendation": {
                "dosing_recommendation": f"Phenotype undetermined. Use {drug} with standard monitoring.",
                "alternative_drugs": [], "monitoring_parameters": ["Standard monitoring"],
                "cpic_guideline_reference": "", "urgency": "soon",
            },
        }

    risk = RISK_MATRIX[drug_upper][pheno]
    rec = CLINICAL_RECS.get(drug_upper, {}).get(pheno, {})
    return {
        "risk_assessment": {
            "risk_label": risk["risk_label"],
            "confidence_score": risk["confidence"],
            "severity": risk["severity"],
        },
        "clinical_recommendation": {
            "dosing_recommendation": rec.get("dosing", "Follow standard prescribing info."),
            "alternative_drugs": rec.get("alternatives", []),
            "monitoring_parameters": rec.get("monitoring", []),
            "cpic_guideline_reference": rec.get("cpic_ref", ""),
            "urgency": rec.get("urgency", "routine"),
        },

        
    }

    if phenotype in ["PM", "Poor Metabolizer"]:
        return {
            "risk_assessment": {"risk_label": "Toxic", "confidence_score": 0.7, "severity": "high"},
            "clinical_recommendation": {
                "dosing_recommendation": f"Patient is a Poor Metabolizer for {gene}. High risk of abnormal {drug} metabolism. Consider alternatives or dose reduction.",
                "alternative_drugs": [], "monitoring_parameters": ["Close clinical monitoring"],
                "cpic_guideline_reference": "Inferred from phenotype", "urgency": "urgent",
            }
        }
    elif phenotype in ["IM", "Intermediate Metabolizer"]:
        return {
            "risk_assessment": {"risk_label": "Adjust Dosage", "confidence_score": 0.7, "severity": "moderate"},
            "clinical_recommendation": {
                "dosing_recommendation": f"Patient is an Intermediate Metabolizer for {gene}. May require dose adjustment for {drug}.",
                "alternative_drugs": [], "monitoring_parameters": ["Therapeutic response"],
                "cpic_guideline_reference": "Inferred from phenotype", "urgency": "soon",
            }
        }
    elif phenotype in ["URM", "RM", "Ultrarapid Metabolizer", "Rapid Metabolizer"]:
        return {
            "risk_assessment": {"risk_label": "Adjust Dosage", "confidence_score": 0.7, "severity": "moderate"},
            "clinical_recommendation": {
                "dosing_recommendation": f"Patient is a Rapid/Ultrarapid Metabolizer for {gene}. May experience lack of efficacy (if active drug) or toxicity (if prodrug).",
                "alternative_drugs": [], "monitoring_parameters": ["Therapeutic response"],
                "cpic_guideline_reference": "Inferred from phenotype", "urgency": "soon",
            }
        }
    elif phenotype in ["NM", "Normal Metabolizer"]:
        return {
            "risk_assessment": {"risk_label": "Safe", "confidence_score": 0.8, "severity": "none"},
            "clinical_recommendation": {
                "dosing_recommendation": f"Patient is a Normal Metabolizer for {gene}. Standard dosing for {drug} is appropriate.",
                "alternative_drugs": [], "monitoring_parameters": [],
                "cpic_guideline_reference": "Inferred from phenotype", "urgency": "routine",
            }
        }

    # ── 5. Ultimate Fallback ──
    return {
        "risk_assessment": {"risk_label": "Unknown", "confidence_score": 0.0, "severity": "low"},
        "clinical_recommendation": {
            "dosing_recommendation": f"No specific pharmacogenomic data found for {drug}.",
            "alternative_drugs": [], "monitoring_parameters": [],
            "cpic_guideline_reference": "", "urgency": "routine",
        },
    }

