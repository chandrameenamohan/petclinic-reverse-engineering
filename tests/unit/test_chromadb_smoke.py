"""Smoke test: verify chromadb dependency is installed and functional."""

import chromadb


def test_chromadb_ephemeral_client_creates_collection() -> None:
    client = chromadb.EphemeralClient()
    collection = client.create_collection("smoke_test")
    assert collection.name == "smoke_test"


def test_chromadb_add_and_query_documents() -> None:
    client = chromadb.EphemeralClient()
    collection = client.create_collection("vet_smoke")
    collection.add(
        documents=[
            '{"firstName": "James", "lastName": "Carter", "specialties": []}',
            '{"firstName": "Helen", "lastName": "Leary", "specialties": [{"name": "radiology"}]}',
        ],
        ids=["vet-1", "vet-2"],
    )
    results = collection.query(query_texts=["radiology specialist"], n_results=1)
    assert results["documents"] is not None
    assert len(results["documents"][0]) == 1
