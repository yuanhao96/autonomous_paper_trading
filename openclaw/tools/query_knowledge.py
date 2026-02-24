"""OpenClaw tool: query the trading knowledge base.

Stub — actual OpenClaw integration happens on the target machine.
"""

from __future__ import annotations

from knowledge.store import KnowledgeStore

TOOL_SCHEMA: dict = {
    "name": "query_knowledge",
    "description": "Query the trading knowledge base",
    "parameters": {
        "query": {
            "type": "str",
            "description": "Natural language query to search the knowledge base",
            "required": True,
        },
        "collection": {
            "type": "str",
            "description": (
                "Collection to search in (e.g. 'general', 'stage_1_foundations', "
                "'stage_2_strategies', 'stage_3_risk_management', 'stage_4_advanced'). "
                "Defaults to 'general'."
            ),
            "required": False,
        },
    },
}


async def handle(params: dict) -> str:
    """Query the knowledge base and return formatted results.

    Performs a semantic similarity search in the specified collection
    and formats the results as a readable string.
    """
    query_text = params.get("query")
    if not query_text:
        return "Error: 'query' parameter is required."

    collection = params.get("collection", "general")

    try:
        store = KnowledgeStore()
        results = store.query(
            query_text=query_text,
            collection_name=collection,
            n_results=5,
        )

        if not results:
            return (
                f"No results found for query '{query_text}' "
                f"in collection '{collection}'."
            )

        lines: list[str] = [
            "=== Knowledge Base Results ===",
            f"Query:      {query_text}",
            f"Collection: {collection}",
            f"Results:    {len(results)}",
            "",
        ]

        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            title = metadata.get("title", "Untitled") if isinstance(metadata, dict) else "Untitled"
            source = metadata.get("source", "Unknown") if isinstance(metadata, dict) else "Unknown"
            distance = result.get("distance", 0.0)
            content = str(result.get("content", ""))

            # Truncate long content for display.
            max_content_len = 500
            if len(content) > max_content_len:
                content = content[:max_content_len] + "..."

            lines.extend([
                f"--- Result {i} (distance: {distance:.4f}) ---",
                f"Title:  {title}",
                f"Source: {source}",
                "Content:",
                content,
                "",
            ])

        return "\n".join(lines)

    except Exception as exc:
        return f"Error querying knowledge base: {exc}"
