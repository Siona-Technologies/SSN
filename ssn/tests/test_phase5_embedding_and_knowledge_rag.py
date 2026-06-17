# ssn/tests/test_phase5_embedding_and_knowledge_rag.py

import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib import request as urllib_request

from ssn.core.embedding_providers import (
    DeterministicHashEmbedding,
    EmbeddingRequest,
    HttpEmbeddingProvider,
    cosine_similarity,
    get_default_embedding_provider_from_env,
)
from ssn.knowledge.store import KnowledgeStore
from ssn.knowledge.vector_index import VectorIndex, sidecar_path_for

ROOT = Path(__file__).resolve().parents[2]


class TestPhase5EmbeddingProviders(unittest.TestCase):
    def test_deterministic_hash_is_stable(self):
        p = DeterministicHashEmbedding(dim=32)
        a = p.embed(EmbeddingRequest(text="SIONA knowledge retrieval"))
        b = p.embed(EmbeddingRequest(text="SIONA knowledge retrieval"))
        self.assertEqual(a.vector, b.vector)
        self.assertEqual(len(a.vector), 32)

    def test_deterministic_hash_differs_for_different_text(self):
        p = DeterministicHashEmbedding(dim=32)
        a = p.embed(EmbeddingRequest(text="alpha"))
        b = p.embed(EmbeddingRequest(text="beta"))
        self.assertNotEqual(a.vector, b.vector)

    def test_cosine_identical_vectors(self):
        v = [0.1, 0.2, 0.3]
        self.assertAlmostEqual(cosine_similarity(v, v), 1.0, places=5)

    def test_default_provider_offline_is_deterministic(self):
        os.environ["SSN_EMBEDDING_PROVIDER"] = "deterministic"
        p = get_default_embedding_provider_from_env()
        self.assertEqual(p.name, "ssn-deterministic-hash-v1")


class TestPhase5KnowledgeStoreRAG(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmpdir.name, "knowledge.jsonl")
        self._write_records(
            [
                {
                    "kid": "k_py",
                    "title": "Python language",
                    "text": "Python is a general-purpose programming language used for automation and data science.",
                    "tags": ["python", "programming"],
                    "created_at": 1.0,
                },
                {
                    "kid": "k_js",
                    "title": "JavaScript",
                    "text": "JavaScript runs in web browsers and powers interactive frontend applications.",
                    "tags": ["javascript", "web"],
                    "created_at": 2.0,
                },
                {
                    "kid": "k_fruit",
                    "title": "Bananas",
                    "text": "Bananas are yellow tropical fruit rich in potassium.",
                    "tags": ["food"],
                    "created_at": 3.0,
                },
            ]
        )

    def tearDown(self):
        self._tmpdir.cleanup()

    def _write_records(self, records):
        with open(self.path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")

    def test_deterministic_search_is_repeatable(self):
        store = KnowledgeStore(
            self.path,
            embedding_provider=DeterministicHashEmbedding(dim=32),
        )
        a = store.search(query="python programming", top_k=3)
        b = store.search(query="python programming", top_k=3)
        self.assertTrue(a["ok"])
        self.assertTrue(b["ok"])
        self.assertEqual(a["results"], b["results"])
        self.assertEqual(a["search_mode"], "deterministic_embedding")

    def test_deterministic_search_finds_python_record(self):
        store = KnowledgeStore(
            self.path,
            embedding_provider=DeterministicHashEmbedding(dim=32),
        )
        out = store.search(query="python programming", top_k=3)
        kids = [r.get("kid") for r in out.get("results", [])]
        self.assertIn("k_py", kids)

    def test_vector_sidecar_written(self):
        store = KnowledgeStore(
            self.path,
            embedding_provider=DeterministicHashEmbedding(dim=32),
        )
        store.search(query="python", top_k=2)
        sidecar = sidecar_path_for(self.path)
        self.assertTrue(os.path.exists(sidecar))
        idx = VectorIndex(sidecar, provider_name="ssn-deterministic-hash-v1", dim=32)
        self.assertIsNotNone(idx.get("k_py"))


class TestPhase5HttpEmbeddingIntegration(unittest.TestCase):
    def setUp(self):
        from ssn.runtime.mock_embed_server import MockEmbedHandler

        self._tmpdir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmpdir.name, "knowledge.jsonl")
        records = [
            {
                "kid": "k_py",
                "title": "Python language",
                "text": "Python is a general-purpose programming language used for automation and data science.",
                "tags": ["python"],
                "created_at": 1.0,
            },
            {
                "kid": "k_js",
                "title": "JavaScript",
                "text": "JavaScript runs in web browsers and powers interactive frontend applications.",
                "tags": ["javascript"],
                "created_at": 2.0,
            },
            {
                "kid": "k_fruit",
                "title": "Bananas",
                "text": "Bananas are yellow tropical fruit rich in potassium.",
                "tags": ["food"],
                "created_at": 3.0,
            },
        ]
        with open(self.path, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), MockEmbedHandler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = f"http://127.0.0.1:{self.port}/embed"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self._tmpdir.cleanup()

    def test_http_provider_reaches_mock_server(self):
        provider = HttpEmbeddingProvider(endpoint=self.endpoint)
        out = provider.embed(EmbeddingRequest(text="python programming language"))
        self.assertEqual(len(out.vector), 64)
        self.assertFalse(out.meta.get("fallback"))

    def test_http_search_ranks_python_for_programming_query(self):
        provider = HttpEmbeddingProvider(endpoint=self.endpoint)
        store = KnowledgeStore(self.path, embedding_provider=provider)
        out = store.search(query="general purpose programming language", top_k=3)
        self.assertTrue(out["ok"])
        self.assertEqual(out["search_mode"], "http_embedding")
        self.assertGreater(len(out["results"]), 0)
        self.assertEqual(out["results"][0]["kid"], "k_py")

    def test_mock_embed_server_health(self):
        with urllib_request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("ok"))


if __name__ == "__main__":
    unittest.main()
