def test_ingest_document_creates_job(client):
    test_client, container = client

    response = test_client.post(
        "/api/v1/documents:ingest",
        files={"file": ("guide.txt", b"hello world", "text/plain")},
    )

    body = response.json()
    assert response.status_code == 202
    assert body["document_id"] == "doc-1"
    assert body["job_id"] == "job-1"
    assert container.processing_service.processed == [("doc-1", "job-1")]


def test_ingest_document_rejects_unsupported_files(client):
    test_client, _ = client

    response = test_client.post(
        "/api/v1/documents:ingest",
        files={"file": ("guide.exe", b"hello world", "application/octet-stream")},
    )

    assert response.status_code == 415
    assert "Unsupported file type" in response.json()["detail"]


def test_get_document_returns_metadata(client):
    test_client, _ = client
    upload = test_client.post(
        "/api/v1/documents:ingest",
        files={"file": ("guide.csv", b"name,role\nWassim,developer", "text/csv")},
    ).json()

    response = test_client.get(f"/api/v1/documents/{upload['document_id']}")
    body = response.json()

    assert response.status_code == 200
    assert body["filename"] == "guide.csv"
    assert body["extension"] == ".csv"


def test_chat_completion_returns_sources(client):
    test_client, _ = client

    response = test_client.post(
        "/api/v1/chat/completions",
        json={"message": "What does the guide say?", "history": []},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["model"] == "fake-model"
    assert body["sources"][0]["filename"] == "guide.txt"


def test_debug_prompt_endpoint_returns_current_prompt(client):
    test_client, _ = client

    response = test_client.get("/api/v1/debug/prompt")
    body = response.json()

    assert response.status_code == 200
    assert body["source"] == "code"
    assert sorted(body["input_variables"]) == ["context", "question"]
    assert body["messages"][0]["role"] == "system"
    assert "Tunisian Darija" in body["messages"][0]["content"]


def test_ready_endpoint_reports_dependency_status(client):
    test_client, _ = client

    response = test_client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_viewer_overview_returns_documents_and_chunks(client):
    test_client, _ = client

    response = test_client.get("/api/v1/viewer/overview")
    body = response.json()

    assert response.status_code == 200
    assert body["collection_name"] == "knowledge_base"
    assert body["documents"][0]["filename"] == "guide.txt"
    assert body["chunks"][0]["document_id"] == "doc-1"


def test_viewer_page_renders(client):
    test_client, _ = client

    response = test_client.get("/viewer")

    assert response.status_code == 200
    assert "Inspect what reached Qdrant" in response.text


def test_qdrant_documents_endpoint_returns_unique_documents(client):
    test_client, _ = client

    response = test_client.get("/api/v1/qdrant/documents")
    body = response.json()

    assert response.status_code == 200
    assert body["collection_name"] == "knowledge_base"
    assert body["total_documents"] == 1
    assert body["total_chunks"] == 3
    assert body["documents"][0]["document_id"] == "doc-1"
    assert body["documents"][0]["filename"] == "guide.txt"
    assert body["documents"][0]["chunk_count"] == 3


def test_qdrant_questions_endpoint_returns_questions(client):
    test_client, _ = client

    response = test_client.get("/api/v1/qdrant/questions")
    body = response.json()

    assert response.status_code == 200
    assert body["collection_name"] == "knowledge_base"
    assert body["total_questions"] == 1
    assert body["questions"][0]["id"] == "faq-1"
    assert body["questions"][0]["question"] == "How do I reset my password?"
    assert body["questions"][0]["score"] is None


def test_qdrant_questions_endpoint_supports_query_search(client):
    test_client, _ = client

    test_client.post(
        "/api/v1/qdrant/questions",
        json={"question": "Where is my order?", "answer": "Check the orders page."},
    )

    response = test_client.get("/api/v1/qdrant/questions", params={"query": "track order"})
    body = response.json()

    assert response.status_code == 200
    assert body["total_questions"] == 1
    assert body["questions"][0]["question"] == "Where is my order?"
    assert body["questions"][0]["score"] == 1.0


def test_create_qdrant_question(client):
    test_client, _ = client

    response = test_client.post(
        "/api/v1/qdrant/questions",
        json={"question": "Where is my order?", "answer": "Check the orders page."},
    )
    body = response.json()

    assert response.status_code == 201
    assert body["question"] == "Where is my order?"
    assert body["source_type"] == "faq_editor"


def test_update_qdrant_question(client):
    test_client, _ = client

    response = test_client.put(
        "/api/v1/qdrant/questions/faq-1",
        json={"question": "How do I update my password?", "answer": "Use profile settings."},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["id"] == "faq-1"
    assert body["question"] == "How do I update my password?"
    assert body["answer"] == "Use profile settings."


def test_delete_qdrant_question(client):
    test_client, _ = client

    response = test_client.delete("/api/v1/qdrant/questions/faq-1")

    assert response.status_code == 204

    list_response = test_client.get("/api/v1/qdrant/questions").json()
    assert list_response["total_questions"] == 0
