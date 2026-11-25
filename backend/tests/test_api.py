import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def auth_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/auth/login",
        json={"email": "dr.sharma@medvault.edu", "password": "Doctor@123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_and_metadata_invariant(client: TestClient):
    """Core Invariant: Health endpoint exposes system status and team metadata without requiring auth."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert len(body["team"]) == 2


def test_auth_and_rbac_boundary_invariant(client: TestClient):
    """Core Invariant: Protected routes reject missing, malformed, or wrong credentials with 401 and record valid logins in audit logs."""
    assert client.get("/api/patients").status_code == 401
    assert client.get("/api/dashboard/stats").status_code == 401

    bad_pw = client.post(
        "/api/auth/login",
        json={"email": "dr.sharma@medvault.edu", "password": "WrongPassword!"},
    )
    assert bad_pw.status_code == 401

    tampered = client.get(
        "/api/patients",
        headers={"Authorization": "Bearer tampered.jwt.token"},
    )
    assert tampered.status_code == 401

    good = client.post(
        "/api/auth/login",
        json={"email": "admin@medvault.edu", "password": "Admin@123"},
    )
    assert good.status_code == 200
    admin_headers = {"Authorization": f"Bearer {good.json()['access_token']}"}
    logs = client.get("/api/auth/audit-logs?limit=10", headers=admin_headers)
    assert logs.status_code == 200
    assert any(entry["action"] == "USER_LOGIN" for entry in logs.json())


def test_patient_crud_and_validation_boundaries(client: TestClient, auth_headers: dict[str, str]):
    """Core Invariant: Patient registration enforces non-empty demographics and valid sex, assigns unique MRNs, and rejects unknown IDs with 404."""
    blank_name = client.post(
        "/api/patients",
        json={
            "first_name": "   ",
            "last_name": "Test",
            "date_of_birth": "1995-03-10",
            "sex": "Female",
            "phone": "+91-98000-11111",
        },
        headers=auth_headers,
    )
    assert blank_name.status_code == 422

    invalid_sex = client.post(
        "/api/patients",
        json={
            "first_name": "Invalid",
            "last_name": "Sex",
            "date_of_birth": "1995-03-10",
            "sex": "Unknown",
            "phone": "+91-98000-11111",
        },
        headers=auth_headers,
    )
    assert invalid_sex.status_code == 422

    assert client.get("/api/patients/999999", headers=auth_headers).status_code == 404

    created = client.post(
        "/api/patients",
        json={
            "first_name": "Siddharth",
            "last_name": "Kapoor",
            "date_of_birth": "1994-08-21",
            "sex": "Male",
            "blood_group": "B+",
            "phone": "+91-98111-22334",
            "email": "siddharth.demo@synthetic-clinic.org",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    pat = created.json()
    assert pat["mrn"].startswith("MRN-")

    updated = client.put(
        f"/api/patients/{pat['id']}",
        json={"blood_group": "O+", "address": "Saket, New Delhi"},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["blood_group"] == "O+"
    assert updated.json()["address"] == "Saket, New Delhi"


def test_visit_creation_and_sql_aggregation_invariant(client: TestClient, auth_headers: dict[str, str]):
    """Core Invariant: Visit creation enforces vital-sign bounds and increments SQL GROUP BY dashboard counts monotonically."""
    before_dash = client.get("/api/dashboard/stats", headers=auth_headers).json()
    before_visits = before_dash["counts"]["total_visits"]

    pats = client.get("/api/patients?q=Siddharth", headers=auth_headers).json()
    assert len(pats) >= 1
    patient_id = pats[0]["id"]

    invalid_spo2 = client.post(
        f"/api/patients/{patient_id}/visits",
        json={
            "visit_type": "OPD",
            "chief_complaint": "Routine checkup",
            "vitals_spo2": 150,
        },
        headers=auth_headers,
    )
    assert invalid_spo2.status_code == 422

    created_visit = client.post(
        f"/api/patients/{patient_id}/visits",
        json={
            "visit_type": "OPD",
            "chief_complaint": "Acute seasonal fever and dry cough",
            "vitals_bp": "120/78 mmHg",
            "vitals_hr": 84,
            "vitals_spo2": 98,
            "treatment_plan": "Hydration and symptomatic antipyretic.",
            "symptoms": [{"name": "Dry Cough", "severity": "Moderate", "duration_days": 3}],
            "diagnoses": [{"condition_name": "Viral Upper Respiratory Infection", "icd10_code": "J06.9", "status": "Confirmed"}],
            "prescriptions": [{"medication_name": "Paracetamol", "strength": "500mg", "dosage": "1 tab", "frequency": "TID", "duration_days": 5}],
            "clinical_notes": [{"note_type": "SOAP", "content": "Afebrile in clinic. Chest clear."}],
        },
        headers=auth_headers,
    )
    assert created_visit.status_code == 201
    assert len(created_visit.json()["symptoms"]) == 1
    assert len(created_visit.json()["diagnoses"]) == 1

    after_dash = client.get("/api/dashboard/stats", headers=auth_headers).json()
    assert after_dash["counts"]["total_visits"] == before_visits + 1
    assert len(after_dash["top_conditions"]) > 0
    assert len(after_dash["top_symptoms"]) > 0


def test_ai_summary_citation_grounding_and_cache_invalidation(client: TestClient, auth_headers: dict[str, str]):
    """Core Invariant: AI summaries achieve 100% verified citation grounding, flag missing or revised data, and invalidate cache on record mutation."""
    aarav = client.get("/api/patients?q=Aarav", headers=auth_headers).json()[0]
    aarav_summary = client.get(f"/api/ai/patients/{aarav['id']}/summary", headers=auth_headers).json()
    assert aarav_summary["validation_stats"]["unverified_citations_dropped"] == 0
    assert aarav_summary["validation_stats"]["grounding_score"] == 1.0
    assert any("Recurring 'Recurring Headache'" in s["text"] for s in aarav_summary["recurring_symptoms"])
    assert any("Diagnostic Status Evolution" in s["text"] for s in aarav_summary["data_gaps_and_conflicts"])

    zoya = client.get("/api/patients?q=Zoya", headers=auth_headers).json()[0]
    zoya_summary = client.get(f"/api/ai/patients/{zoya['id']}/summary", headers=auth_headers).json()
    assert any("blood group is not recorded" in s["text"].lower() for s in zoya_summary["data_gaps_and_conflicts"])

    # Verify cache is invalidated when an allergy is added to a patient
    siddharth = client.get("/api/patients?q=Siddharth", headers=auth_headers).json()[0]
    first_sum = client.get(f"/api/ai/patients/{siddharth['id']}/summary", headers=auth_headers).json()
    assert first_sum["cached"] is False

    cached_sum = client.get(f"/api/ai/patients/{siddharth['id']}/summary", headers=auth_headers).json()
    assert cached_sum["cached"] is True

    add_allergy = client.post(
        f"/api/patients/{siddharth['id']}/allergies",
        json={"allergen": "Latex", "reaction": "Contact dermatitis", "severity": "Mild", "status": "Active"},
        headers=auth_headers,
    )
    assert add_allergy.status_code == 201

    refreshed_sum = client.get(f"/api/ai/patients/{siddharth['id']}/summary", headers=auth_headers).json()
    assert refreshed_sum["cached"] is False
    assert any("Latex" in s["text"] for s in refreshed_sum["allergies_and_alerts"])


def test_ai_natural_language_retrieval_and_zero_hallucination_guard(client: TestClient, auth_headers: dict[str, str]):
    """Core Invariant: Natural-language retrieval returns ranked source records for present terms and explicitly refuses unavailable terms."""
    aarav_id = client.get("/api/patients?q=Aarav", headers=auth_headers).json()[0]["id"]

    headache_res = client.post(
        "/api/ai/query",
        json={"query": "Find previous records mentioning recurring headaches", "patient_id": aarav_id},
        headers=auth_headers,
    )
    assert headache_res.status_code == 200
    assert headache_res.json()["total_matches"] > 0
    assert len(headache_res.json()["retrieved_records"]) > 0

    unavailable_res = client.post(
        "/api/ai/query",
        json={"query": "Find previous records mentioning Ebola hemorrhagic fever", "patient_id": aarav_id},
        headers=auth_headers,
    )
    assert unavailable_res.status_code == 200
    assert unavailable_res.json()["total_matches"] == 0
    assert "No matching clinical records" in unavailable_res.json()["direct_summary"]

    empty_res = client.post("/api/ai/query", json={"query": "   "}, headers=auth_headers)
    assert empty_res.status_code == 400


def test_clinical_note_entity_extraction_boundaries(client: TestClient, auth_headers: dict[str, str]):
    """Core Invariant: SOAP note entity extraction identifies symptoms, diagnoses, and medications while rejecting blank input with 400."""
    blank = client.post("/api/ai/extract-note", json={"note_text": "   "}, headers=auth_headers)
    assert blank.status_code == 400

    note = client.post(
        "/api/ai/extract-note",
        json={
            "note_text": (
                "Patient reports severe throbbing headache and photophobia for 2 days. "
                "Suspected migraine with aura. Prescribed Sumatriptan 50mg PRN. Follow up in 2 weeks."
            )
        },
        headers=auth_headers,
    )
    assert note.status_code == 200
    body = note.json()
    assert any("Headache" in s["name"] for s in body["extracted_symptoms"])
    assert any("Migraine" in d["condition_name"] for d in body["suspected_diagnoses"])
    assert any("Sumatriptan" in m["medication"] for m in body["mentioned_medications"])
