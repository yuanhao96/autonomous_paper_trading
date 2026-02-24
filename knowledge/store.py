"""ChromaDB wrapper for semantic knowledge storage."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import chromadb
from chromadb.config import Settings


@dataclass
class Document:
    """A knowledge document to be stored in the vector database."""

    title: str
    content: str
    source: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    topic_tags: list[str] = field(default_factory=list)


# Predefined collection names aligned with the curriculum stages.
CURRICULUM_COLLECTIONS: list[str] = [
    "general",
    "stage_1_foundations",
    "stage_2_strategies",
    "stage_3_risk_management",
    "stage_4_advanced",
]


class KnowledgeStore:
    """Persistent semantic knowledge store backed by ChromaDB.

    Documents are embedded and stored in named collections. Each collection
    maps to a curriculum stage (or "general" for uncategorised content).
    Metadata fields are kept as scalars because ChromaDB metadata values
    must be ``str | int | float | bool``.
    """

    def __init__(self, persist_dir: str = "data/knowledge_base") -> None:
        self._client: chromadb.ClientAPI = chromadb.Client(
            Settings(
                persist_directory=persist_dir,
                is_persistent=True,
                anonymized_telemetry=False,
            )
        )
        self._persist_dir: str = persist_dir

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def _get_or_create_collection(self, name: str) -> chromadb.Collection:
        """Return an existing collection or create a new one."""
        return self._client.get_or_create_collection(name=name)

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def add_document(
        self,
        doc: Document,
        collection_name: str = "general",
    ) -> str:
        """Add a document to the specified collection.

        Parameters
        ----------
        doc:
            The ``Document`` to store.
        collection_name:
            Target collection (default ``"general"``).

        Returns
        -------
        str
            The generated document ID.
        """
        collection = self._get_or_create_collection(collection_name)

        doc_id: str = uuid.uuid4().hex

        metadata: dict[str, str] = {
            "title": doc.title,
            "source": doc.source,
            "timestamp": doc.timestamp,
            "topic_tags": ",".join(doc.topic_tags),
        }

        collection.add(
            ids=[doc_id],
            documents=[doc.content],
            metadatas=[metadata],
        )

        return doc_id

    def query(
        self,
        query_text: str,
        collection_name: str = "general",
        n_results: int = 5,
    ) -> list[dict[str, object]]:
        """Perform a semantic similarity search.

        Parameters
        ----------
        query_text:
            Natural-language query string.
        collection_name:
            Collection to search in.
        n_results:
            Maximum number of results to return.

        Returns
        -------
        list[dict[str, object]]
            Each dict contains ``id``, ``content``, ``metadata``, and
            ``distance`` keys.
        """
        collection = self._get_or_create_collection(collection_name)

        # Guard against querying an empty collection.
        if collection.count() == 0:
            return []

        # Clamp n_results to the number of documents in the collection.
        effective_n: int = min(n_results, collection.count())

        results = collection.query(
            query_texts=[query_text],
            n_results=effective_n,
        )

        output: list[dict[str, object]] = []
        ids: list[str] = results["ids"][0] if results["ids"] else []
        documents: list[str] = results["documents"][0] if results["documents"] else []
        metadatas: list[dict[str, str]] = results["metadatas"][0] if results["metadatas"] else []
        distances: list[float] = results["distances"][0] if results["distances"] else []

        for i, doc_id in enumerate(ids):
            output.append(
                {
                    "id": doc_id,
                    "content": documents[i] if i < len(documents) else "",
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "distance": distances[i] if i < len(distances) else 0.0,
                }
            )

        return output

    def list_by_topic(
        self,
        topic: str,
        collection_name: str = "general",
    ) -> list[dict[str, object]]:
        """Return all documents whose ``topic_tags`` metadata contains *topic*.

        ChromaDB stores ``topic_tags`` as a comma-separated string, so we
        use the ``$contains`` operator to filter.

        Parameters
        ----------
        topic:
            The topic tag to filter on (case-sensitive substring match
            against the comma-separated ``topic_tags`` field).
        collection_name:
            Collection to search in.

        Returns
        -------
        list[dict[str, object]]
            Each dict contains ``id``, ``content``, and ``metadata`` keys.
        """
        collection = self._get_or_create_collection(collection_name)

        if collection.count() == 0:
            return []

        # ChromaDB $contains on string metadata is unreliable across
        # versions, so we fetch all documents and filter in Python.
        results = collection.get()

        output: list[dict[str, object]] = []
        ids: list[str] = results["ids"] if results["ids"] else []
        documents: list[str] = (
            results["documents"] if results["documents"] else []
        )
        metadatas: list[dict[str, str]] = (
            results["metadatas"] if results["metadatas"] else []
        )

        for i, doc_id in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) else {}
            tags_str = meta.get("topic_tags", "")
            if topic not in tags_str:
                continue
            output.append(
                {
                    "id": doc_id,
                    "content": documents[i] if i < len(documents) else "",
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                }
            )

        return output

    def get_collection_names(self) -> list[str]:
        """Return the names of all collections that currently exist."""
        collections = self._client.list_collections()
        return [c.name for c in collections]

    def count(self, collection_name: str = "general") -> int:
        """Return the number of documents in the given collection.

        Returns ``0`` if the collection does not exist yet.
        """
        try:
            collection = self._client.get_collection(name=collection_name)
        except (ValueError, Exception):
            # ChromaDB raises NotFoundError (or ValueError in some versions)
            # when the collection does not exist.
            return 0
        return collection.count()
