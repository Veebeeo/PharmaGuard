-- ═══════════════════════════════════════════════════════════════════
-- PharmaGuard AI — Supabase Database Schema
-- Run this ENTIRE script in your Supabase SQL Editor (Dashboard > SQL)
-- ═══════════════════════════════════════════════════════════════════

-- ─── 1. PHENOTYPE MAPPINGS TABLE ─────────────────────────────────
-- Replaces hardcoded diplotype → phenotype logic
-- Your backend queries: gene + allele1 + allele2 → phenotype

CREATE TABLE IF NOT EXISTS phenotype_mappings (
    id BIGSERIAL PRIMARY KEY,
    gene TEXT NOT NULL,
    allele1 TEXT NOT NULL,
    allele2 TEXT NOT NULL,
    activity_score_total NUMERIC(4,2),
    phenotype TEXT NOT NULL,  -- PM, IM, NM, RM, URM
    phenotype_full TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(gene, allele1, allele2)
);

-- ─── 2. CPIC GUIDELINES TABLE ────────────────────────────────────
-- Replaces hardcoded RISK_MATRIX + CLINICAL_RECS dictionaries

CREATE TABLE IF NOT EXISTS cpic_guidelines (
    id BIGSERIAL PRIMARY KEY,
    drug TEXT NOT NULL,
    gene TEXT NOT NULL,
    phenotype TEXT NOT NULL,  -- PM, IM, NM, RM, URM
    risk_label TEXT NOT NULL, -- Safe, Adjust Dosage, Toxic, Ineffective, Unknown
    severity TEXT NOT NULL,   -- none, low, moderate, high, critical
    confidence NUMERIC(3,2) DEFAULT 0.90,
    dosing_recommendation TEXT NOT NULL,
    alternative_drugs TEXT[] DEFAULT '{}',
    monitoring_parameters TEXT[] DEFAULT '{}',
    cpic_reference TEXT,
    urgency TEXT DEFAULT 'routine',  -- routine, soon, urgent, emergent
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(drug, phenotype)
);

-- ─── 3. KNOWN VARIANTS TABLE ─────────────────────────────────────
-- Replaces hardcoded KNOWN_VARIANTS dictionary

CREATE TABLE IF NOT EXISTS known_variants (
    id BIGSERIAL PRIMARY KEY,
    rsid TEXT NOT NULL UNIQUE,
    gene TEXT NOT NULL,
    star_allele TEXT NOT NULL,
    functional_effect TEXT NOT NULL,  -- normal, increased_function, decreased_function, no_function
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── 4. DRUG-GENE MAPPINGS TABLE ─────────────────────────────────

CREATE TABLE IF NOT EXISTS drug_gene_map (
    id BIGSERIAL PRIMARY KEY,
    drug TEXT NOT NULL UNIQUE,
    gene TEXT NOT NULL,
    pathway TEXT,
    drug_class TEXT
);

-- ─── 5. ALLELE ACTIVITY SCORES TABLE ─────────────────────────────
-- Gene-specific activity scores for star alleles

CREATE TABLE IF NOT EXISTS allele_activity (
    id BIGSERIAL PRIMARY KEY,
    gene TEXT NOT NULL,
    star_allele TEXT NOT NULL,
    activity_score NUMERIC(4,2) NOT NULL,
    UNIQUE(gene, star_allele)
);

-- ─── 6. PATIENT REPORTS TABLE ────────────────────────────────────
-- Stores completed analysis reports (JSONB)

CREATE TABLE IF NOT EXISTS patient_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    patient_id TEXT NOT NULL,
    drug TEXT NOT NULL,
    risk_label TEXT NOT NULL,
    severity TEXT NOT NULL,
    phenotype TEXT,
    gene TEXT,
    diplotype TEXT,
    report_json JSONB NOT NULL,
    vcf_storage_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reports_user ON patient_reports(user_id);
CREATE INDEX idx_reports_patient ON patient_reports(patient_id);
CREATE INDEX idx_reports_created ON patient_reports(created_at DESC);

-- ─── 7. ROW LEVEL SECURITY ──────────────────────────────────────
-- Doctors can only see their own patient reports

ALTER TABLE patient_reports ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own reports"
    ON patient_reports FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own reports"
    ON patient_reports FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own reports"
    ON patient_reports FOR DELETE
    USING (auth.uid() = user_id);

-- Public read for reference tables (no auth needed)
ALTER TABLE phenotype_mappings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read phenotype_mappings" ON phenotype_mappings FOR SELECT USING (true);

ALTER TABLE cpic_guidelines ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read cpic_guidelines" ON cpic_guidelines FOR SELECT USING (true);

ALTER TABLE known_variants ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read known_variants" ON known_variants FOR SELECT USING (true);

ALTER TABLE drug_gene_map ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read drug_gene_map" ON drug_gene_map FOR SELECT USING (true);

ALTER TABLE allele_activity ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read allele_activity" ON allele_activity FOR SELECT USING (true);


-- ═══════════════════════════════════════════════════════════════════
-- SEED DATA — All pharmacogenomic reference data
-- ═══════════════════════════════════════════════════════════════════

-- ─── DRUG-GENE MAP ───────────────────────────────────────────────
INSERT INTO drug_gene_map (drug, gene, pathway, drug_class) VALUES
('CODEINE',      'CYP2D6',  'CYP2D6 O-demethylates codeine to morphine. URMs produce excess morphine; PMs get no effect.', 'Opioid analgesic'),
('WARFARIN',     'CYP2C9',  'CYP2C9 metabolizes S-warfarin. Reduced function → elevated levels → bleeding risk.', 'Anticoagulant'),
('CLOPIDOGREL',  'CYP2C19', 'CYP2C19 bioactivates the prodrug. PMs cannot activate → treatment failure.', 'Antiplatelet'),
('SIMVASTATIN',  'SLCO1B1', 'SLCO1B1 mediates hepatic uptake. Decreased function → elevated plasma → myopathy.', 'Statin'),
('AZATHIOPRINE', 'TPMT',    'TPMT methylates thiopurines. Deficiency → toxic TGN accumulation → myelosuppression.', 'Immunosuppressant'),
('FLUOROURACIL', 'DPYD',    'DPD catabolizes >80% of 5-FU. Deficiency → drug accumulation → fatal toxicity.', 'Antineoplastic')
ON CONFLICT (drug) DO NOTHING;

-- ─── KNOWN VARIANTS ──────────────────────────────────────────────
INSERT INTO known_variants (rsid, gene, star_allele, functional_effect, description) VALUES
('rs3892097',  'CYP2D6',  '*4',  'no_function',        'Splicing defect; most common null allele in Europeans'),
('rs5030655',  'CYP2D6',  '*6',  'no_function',        'Frameshift deletion'),
('rs1065852',  'CYP2D6',  '*10', 'decreased_function',  'Pro34Ser; common in Asians'),
('rs16947',    'CYP2D6',  '*2',  'normal',              'Normal function'),
('rs1135840',  'CYP2D6',  '*2B', 'normal',              'Ser486Thr; normal function'),
('rs28371725', 'CYP2D6',  '*41', 'decreased_function',  'Reduced splicing'),
('rs5030656',  'CYP2D6',  '*9',  'decreased_function',  'Lys281del'),
('rs28371706', 'CYP2D6',  '*17', 'decreased_function',  'Thr107Ile; common in Africans'),
('rs4244285',  'CYP2C19', '*2',  'no_function',        'Splicing defect; most common LOF'),
('rs4986893',  'CYP2C19', '*3',  'no_function',        'Premature stop codon'),
('rs12248560', 'CYP2C19', '*17', 'increased_function',  'Enhanced promoter; ultra-rapid'),
('rs28399504', 'CYP2C19', '*4',  'no_function',        'Rare LOF allele'),
('rs56337013', 'CYP2C19', '*5',  'no_function',        'Arg433Trp'),
('rs72552267', 'CYP2C19', '*6',  'no_function',        'Arg132Gln'),
('rs72558186', 'CYP2C19', '*7',  'no_function',        'Splicing defect'),
('rs41291556', 'CYP2C19', '*8',  'no_function',        'Trp120Arg'),
('rs1799853',  'CYP2C9',  '*2',  'decreased_function',  'Arg144Cys; ~30% reduced warfarin metabolism'),
('rs1057910',  'CYP2C9',  '*3',  'decreased_function',  'Ile359Leu; ~80% reduced warfarin metabolism'),
('rs28371686', 'CYP2C9',  '*5',  'decreased_function',  'Asp360Glu'),
('rs9332131',  'CYP2C9',  '*6',  'no_function',        'Frameshift; LOF'),
('rs7900194',  'CYP2C9',  '*8',  'decreased_function',  'Arg150His; common in African Americans'),
('rs2256871',  'CYP2C9',  '*9',  'decreased_function',  'His251Arg'),
('rs28371685', 'CYP2C9',  '*11', 'decreased_function',  'Arg335Trp'),
('rs4149056',  'SLCO1B1', '*5',  'decreased_function',  'Val174Ala; impaired statin uptake'),
('rs2306283',  'SLCO1B1', '*1B', 'normal',              'Asn130Asp; normal function'),
('rs4149015',  'SLCO1B1', '*1A', 'normal',              'Reference allele'),
('rs11045819', 'SLCO1B1', '*14', 'decreased_function',  'Pro155Thr'),
('rs1800460',  'TPMT',    '*3B', 'no_function',        'Ala154Thr; non-functional'),
('rs1142345',  'TPMT',    '*3C', 'no_function',        'Tyr240Cys; most common globally'),
('rs1800462',  'TPMT',    '*2',  'no_function',        'Ala80Pro; non-functional'),
('rs1800584',  'TPMT',    '*4',  'no_function',        'Rare non-functional'),
('rs3918290',  'DPYD',    '*2A', 'no_function',        'IVS14+1G>A; exon 14 skipping'),
('rs67376798', 'DPYD',    '*13', 'decreased_function',  'Ile560Ser; ~50% reduced DPD'),
('rs55886062', 'DPYD',    'c.1679T>G',          'no_function',       'Complete DPD loss'),
('rs75017182', 'DPYD',    'c.1129-5923C>G',      'decreased_function', 'HapB3 intronic'),
('rs56038477', 'DPYD',    'c.1129-5923C>G_tag',  'decreased_function', 'HapB3 tag SNP')
ON CONFLICT (rsid) DO NOTHING;

-- ─── ALLELE ACTIVITY SCORES ─────────────────────────────────────
INSERT INTO allele_activity (gene, star_allele, activity_score) VALUES
-- CYP2D6
('CYP2D6','*1',1.0),('CYP2D6','*2',1.0),('CYP2D6','*2B',1.0),('CYP2D6','*4',0.0),('CYP2D6','*6',0.0),
('CYP2D6','*9',0.5),('CYP2D6','*10',0.25),('CYP2D6','*17',0.5),('CYP2D6','*41',0.5),
-- CYP2C19
('CYP2C19','*1',1.0),('CYP2C19','*2',0.0),('CYP2C19','*3',0.0),('CYP2C19','*4',0.0),('CYP2C19','*5',0.0),
('CYP2C19','*6',0.0),('CYP2C19','*7',0.0),('CYP2C19','*8',0.0),('CYP2C19','*17',1.5),
-- CYP2C9
('CYP2C9','*1',1.0),('CYP2C9','*2',0.5),('CYP2C9','*3',0.25),('CYP2C9','*5',0.0),('CYP2C9','*6',0.0),
('CYP2C9','*8',0.5),('CYP2C9','*9',0.5),('CYP2C9','*11',0.5),
-- SLCO1B1
('SLCO1B1','*1',1.0),('SLCO1B1','*1A',1.0),('SLCO1B1','*1B',1.0),('SLCO1B1','*5',0.0),('SLCO1B1','*14',0.5),
-- TPMT
('TPMT','*1',1.0),('TPMT','*2',0.0),('TPMT','*3B',0.0),('TPMT','*3C',0.0),('TPMT','*4',0.0),
-- DPYD
('DPYD','*1',1.0),('DPYD','*2A',0.0),('DPYD','*13',0.5),('DPYD','c.1679T>G',0.0),('DPYD','c.1129-5923C>G',0.5)
ON CONFLICT (gene, star_allele) DO NOTHING;

-- ─── CPIC GUIDELINES (Risk Matrix + Recommendations) ─────────────
INSERT INTO cpic_guidelines (drug, gene, phenotype, risk_label, severity, confidence, dosing_recommendation, alternative_drugs, monitoring_parameters, cpic_reference, urgency) VALUES
-- CODEINE
('CODEINE','CYP2D6','URM','Toxic','critical',0.95,'AVOID codeine. Ultra-rapid CYP2D6 metabolism → excess morphine → respiratory depression risk.','{"Morphine (with caution)","Non-opioid analgesics (NSAIDs, acetaminophen)"}','{"Respiratory rate","Sedation level","O2 saturation"}','CPIC Guideline for CYP2D6 and Codeine Therapy (2019)','emergent'),
('CODEINE','CYP2D6','RM','Toxic','high',0.88,'AVOID codeine. Rapid metabolism may cause excess morphine.','{"Morphine (dose-adjusted)","Non-opioid analgesics"}','{"Respiratory rate","Sedation"}','CPIC Guideline for CYP2D6 and Codeine Therapy (2019)','urgent'),
('CODEINE','CYP2D6','NM','Safe','none',0.92,'Use codeine at standard dose. Normal CYP2D6 metabolism.','{}','{"Pain assessment","Adverse effects"}','CPIC Guideline for CYP2D6 and Codeine Therapy (2019)','routine'),
('CODEINE','CYP2D6','IM','Ineffective','moderate',0.85,'Reduced efficacy expected. Consider alternative analgesic.','{"Morphine","Hydromorphone","Non-opioid analgesics"}','{"Pain control adequacy"}','CPIC Guideline for CYP2D6 and Codeine Therapy (2019)','soon'),
('CODEINE','CYP2D6','PM','Ineffective','high',0.95,'AVOID codeine. PMs cannot convert codeine to morphine — no analgesic effect.','{"Morphine","Hydromorphone","Non-opioid analgesics"}','{"Pain control with alternative"}','CPIC Guideline for CYP2D6 and Codeine Therapy (2019)','urgent'),
-- WARFARIN
('WARFARIN','CYP2C9','URM','Adjust Dosage','low',0.80,'May require higher warfarin doses. INR-guided titration.','{}','{"INR"}','CPIC Guideline for Warfarin Dosing (2017)','routine'),
('WARFARIN','CYP2C9','RM','Adjust Dosage','low',0.80,'May need higher dose. INR-guided titration.','{}','{"INR"}','CPIC Guideline for Warfarin Dosing (2017)','routine'),
('WARFARIN','CYP2C9','NM','Safe','none',0.90,'Standard dose (5 mg/day). Adjust per INR.','{}','{"INR (2.0-3.0)","Bleeding signs"}','CPIC Guideline for Warfarin Dosing (2017)','routine'),
('WARFARIN','CYP2C9','IM','Adjust Dosage','high',0.92,'Reduce dose 25-50%. Intermediate CYP2C9 metabolism.','{"Apixaban","Rivaroxaban"}','{"INR (frequent)","Bleeding","Hemoglobin"}','CPIC Guideline for Warfarin Dosing (2017)','soon'),
('WARFARIN','CYP2C9','PM','Toxic','critical',0.95,'Reduce dose 50-80%. HIGH BLEEDING RISK. Consider DOAC.','{"Apixaban","Rivaroxaban","Edoxaban"}','{"INR 2-3x/week","CBC","Bleeding signs"}','CPIC Guideline for Warfarin Dosing (2017)','urgent'),
-- CLOPIDOGREL
('CLOPIDOGREL','CYP2C19','URM','Safe','none',0.85,'Standard dose. Slightly increased bleeding risk possible.','{}','{"Bleeding signs"}','CPIC Guideline for CYP2C19 and Clopidogrel (2022)','routine'),
('CLOPIDOGREL','CYP2C19','RM','Safe','none',0.88,'Standard dose. Adequate activation.','{}','{"CV monitoring"}','CPIC Guideline for CYP2C19 and Clopidogrel (2022)','routine'),
('CLOPIDOGREL','CYP2C19','NM','Safe','none',0.92,'Standard dose (75 mg/day). Normal bioactivation.','{}','{"Platelet function","CV events"}','CPIC Guideline for CYP2C19 and Clopidogrel (2022)','routine'),
('CLOPIDOGREL','CYP2C19','IM','Adjust Dosage','moderate',0.88,'Reduced activation. Consider alternative or double dose with monitoring.','{"Prasugrel","Ticagrelor"}','{"Platelet function","CV events"}','CPIC Guideline for CYP2C19 and Clopidogrel (2022)','soon'),
('CLOPIDOGREL','CYP2C19','PM','Ineffective','critical',0.95,'AVOID clopidogrel. Cannot activate prodrug — HIGH treatment failure risk.','{"Prasugrel","Ticagrelor"}','{"Platelet function","Stent thrombosis"}','CPIC Guideline for CYP2C19 and Clopidogrel (2022)','emergent'),
-- SIMVASTATIN
('SIMVASTATIN','SLCO1B1','URM','Safe','none',0.80,'Standard dose.','{}','{"LDL-C"}','CPIC Guideline for SLCO1B1 and Statins (2022)','routine'),
('SIMVASTATIN','SLCO1B1','RM','Safe','none',0.85,'Standard dose.','{}','{"LDL-C","Muscle symptoms"}','CPIC Guideline for SLCO1B1 and Statins (2022)','routine'),
('SIMVASTATIN','SLCO1B1','NM','Safe','none',0.92,'Standard dose. Normal SLCO1B1 function.','{}','{"LDL-C","LFTs","Muscle symptoms"}','CPIC Guideline for SLCO1B1 and Statins (2022)','routine'),
('SIMVASTATIN','SLCO1B1','IM','Adjust Dosage','moderate',0.88,'Limit to ≤20 mg/day. Increased myopathy risk.','{"Pravastatin","Rosuvastatin"}','{"CK levels","Muscle pain","LDL-C"}','CPIC Guideline for SLCO1B1 and Statins (2022)','soon'),
('SIMVASTATIN','SLCO1B1','PM','Toxic','high',0.92,'AVOID simvastatin. High myopathy/rhabdomyolysis risk.','{"Pravastatin","Rosuvastatin","Fluvastatin"}','{"CK","Renal function","Muscle symptoms"}','CPIC Guideline for SLCO1B1 and Statins (2022)','urgent'),
-- AZATHIOPRINE
('AZATHIOPRINE','TPMT','URM','Safe','none',0.80,'May need higher dose. Monitor response.','{}','{"TGN levels","CBC"}','CPIC Guideline for TPMT and Thiopurines (2018)','routine'),
('AZATHIOPRINE','TPMT','RM','Safe','none',0.85,'Standard dose.','{}','{"CBC","LFTs"}','CPIC Guideline for TPMT and Thiopurines (2018)','routine'),
('AZATHIOPRINE','TPMT','NM','Safe','none',0.92,'Standard dose (2-3 mg/kg/day). Normal TPMT.','{}','{"CBC","LFTs"}','CPIC Guideline for TPMT and Thiopurines (2018)','routine'),
('AZATHIOPRINE','TPMT','IM','Adjust Dosage','high',0.90,'Reduce dose 30-80%. Start 0.5-1.5 mg/kg/day.','{"Mycophenolate mofetil"}','{"CBC weekly then biweekly","LFTs","TGN levels"}','CPIC Guideline for TPMT and Thiopurines (2018)','urgent'),
('AZATHIOPRINE','TPMT','PM','Toxic','critical',0.97,'AVOID or reduce 90%. LIFE-THREATENING myelosuppression risk.','{"Mycophenolate mofetil"}','{"CBC 2-3x/week","ANC","TGN levels"}','CPIC Guideline for TPMT and Thiopurines (2018)','emergent'),
-- FLUOROURACIL
('FLUOROURACIL','DPYD','URM','Safe','none',0.80,'Standard dose. May have reduced efficacy.','{}','{"Treatment response","CBC"}','CPIC Guideline for DPYD and Fluoropyrimidines (2017)','routine'),
('FLUOROURACIL','DPYD','RM','Safe','none',0.85,'Standard dose.','{}','{"CBC","Toxicity"}','CPIC Guideline for DPYD and Fluoropyrimidines (2017)','routine'),
('FLUOROURACIL','DPYD','NM','Safe','none',0.92,'Standard dose. Normal DPD activity.','{}','{"CBC","Mucositis","Hand-foot syndrome"}','CPIC Guideline for DPYD and Fluoropyrimidines (2017)','routine'),
('FLUOROURACIL','DPYD','IM','Adjust Dosage','high',0.90,'Reduce dose 25-50%. Intermediate DPD activity.','{"Dose-reduced capecitabine"}','{"CBC 2x/week","Mucositis","Diarrhea","Neurotoxicity"}','CPIC Guideline for DPYD and Fluoropyrimidines (2017)','urgent'),
('FLUOROURACIL','DPYD','PM','Toxic','critical',0.97,'AVOID all fluoropyrimidines. Complete DPD deficiency → FATAL toxicity.','{"Non-fluoropyrimidine chemo (consult oncology)"}','{"If given: emergent CBC, renal, electrolytes, ICU"}','CPIC Guideline for DPYD and Fluoropyrimidines (2017)','emergent')
ON CONFLICT (drug, phenotype) DO NOTHING;


-- ═══════════════════════════════════════════════════════════════════
-- STORAGE BUCKET for VCF files
-- ═══════════════════════════════════════════════════════════════════
-- Run this separately if the above doesn't work in one go:
-- INSERT INTO storage.buckets (id, name, public) VALUES ('vcf-uploads', 'vcf-uploads', false);

-- NOTE: You may need to create the bucket via Dashboard > Storage > New Bucket
-- Name: vcf-uploads, Private (not public)
-- Then add these policies via Dashboard > Storage > vcf-uploads > Policies:
--   - Allow authenticated users to upload: (auth.uid() IS NOT NULL)
--   - Allow authenticated users to read own files: (auth.uid()::text = (storage.foldername(name))[1])
