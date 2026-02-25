"""Vector store for vet data — ChromaDB-based similarity search.

Loads vet data on startup from either:
1. A pre-embedded ``vectorstore.json`` file (saves embedding API costs)
2. Live fetch from vets-service (``GET /vets``) if no file exists

Provides ``search_vets()`` for similarity search used by the listVets tool.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import anyio
import chromadb
from loguru import logger

if TYPE_CHECKING:
    import httpx

# Configurable vets-service URL (overridden by settings or tests)
VETS_SERVICE_URL = "http://localhost:8083"

# Path to pre-embedded vet data file
VECTORSTORE_FILE = "vectorstore.json"

# Module-level state
_collection: chromadb.Collection | None = None
_initialized: bool = False


def _get_or_create_collection() -> chromadb.Collection:
    """Create a ChromaDB ephemeral collection for vet data."""
    client = chromadb.EphemeralClient()
    return client.get_or_create_collection("vets")


async def initialize(
    http_client: httpx.AsyncClient | None = None,
) -> None:
    """Load vet data into the vector store.

    Tries ``vectorstore.json`` first.  Falls back to fetching from vets-service.
    Idempotent — subsequent calls are no-ops.
    """
    global _collection, _initialized  # noqa: PLW0603

    if _initialized:
        return

    _collection = _get_or_create_collection()

    # Try loading from pre-embedded file
    try:
        raw = await anyio.Path(VECTORSTORE_FILE).read_text()
        data: list[dict[str, str]] = json.loads(raw)

        documents = [item["content"] for item in data]
        ids = [str(i) for i in range(len(documents))]
        _collection.add(documents=documents, ids=ids)
        logger.info("Vector store loaded {} vets from {}", len(documents), VECTORSTORE_FILE)
        _initialized = True
        return
    except FileNotFoundError:
        logger.debug("No {} found, fetching from vets-service", VECTORSTORE_FILE)

    # Fetch from vets-service
    if http_client is None:
        import httpx as httpx_mod

        http_client = httpx_mod.AsyncClient(timeout=10.0)

    resp = await http_client.get(f"{VETS_SERVICE_URL}/vets")
    resp.raise_for_status()
    vets: list[dict[str, object]] = resp.json()

    documents = [json.dumps(vet) for vet in vets]
    ids = [str(i) for i in range(len(documents))]
    _collection.add(documents=documents, ids=ids)
    logger.info("Vector store loaded {} vets from vets-service", len(documents))
    _initialized = True


async def search_vets(vet_filter: dict[str, object] | None) -> list[str]:
    """Similarity search for vets based on filter criteria.

    Args:
        vet_filter: Dict with optional firstName, lastName, specialties keys.
                    Pass None for unfiltered search.

    Returns:
        List of vet document strings matching the query.
    """
    if _collection is None or not _initialized:
        logger.warning("Vector store not initialized, returning empty results")
        return []

    query = json.dumps(vet_filter) if vet_filter else "{}"
    top_k = 20 if vet_filter else 50

    results = _collection.query(
        query_texts=[query],
        n_results=top_k,
    )

    docs = results.get("documents") or [[]]
    return docs[0] if docs else []
