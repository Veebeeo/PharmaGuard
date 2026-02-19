"""
PharmaGuard AI — VCF Parser
Parses Variant Call Format files and extracts pharmacogenomic variants.

Supports:
  - Standard VCFv4.x format
  - INFO tags: GENE=, STAR=, RS=
  - Fallback: matches rsID from ID column against known variant database
  - Genotype extraction from FORMAT/SAMPLE columns
"""
import re
from typing import Dict, List, Tuple, Optional
from risk_engine import KNOWN_VARIANTS, TARGET_GENES, DRUG_GENE_MAP, determine_phenotype, resolve_drug


def parse_info_field(info: str) -> Dict[str, str]:
    """Parse VCF INFO field (semicolon-separated key=value pairs)."""
    result = {}
    if not info or info == ".":
        return result
    for item in info.split(";"):
        if "=" in item:
            key, val = item.split("=", 1)
            result[key.strip()] = val.strip()
        else:
            result[item.strip()] = "true"
    return result


def extract_genotype(format_field: str, sample_field: str) -> str:
    """Extract GT (genotype) from FORMAT and SAMPLE columns."""
    if not format_field or not sample_field:
        return ""
    try:
        keys = format_field.split(":")
        values = sample_field.split(":")
        if "GT" in keys:
            idx = keys.index("GT")
            if idx < len(values):
                return values[idx]
    except Exception:
        pass
    return ""


def parse_vcf(vcf_content: str) -> Dict:
    """
    Parse a VCF file and extract pharmacogenomic variants.

    Returns:
        {
            "patient_id": str,
            "total_variants": int,
            "pgx_variants": [
                {
                    "rsid": str, "gene": str, "chromosome": str,
                    "position": int, "ref": str, "alt": str,
                    "star": str, "genotype": str, "effect": str,
                    "quality": float, "description": str,
                }
            ],
            "gene_variants": {gene: [variants]},  # grouped by gene
            "genes_found": [str],
            "errors": [str],
            "vcf_valid": bool,
        }
    """
    result = {
        "patient_id": "PATIENT_001",
        "total_variants": 0,
        "pgx_variants": [],
        "gene_variants": {},
        "genes_found": [],
        "errors": [],
        "vcf_valid": False,
    }

    lines = vcf_content.strip().split("\n")
    if not lines:
        result["errors"].append("Empty VCF file")
        return result

    # ── Check for valid VCF header ──────────────────────────────
    has_fileformat = False
    header_line = None
    data_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("##fileformat=VCF"):
            has_fileformat = True
        if stripped.startswith("##"):
            # Check for patient ID in meta-info
            if "PATIENT" in stripped.upper():
                # Match patterns like ##PATIENT_ID=PATIENT_001 or ##PATIENT_ID=001
                match = re.search(r'PATIENT[_\-]?ID\s*=\s*(\S+)', stripped, re.IGNORECASE)
                if match:
                    pid = match.group(1)
                    if not pid.upper().startswith("PATIENT"):
                        pid = f"PATIENT_{pid}"
                    result["patient_id"] = pid
        elif stripped.startswith("#CHROM") or stripped.startswith("#chrom"):
            header_line = stripped
        elif stripped and not stripped.startswith("#"):
            data_lines.append(stripped)

    if not has_fileformat:
        # Be lenient — some VCFs might not have this
        result["errors"].append("Warning: Missing ##fileformat=VCF header")

    if header_line is None:
        result["errors"].append("Missing #CHROM header line")
        # Try to parse anyway if there are data lines
        if not data_lines:
            return result

    # Determine column indices from header
    has_format = False
    has_sample = False
    if header_line:
        cols = header_line.lstrip("#").split("\t")
        col_count = len(cols)
        has_format = col_count > 8
        has_sample = col_count > 9

    result["vcf_valid"] = True

    # ── Parse each variant line ─────────────────────────────────
    for line in data_lines:
        fields = line.split("\t")
        if len(fields) < 5:
            continue  # Skip malformed lines

        result["total_variants"] += 1

        chrom = fields[0].strip()
        pos = fields[1].strip()
        rsid = fields[2].strip() if len(fields) > 2 else "."
        ref = fields[3].strip() if len(fields) > 3 else ""
        alt = fields[4].strip() if len(fields) > 4 else ""
        qual = fields[5].strip() if len(fields) > 5 else "0"
        filt = fields[6].strip() if len(fields) > 6 else "."
        info_str = fields[7].strip() if len(fields) > 7 else ""

        # Parse quality
        try:
            quality = float(qual) if qual != "." else 0.0
        except ValueError:
            quality = 0.0

        # Parse INFO field
        info = parse_info_field(info_str)

        # Extract genotype
        genotype = ""
        if has_format and has_sample and len(fields) > 9:
            genotype = extract_genotype(fields[8], fields[9])

        # Skip homozygous reference (0/0 or 0|0) — no variant present
        if genotype in ("0/0", "0|0"):
            result["total_variants"] += 0  # already counted above
            continue

        # ── Identify pharmacogenomic variant ────────────────────
        gene = info.get("GENE", "")
        star = info.get("STAR", "")
        rs_from_info = info.get("RS", "")
        effect = ""
        description = ""

        # Strategy 1: Use INFO tags if present
        if gene and gene in TARGET_GENES:
            # Look up effect from our database
            lookup_rsid = rsid if rsid != "." else rs_from_info
            if lookup_rsid in KNOWN_VARIANTS:
                effect = KNOWN_VARIANTS[lookup_rsid]["effect"]
                description = KNOWN_VARIANTS[lookup_rsid].get("desc", "")
            elif star:
                # Try to infer from star allele
                for v in KNOWN_VARIANTS.values():
                    if v["gene"] == gene and v["star"] == star:
                        effect = v["effect"]
                        description = v.get("desc", "")
                        break
            if not effect:
                effect = "unknown"

            variant_data = {
                "rsid": rsid if rsid != "." else rs_from_info,
                "gene": gene,
                "chromosome": chrom,
                "position": int(pos) if pos.isdigit() else 0,
                "ref": ref,
                "alt": alt,
                "star": star,
                "genotype": genotype,
                "effect": effect,
                "quality": quality,
                "description": description,
            }
            result["pgx_variants"].append(variant_data)
            result["gene_variants"].setdefault(gene, []).append(variant_data)
            continue

        # Strategy 2: Fallback — match rsID against known variants DB
        lookup_id = rsid if rsid != "." else rs_from_info
        if lookup_id and lookup_id in KNOWN_VARIANTS:
            known = KNOWN_VARIANTS[lookup_id]
            variant_data = {
                "rsid": lookup_id,
                "gene": known["gene"],
                "chromosome": chrom,
                "position": int(pos) if pos.isdigit() else 0,
                "ref": ref,
                "alt": alt,
                "star": known["star"],
                "genotype": genotype,
                "effect": known["effect"],
                "quality": quality,
                "description": known.get("desc", ""),
            }
            result["pgx_variants"].append(variant_data)
            result["gene_variants"].setdefault(known["gene"], []).append(variant_data)
            continue

        # Strategy 3: Check if GENE tag points to a target gene even without star
        if gene in TARGET_GENES:
            variant_data = {
                "rsid": rsid if rsid != "." else "unknown",
                "gene": gene,
                "chromosome": chrom,
                "position": int(pos) if pos.isdigit() else 0,
                "ref": ref,
                "alt": alt,
                "star": star or "unknown",
                "genotype": genotype,
                "effect": "unknown",
                "quality": quality,
                "description": "",
            }
            result["pgx_variants"].append(variant_data)
            result["gene_variants"].setdefault(gene, []).append(variant_data)

    result["genes_found"] = sorted(result["gene_variants"].keys())
    return result


def build_profile_for_drug(parsed_vcf: Dict, drug: str) -> Dict:
    """
    Given parsed VCF data and a drug, determine:
    - primary gene, diplotype, phenotype
    - list of detected variants for that gene

    Returns dict with keys: primary_gene, diplotype, phenotype, detected_variants
    """
    drug_upper = resolve_drug(drug)

    # Use get_drug_gene_info which checks hardcoded → Supabase → CPIC API
    from risk_engine import get_drug_gene_info
    drug_info = get_drug_gene_info(drug_upper)

    if not drug_info or not drug_info.get("gene"):
        return {
            "primary_gene": "Unknown",
            "diplotype": "Unknown",
            "phenotype": "Unknown",
            "detected_variants": [],
        }

    gene = drug_info["gene"]
    gene_variants = parsed_vcf["gene_variants"].get(gene, [])

    if not gene_variants:
        # No variants found for this gene → assume wildtype
        return {
            "primary_gene": gene,
            "diplotype": "*1/*1",
            "phenotype": "NM",
            "detected_variants": [],
        }

    # ── Determine diplotype ─────────────────────────────────────
    # Collect all star alleles found
    stars = []
    for v in gene_variants:
        if v["star"] and v["star"] != "unknown":
            stars.append(v["star"])

    if not stars:
        # Have gene variants but no star alleles
        allele1, allele2 = "*1", "*1"
    elif len(stars) == 1:
        # Heterozygous: one variant allele + one wildtype
        # Check genotype for homozygous
        gt = gene_variants[0].get("genotype", "")
        if gt in ("1/1", "1|1"):
            allele1, allele2 = stars[0], stars[0]
        else:
            allele1, allele2 = "*1", stars[0]
    else:
        # Multiple variants — take first two distinct
        unique_stars = list(dict.fromkeys(stars))  # preserve order, dedupe
        allele1 = unique_stars[0]
        allele2 = unique_stars[1] if len(unique_stars) > 1 else unique_stars[0]

    diplotype = f"{allele1}/{allele2}"
    phenotype = determine_phenotype(allele1, allele2, gene)

    # Build detected variants list
    detected = []
    for v in gene_variants:
        detected.append({
            "rsid": v["rsid"],
            "gene": v["gene"],
            "chromosome": v["chromosome"],
            "position": v["position"],
            "ref_allele": v["ref"],
            "alt_allele": v["alt"],
            "star_allele": v["star"],
            "genotype": v["genotype"],
            "functional_effect": v["effect"],
            "quality": v["quality"],
        })

    return {
        "primary_gene": gene,
        "diplotype": diplotype,
        "phenotype": phenotype,
        "detected_variants": detected,
    }
