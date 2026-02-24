"""OpenClaw tool: query the trading knowledge base.

Stub — actual OpenClaw integration happens on the target machine.
"""

from __future__ import annotations

from knowledge.store import MarkdownMemory

TOOL_SCHEMA: dict = {
    "name": "query_knowledge",
    "description": "Query the trading knowledge base",
    "parameters": {
        "query": {
            "type": "str",
            "description": "Natural language query to search the knowledge base",
            "required": True,
        },
        "scope": {
            "type": "str",
            "description": (
                "Scope to search in: 'curriculum', 'discovered', 'daily_log', "
                "or 'all' (default)."
            ),
            "required": False,
        },
    },
}

_SCOPE_DIR: dict[str, str | None] = {
    "curriculum": "curriculum",
    "discovered": "discovered",
    "daily_log": "daily_log",
    "all": None,
}


async def handle(params: dict) -> str:
    """Query the knowledge base and return formatted results.

    Performs a BM25 full-text search over markdown memory files and
    formats the results as a readable string.
    """
    query_text = params.get("query")
    if not query_text:
        return "Error: 'query' parameter is required."

    scope = params.get("scope", "all")
    subdirectory = _SCOPE_DIR.get(scope)

    try:
        memory = MarkdownMemory()
        results = memory.search(
            query=query_text,
            subdirectory=subdirectory,
            n_results=5,
        )

        if not results:
            return (
                f"No results found for query '{query_text}' "
                f"in scope '{scope}'."
            )

        lines: list[str] = [
            "=== Knowledge Base Results ===",
            f"Query: {query_text}",
            f"Scope: {scope}",
            f"Results: {len(results)}",
            "",
        ]

        for i, result in enumerate(results, 1):
            metadata = result.get("metadata", {})
            topic = metadata.get("topic_id", metadata.get("topic", "Unknown"))
            score = result.get("score", 0.0)
            content = str(result.get("content", ""))

            max_content_len = 500
            if len(content) > max_content_len:
                content = content[:max_content_len] + "..."

            lines.extend([
                f"--- Result {i} (score: {score:.4f}) ---",
                f"Topic: {topic}",
                f"Path:  {result.get('path', '')}",
                "Content:",
                content,
                "",
            ])

        return "\n".join(lines)

    except Exception as exc:
        return f"Error querying knowledge base: {exc}"
