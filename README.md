# PharmaGuard AI

**AI-Powered Pharmacogenomic Risk Analysis**

> Decode your genes. Protect your life.

[![Live Demo](https://img.shields.io/badge/Live_Demo-PharmaGuard_AI-2d6a4f?style=for-the-badge)](YOUR_DEPLOYED_URL_HERE)
[![LinkedIn Video](https://img.shields.io/badge/LinkedIn-Demo_Video-0A66C2?style=for-the-badge)](YOUR_LINKEDIN_VIDEO_URL_HERE)

---

## Overview

Adverse drug reactions kill **over 100,000 Americans annually**. Many of these deaths are preventable through pharmacogenomic testing — analyzing how genetic variants affect drug metabolism.

**PharmaGuard AI** analyzes patient genetic data (VCF files) and drug names to predict personalized pharmacogenomic risks with clinically actionable, CPIC-aligned recommendations powered by Google Gemini AI.

## Live Demo

- **Live Application**: [YOUR_DEPLOYED_URL_HERE](YOUR_DEPLOYED_URL_HERE)
- **LinkedIn Video Demo**: [YOUR_LINKEDIN_VIDEO_URL_HERE](YOUR_LINKEDIN_VIDEO_URL_HERE)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (SPA)                            │
│  Landing → Analyze (Upload + Drug Select) → Results → About │
│  Vanilla JS  |  Drag-Drop Upload  |  Color-coded Risk Cards │
└──────────────────────────┬──────────────────────────────────┘
                           │ POST /api/analyze (FormData)
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend                            │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  VCF Parser   │→│ Risk Engine   │→│  Gemini Service    │  │
│  │ (vcf_parser)  │  │ (risk_engine) │  │ (gemini_service)  │  │
│  │               │  │               │  │                   │  │
│  │ • Parse VCF   │  │ • 35+ known   │  │ • Structured      │  │
│  │ • Extract     │  │   variants    │  │   prompts         │  │
│  │   variants    │  │ • 6 drug-gene │  │ • Clinical        │  │
│  │ • Match rsIDs │  │   mappings    │  │   explanations    │  │
│  │ • Determine   │  │ • Phenotype   │  │ • Fallback logic  │  │
│  │   genotypes   │  │   scoring     │  │                   │  │
│  │               │  │ • CPIC risk   │  │                   │  │
│  │               │  │   matrix      │  │                   │  │
│  └──────────────┘  └──────────────┘  └───────────────────┘  │
│                                                              │
│  Output: Structured JSON per spec (PharmaGuardResponse)      │
└──────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Component    | Technology                      |
|-------------|----------------------------------|
| Frontend    | Vanilla JS SPA + CSS3            |
| Backend     | Python FastAPI                   |
| AI Engine   | Google Gemini 2.0 Flash          |
| VCF Parsing | Custom Python parser             |
| Risk Engine | CPIC-aligned rule engine         |
| Models      | Pydantic v2                      |
| Deployment  | Docker + Render                  |

## Features

- **VCF File Upload**: Drag-and-drop or file picker with client-side validation (extension, size ≤5MB, header check)
- **Multi-Drug Analysis**: Click drug pills or type comma-separated names. Supports 6 CPIC drugs + aliases
- **Color-Coded Risk Cards**: Green (Safe), Yellow (Adjust Dosage), Red (Toxic/Ineffective)
- **Expandable Sections**: Pharmacogenomic profile, clinical recommendation, AI explanation, quality metrics, raw JSON
- **AI Explanations**: Gemini-generated clinical summaries with mechanisms, variant effects, and patient-friendly language
- **JSON Output**: Copy-to-clipboard + downloadable JSON per drug or full analysis
- **Robust Parsing**: 3-strategy variant matching (INFO tags → rsID fallback → gene tag), 0/0 genotype filtering

## Supported Drugs & Genes

| Drug           | Primary Gene | Drug Class          |
|----------------|-------------|----------------------|
| Codeine        | CYP2D6      | Opioid analgesic     |
| Warfarin       | CYP2C9      | Anticoagulant        |
| Clopidogrel    | CYP2C19     | Antiplatelet         |
| Simvastatin    | SLCO1B1     | Statin               |
| Azathioprine   | TPMT        | Immunosuppressant    |
| Fluorouracil   | DPYD        | Antineoplastic       |

## Installation

### Prerequisites

- Python 3.10+
- Google Gemini API key ([Get one here](https://aistudio.google.com/apikey))

### Local Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/pharmaguard-ai.git
cd pharmaguard-ai

# Set up environment
cd backend
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn main:app --reload --port 8000

# Open http://localhost:8000 in your browser
```

### Docker

```bash
docker build -t pharmaguard-ai .
docker run -p 10000:10000 -e GOOGLE_API_KEY=your_key_here pharmaguard-ai
```

### Deploy to Render

1. Push to GitHub
2. Create a new Web Service on [Render](https://render.com)
3. Connect your repository
4. Set **Docker** as the environment
5. Add `GOOGLE_API_KEY` as an environment variable
6. Deploy

## API Documentation

### `POST /api/analyze`

Analyze a VCF file against one or more drugs.

**Request** (multipart/form-data):
| Field    | Type   | Description                          |
|----------|--------|--------------------------------------|
| vcf_file | File   | VCF file (.vcf, max 5MB)            |
| drugs    | String | Comma-separated drug names           |

**Response**: `MultiDrugResponse`
```json
{
  "results": [
    {
      "patient_id": "PATIENT_001",
      "drug": "CODEINE",
      "timestamp": "2026-02-19T...",
      "risk_assessment": {
        "risk_label": "Ineffective",
        "confidence_score": 0.95,
        "severity": "high"
      },
      "pharmacogenomic_profile": {
        "primary_gene": "CYP2D6",
        "diplotype": "*4/*6",
        "phenotype": "PM",
        "detected_variants": [...]
      },
      "clinical_recommendation": {
        "dosing_recommendation": "AVOID codeine...",
        "alternative_drugs": ["Morphine", ...],
        "monitoring_parameters": [...],
        "cpic_guideline_reference": "CPIC Guideline...",
        "urgency": "urgent"
      },
      "llm_generated_explanation": {
        "summary": "...",
        "mechanism": "...",
        "variant_specific_effects": [...],
        "patient_friendly_summary": "...",
        "citations": [...],
        "model_used": "gemini-2.0-flash"
      },
      "quality_metrics": {
        "vcf_parsing_success": true,
        "total_variants_parsed": 7,
        "pharmacogenomic_variants_found": 7,
        "gene_coverage": ["CYP2C19", "CYP2C9", "CYP2D6", "DPYD", "SLCO1B1", "TPMT"]
      }
    }
  ],
  "total_drugs_analyzed": 1,
  "analysis_id": "abc12345"
}
```

### `GET /api/health`

Returns API status and configuration.

### `GET /api/supported-drugs`

Returns list of supported drugs with gene mappings.

## Sample VCF Files

Three test files are included in `backend/sample_vcfs/`:

| File               | Key Variants                          | Expected Results                    |
|-------------------|---------------------------------------|--------------------------------------|
| `patient_001.vcf` | CYP2D6 *4/*6, CYP2C9 *1/*2, SLCO1B1 *1/*5 | Codeine: Ineffective, Simvastatin: Adjust |
| `patient_002.vcf` | CYP2C19 *2/*2 (homozygous), DPYD *2A/*13   | Clopidogrel: Ineffective, 5-FU: Adjust    |
| `patient_003.vcf` | CYP2D6 *2 (normal), CYP2C19 *17             | Codeine: Safe, Clopidogrel: Safe           |

## Usage Examples

### Example 1: High-Risk Patient

Upload `patient_001.vcf` → Select **Codeine**

**Result**: ⛔ **Ineffective** (high severity, 95% confidence)
- Patient is CYP2D6 *4/*6 = Poor Metabolizer
- Cannot convert codeine to morphine → no pain relief
- Alternative: Morphine, hydromorphone, NSAIDs

### Example 2: Multi-Drug Analysis

Upload `patient_002.vcf` → Select **All Drugs**

**Results**:
- Clopidogrel: ⛔ Ineffective (CYP2C19 *2/*2 = PM)
- Fluorouracil: ⚠ Adjust Dosage (DPYD *2A/*13 = IM)
- Codeine: ✅ Safe (no CYP2D6 variants = NM)

## Project Structure

```
pharmaguard/
├── backend/
│   ├── main.py              # FastAPI app + routes
│   ├── vcf_parser.py        # VCF file parsing
│   ├── risk_engine.py       # Pharmacogenomics knowledge base
│   ├── gemini_service.py    # Gemini API integration
│   ├── models.py            # Pydantic response models
│   ├── test_core.py         # Core logic tests
│   ├── requirements.txt
│   ├── .env.example
│   └── sample_vcfs/
│       ├── patient_001.vcf
│       ├── patient_002.vcf
│       └── patient_003.vcf
├── frontend/
│   └── index.html           # Single-page application
├── Dockerfile
├── render.yaml
├── .gitignore
└── README.md
```

## Team Members

- **[Your Name]** — Full-stack development, pharmacogenomics engine
- **[Team Member 2]** — [Role]

## Hashtags

#RIFT2026 #PharmaGuard #Pharmacogenomics #AIinHealthcare

## License

MIT License — For research and educational purposes only. Not a medical device.

---

**Disclaimer**: PharmaGuard AI is developed for the RIFT 2026 hackathon and is intended for research and educational purposes only. It is not a medical device and should not be used as a substitute for professional pharmacogenomic testing or clinical judgment.
