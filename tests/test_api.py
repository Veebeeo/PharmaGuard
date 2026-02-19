import pytest
from fastapi.testclient import TestClient
from backend.main import app
import os

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_analyze_endpoint():
    # Create a dummy VCF string based on your app's expected format
    vcf_content = """##fileformat=VCFv4.2
##PATIENT_ID=PATIENT_001
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE
22\t42522755\trs3892097\tC\tT\t.\t.\tGENE=CYP2D6;STAR=*4\tGT\t1/1
"""
    
    # Write to a temporary file for the test
    with open("temp_test.vcf", "w") as f:
        f.write(vcf_content)
        
    with open("temp_test.vcf", "rb") as f:
        response = client.post(
            "/api/analyze",
            files={"vcf_file": ("temp_test.vcf", f, "text/vcard")},
            data={"drugs": "CODEINE"}
        )
    
    os.remove("temp_test.vcf")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_drugs_analyzed"] == 1
    
    codeine_result = data["results"][0]
    assert codeine_result["drug"] == "CODEINE"
    assert codeine_result["pharmacogenomic_profile"]["diplotype"] == "*4/*4"