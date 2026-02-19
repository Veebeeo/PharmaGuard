"""
PharmaGuard AI — Gemini LLM Service
Generates clinical explanations using Google Gemini API.
Builds structured prompts with patient variant data, risk predictions,
and requests explanations with biological mechanisms and citations.
"""
import os
import json
import traceback
from typing import Dict, List, Optional

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from risk_engine import DRUG_GENE_MAP, resolve_drug


def configure_gemini():
    """Configure Gemini with API key from environment."""
    if not GEMINI_AVAILABLE:
        return False
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        return False
    genai.configure(api_key=api_key)
    return True


def build_prompt(drug: str, gene: str, diplotype: str, phenotype: str,
                 risk_label: str, severity: str, variants: List[Dict],
                 dosing_rec: str) -> str:
    """Build a structured prompt for Gemini to generate clinical explanation."""

    variant_details = ""
    for v in variants:
        variant_details += f"  - {v.get('rsid', 'unknown')}: {v.get('gene', '')} {v.get('star_allele', '')} "
        variant_details += f"(effect: {v.get('functional_effect', 'unknown')})\n"

    if not variant_details:
        variant_details = "  - No specific variants detected (wildtype assumed)\n"

    drug_info = DRUG_GENE_MAP.get(resolve_drug(drug), {})
    pathway = drug_info.get("pathway", "Unknown metabolic pathway")
    drug_class = drug_info.get("drug_class", "")

    prompt = f"""You are a clinical pharmacogenomics expert. Generate a detailed clinical explanation for the following patient analysis.

PATIENT DATA:
- Drug: {drug} ({drug_class})
- Primary Gene: {gene}
- Diplotype: {diplotype}
- Phenotype: {phenotype}
- Risk Assessment: {risk_label} (Severity: {severity})
- Metabolic Pathway: {pathway}
- Current Dosing Recommendation: {dosing_rec}

DETECTED VARIANTS:
{variant_details}

Please provide your response as a JSON object with EXACTLY these fields:
{{
  "summary": "A 2-3 sentence clinical summary explaining this patient's pharmacogenomic result and its clinical significance.",
  "mechanism": "A detailed paragraph explaining the biological mechanism: how the gene affects the drug, what the variants do at the molecular level, and why this leads to the predicted risk.",
  "variant_specific_effects": ["One sentence per variant explaining its specific molecular effect"],
  "patient_friendly_summary": "A 2-3 sentence explanation in plain language that a patient with no medical background could understand. Avoid jargon.",
  "citations": ["CPIC Guideline citation", "PharmGKB reference", "Any relevant clinical study"]
}}

IMPORTANT: Respond ONLY with the JSON object, no markdown formatting, no extra text."""

    return prompt


def generate_explanation(drug: str, gene: str, diplotype: str, phenotype: str,
                         risk_label: str, severity: str, variants: List[Dict],
                         dosing_rec: str) -> Dict:
    """
    Call Gemini API to generate clinical explanation.
    Returns dict matching LLMExplanation schema.
    Falls back to rule-based explanation if API fails.
    """

    # ── Fallback explanation (always available) ─────────────────
    drug_info = DRUG_GENE_MAP.get(resolve_drug(drug), {})
    pathway = drug_info.get("pathway", "")

    fallback = {
        "summary": f"Patient carries {gene} {diplotype} diplotype, classified as {phenotype} metabolizer. "
                   f"For {drug}, this results in a risk assessment of '{risk_label}' with {severity} severity.",
        "mechanism": pathway or f"{gene} is involved in the metabolism of {drug}. "
                     f"The {diplotype} diplotype results in {phenotype} metabolizer status, "
                     f"which affects how the body processes this medication.",
        "variant_specific_effects": [
            f"{v.get('rsid', 'unknown')} ({v.get('star_allele', '')}): {v.get('functional_effect', 'unknown')} allele"
            for v in variants
        ] if variants else [f"No pharmacogenomic variants detected in {gene}; wildtype (*1/*1) assumed"],
        "patient_friendly_summary": f"Your genetic test shows that your body {'may have difficulty processing' if phenotype in ('PM', 'IM') else 'processes'} "
                                    f"the medication {drug} {'slower than normal' if phenotype in ('PM', 'IM') else 'faster than normal' if phenotype in ('RM', 'URM') else 'normally'}. "
                                    f"{'Your doctor may need to adjust your dose or consider an alternative medication.' if risk_label != 'Safe' else 'Standard dosing should work well for you.'}",
        "citations": [
            f"CPIC Guideline for {gene} and {drug} Therapy",
            f"PharmGKB: {gene}-{drug} drug-gene interaction",
        ],
        "model_used": "fallback-rule-based",
    }

    # ── Try Gemini API ──────────────────────────────────────────
    if not configure_gemini():
        fallback["model_used"] = "fallback-no-api-key"
        return fallback

    try:
        prompt = build_prompt(drug, gene, diplotype, phenotype, risk_label, severity, variants, dosing_rec)

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1024,
            ),
        )

        # Parse the response
        text = response.text.strip()
        # Remove markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()

        parsed = json.loads(text)

        return {
            "summary": parsed.get("summary", fallback["summary"]),
            "mechanism": parsed.get("mechanism", fallback["mechanism"]),
            "variant_specific_effects": parsed.get("variant_specific_effects", fallback["variant_specific_effects"]),
            "patient_friendly_summary": parsed.get("patient_friendly_summary", fallback["patient_friendly_summary"]),
            "citations": parsed.get("citations", fallback["citations"]),
            "model_used": "gemini-2.0-flash",
        }

    except json.JSONDecodeError:
        # Gemini returned non-JSON — use the raw text as summary
        try:
            raw_text = response.text.strip()
            return {
                "summary": raw_text[:500],
                "mechanism": fallback["mechanism"],
                "variant_specific_effects": fallback["variant_specific_effects"],
                "patient_friendly_summary": fallback["patient_friendly_summary"],
                "citations": fallback["citations"],
                "model_used": "gemini-2.0-flash-partial",
            }
        except Exception:
            return fallback

    except Exception as e:
        print(f"[Gemini Error] {e}")
        traceback.print_exc()
        fallback["model_used"] = f"fallback-error: {str(e)[:100]}"
        return fallback
