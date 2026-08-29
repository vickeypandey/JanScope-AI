from app.services.retrieval_service import HashingEmbedder


def test_hash_embeddings_are_stable_and_normalized():
    embedder = HashingEmbedder(64)
    first = embedder.embed("farmer support scheme")
    second = embedder.embed("farmer support scheme")
    assert first == second
    norm = sum(value * value for value in first) ** 0.5
    assert abs(norm - 1.0) < 1e-8


def test_grievance_draft_preserves_missing_fact_placeholders(client):
    response = client.post(
        "/api/v1/grievances/draft",
        json={
            "subject": "Delayed instalment",
            "department": "Agriculture Department",
            "problem_summary": "The latest expected instalment has not appeared in the bank account.",
            "language": "en",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["review_required"] is True
    assert "applicant_name" in payload["missing_information"]
    assert "[Enter full name]" in payload["draft"]
    assert payload["ai_mode"] == "demo"


def test_document_ingestion_and_retrieval_endpoint(client):
    text = (
        "PM-KISAN provides farmer income support. This test document explains registration, "
        "Aadhaar e-KYC, bank details, land records, and official verification requirements. " * 4
    )
    response = client.post(
        "/api/v1/documents/ingest",
        headers={"X-Admin-Key": "test-admin-key-not-for-production"},
        json={
            "scheme_slug": "pm-kisan",
            "title": "PM-KISAN test reference",
            "text": text,
            "source_url": "https://pmkisan.gov.in/",
        },
    )
    assert response.status_code == 201
    assert response.json()["chunks_created"] >= 1


def test_markdown_file_ingestion(client):
    content = (
        "# PM-KISAN verified note\n\nThis source note describes farmer registration, identity verification, "
        "bank details and official portal checking. " * 8
    ).encode("utf-8")
    response = client.post(
        "/api/v1/documents/ingest-file",
        headers={"X-Admin-Key": "test-admin-key-not-for-production"},
        data={
            "scheme_slug": "pm-kisan",
            "title": "Uploaded PM-KISAN note",
            "source_url": "https://pmkisan.gov.in/",
        },
        files={"document": ("pm-kisan.md", content, "text/markdown")},
    )
    assert response.status_code == 201
    assert response.json()["chunks_created"] >= 1
