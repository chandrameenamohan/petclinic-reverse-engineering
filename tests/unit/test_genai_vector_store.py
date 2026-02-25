"""Unit tests for GenAI vector store — vet data loading + similarity search."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestInitializeFromFile:
    """Test loading vet data from vectorstore.json."""

    @pytest.fixture(autouse=True)
    def _reset_collection(self):
        """Reset the vector store collection before each test."""
        import genai_service.vector_store as vs

        vs._collection = None
        vs._initialized = False
        yield
        vs._collection = None
        vs._initialized = False

    async def test_loads_from_vectorstore_json_when_file_exists(self):
        import genai_service.vector_store as vs

        file_data = [
            {"content": '{"firstName": "James", "lastName": "Carter", "specialties": []}'},
            {"content": '{"firstName": "Helen", "lastName": "Leary"}'},
        ]
        mock_collection = MagicMock()
        mock_anyio_path = AsyncMock()
        mock_anyio_path.read_text = AsyncMock(return_value=json.dumps(file_data))

        with (
            patch("genai_service.vector_store.anyio.Path", return_value=mock_anyio_path),
            patch.object(vs, "_get_or_create_collection", return_value=mock_collection),
        ):
            await vs.initialize()

        mock_collection.add.assert_called_once()
        call_kwargs = mock_collection.add.call_args.kwargs
        assert len(call_kwargs["documents"]) == 2
        assert vs._initialized is True

    async def test_does_not_fetch_from_service_when_file_exists(self):
        import genai_service.vector_store as vs

        file_data = [{"content": '{"firstName": "James"}'}]
        mock_collection = MagicMock()
        mock_http = AsyncMock()
        mock_anyio_path = AsyncMock()
        mock_anyio_path.read_text = AsyncMock(return_value=json.dumps(file_data))

        with (
            patch("genai_service.vector_store.anyio.Path", return_value=mock_anyio_path),
            patch.object(vs, "_get_or_create_collection", return_value=mock_collection),
        ):
            await vs.initialize(http_client=mock_http)

        mock_http.get.assert_not_called()


class TestInitializeFromService:
    """Test loading vet data from vets-service when file is absent."""

    @pytest.fixture(autouse=True)
    def _reset_collection(self):
        import genai_service.vector_store as vs

        vs._collection = None
        vs._initialized = False
        yield
        vs._collection = None
        vs._initialized = False

    async def test_fetches_from_vets_service_when_no_file(self):
        import genai_service.vector_store as vs

        vets_data = [
            {"firstName": "James", "lastName": "Carter", "specialties": []},
            {"firstName": "Helen", "lastName": "Leary", "specialties": [{"name": "radiology"}]},
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = vets_data
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_collection = MagicMock()
        mock_anyio_path = AsyncMock()
        mock_anyio_path.read_text = AsyncMock(side_effect=FileNotFoundError)

        with (
            patch("genai_service.vector_store.anyio.Path", return_value=mock_anyio_path),
            patch.object(vs, "_get_or_create_collection", return_value=mock_collection),
        ):
            await vs.initialize(http_client=mock_http)

        mock_http.get.assert_called_once()
        mock_collection.add.assert_called_once()
        call_kwargs = mock_collection.add.call_args.kwargs
        docs = call_kwargs["documents"]
        assert len(docs) == 2
        # Each doc should be JSON-serialized vet
        assert json.loads(docs[0])["firstName"] == "James"

    async def test_uses_configured_vets_url(self):
        import genai_service.vector_store as vs

        vs.VETS_SERVICE_URL = "http://custom-host:9999"
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)
        mock_collection = MagicMock()
        mock_anyio_path = AsyncMock()
        mock_anyio_path.read_text = AsyncMock(side_effect=FileNotFoundError)

        with (
            patch("genai_service.vector_store.anyio.Path", return_value=mock_anyio_path),
            patch.object(vs, "_get_or_create_collection", return_value=mock_collection),
        ):
            await vs.initialize(http_client=mock_http)

        mock_http.get.assert_called_once_with("http://custom-host:9999/vets")
        vs.VETS_SERVICE_URL = "http://localhost:8083"

    async def test_initialize_is_idempotent(self):
        """Calling initialize() twice should not reload data."""
        import genai_service.vector_store as vs

        file_data = [{"content": '{"firstName": "James"}'}]
        mock_collection = MagicMock()
        mock_anyio_path = AsyncMock()
        mock_anyio_path.read_text = AsyncMock(return_value=json.dumps(file_data))

        with (
            patch("genai_service.vector_store.anyio.Path", return_value=mock_anyio_path),
            patch.object(vs, "_get_or_create_collection", return_value=mock_collection),
        ):
            await vs.initialize()
            await vs.initialize()

        # Should only add once
        assert mock_collection.add.call_count == 1


class TestSearchVets:
    """Test similarity search functionality."""

    @pytest.fixture(autouse=True)
    def _reset_and_set_collection(self):
        import genai_service.vector_store as vs

        self.mock_collection = MagicMock()
        vs._collection = self.mock_collection
        vs._initialized = True
        yield
        vs._collection = None
        vs._initialized = False

    async def test_search_with_no_filter_uses_top_k_50(self):
        import genai_service.vector_store as vs

        self.mock_collection.query.return_value = {
            "documents": [['{"firstName": "James"}']],
        }

        results = await vs.search_vets(None)

        self.mock_collection.query.assert_called_once()
        call_kwargs = self.mock_collection.query.call_args.kwargs
        assert call_kwargs["n_results"] == 50
        assert len(results) == 1

    async def test_search_with_filter_uses_top_k_20(self):
        import genai_service.vector_store as vs

        self.mock_collection.query.return_value = {
            "documents": [['{"firstName": "Helen"}']],
        }

        results = await vs.search_vets({"specialties": [{"name": "radiology"}]})

        call_kwargs = self.mock_collection.query.call_args.kwargs
        assert call_kwargs["n_results"] == 20
        assert len(results) == 1

    async def test_search_returns_empty_list_when_no_results(self):
        import genai_service.vector_store as vs

        self.mock_collection.query.return_value = {"documents": [[]]}

        results = await vs.search_vets(None)
        assert results == []

    async def test_search_query_text_is_json_of_filter(self):
        import genai_service.vector_store as vs

        self.mock_collection.query.return_value = {"documents": [[]]}
        vet_filter = {"firstName": "Helen"}

        await vs.search_vets(vet_filter)

        call_kwargs = self.mock_collection.query.call_args.kwargs
        assert call_kwargs["query_texts"] == [json.dumps(vet_filter)]

    async def test_search_with_none_filter_queries_empty_json(self):
        import genai_service.vector_store as vs

        self.mock_collection.query.return_value = {"documents": [[]]}

        await vs.search_vets(None)

        call_kwargs = self.mock_collection.query.call_args.kwargs
        assert call_kwargs["query_texts"] == ["{}"]

    async def test_search_before_initialize_returns_empty(self):
        """If search is called before initialization, return empty list gracefully."""
        import genai_service.vector_store as vs

        vs._collection = None
        vs._initialized = False

        results = await vs.search_vets(None)
        assert results == []
