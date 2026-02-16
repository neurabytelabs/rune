"""
🔍 RUNE Search — Grimoire Search Engine
TF-IDF based semantic search for prompt library discovery.
"""

import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SearchResult:
    """A single search result with relevance scoring."""
    name: str
    path: str
    score: float
    title: str
    description: str
    snippet: str
    tags: list[str] = field(default_factory=list)


@dataclass
class PromptInfo:
    """Metadata about a prompt file in the library."""
    name: str
    path: str
    title: str
    description: str
    tags: list[str]
    size_bytes: int
    lines: int


# Common stop words for English and Turkish
STOP_WORDS: set[str] = {
    # English
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "was", "are",
    "were", "been", "has", "have", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "this", "that",
    "these", "those", "i", "you", "he", "she", "we", "they", "me", "him",
    "her", "us", "them", "my", "your", "his", "its", "our", "their",
    "what", "which", "who", "whom", "how", "when", "where", "why",
    "not", "no", "so", "if", "then", "than", "too", "very", "just",
    "about", "up", "out", "all", "also", "into", "over", "after",
    # Turkish
    "bir", "ve", "bu", "da", "de", "ile", "için", "gibi", "ama",
    "olan", "den", "dan", "mi", "mu", "mı", "ne", "ya", "en",
    "çok", "daha", "sonra", "önce", "kadar", "her", "o", "ben",
    "sen", "biz", "siz", "onlar", "şu", "ki", "ise", "olarak",
}


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Returns:
        Tuple of (metadata dict, body text without frontmatter).
    """
    if not content.startswith("---"):
        return {}, content

    end = content.find("---", 3)
    if end == -1:
        return {}, content

    front = content[3:end].strip()
    body = content[end + 3:].strip()
    meta: dict = {}

    for line in front.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if key == "tags":
            # Support both `tags: [a, b]` and `tags: a, b`
            value = value.strip("[]")
            meta[key] = [t.strip().strip("'\"") for t in value.split(",") if t.strip()]
        else:
            meta[key] = value.strip("'\"")

    return meta, body


class SearchEngine:
    """TF-IDF based search engine for a prompt library.

    Scans markdown files in the given directory, builds an inverted index,
    and supports ranked keyword search.

    Args:
        library_path: Root directory containing ``.md`` prompt files.
    """

    def __init__(self, library_path: str = "prompts"):
        self.library_path: str = library_path
        self.index: dict[str, dict[str, float]] = {}  # term -> {doc_id: tf-idf}
        self._docs: dict[str, dict] = {}  # doc_id -> {tokens, meta, path, content}
        self._build_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """Search prompts by query using TF-IDF ranking.

        Args:
            query: Free-text search query.
            top_k: Maximum number of results to return.

        Returns:
            List of :class:`SearchResult` sorted by descending relevance.
        """
        tokens = self._tokenize(query)
        if not tokens:
            return []

        scores: dict[str, float] = {}
        for term in tokens:
            if term not in self.index:
                continue
            for doc_id, tfidf in self.index[term].items():
                scores[doc_id] = scores.get(doc_id, 0.0) + tfidf

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results: list[SearchResult] = []
        for doc_id, score in ranked:
            doc = self._docs[doc_id]
            meta = doc["meta"]
            content_body = doc["content"]
            results.append(SearchResult(
                name=doc_id,
                path=doc["path"],
                score=round(score, 4),
                title=meta.get("title", doc_id),
                description=meta.get("description", ""),
                snippet=content_body[:200].replace("\n", " "),
                tags=meta.get("tags", []),
            ))

        return results

    def list_all(self) -> list[PromptInfo]:
        """List all prompts in the library.

        Returns:
            List of :class:`PromptInfo` for every indexed prompt.
        """
        infos: list[PromptInfo] = []
        for doc_id, doc in sorted(self._docs.items()):
            meta = doc["meta"]
            full_path = doc["path"]
            try:
                size = os.path.getsize(full_path)
            except OSError:
                size = 0
            infos.append(PromptInfo(
                name=doc_id,
                path=full_path,
                title=meta.get("title", doc_id),
                description=meta.get("description", ""),
                tags=meta.get("tags", []),
                size_bytes=size,
                lines=doc["content"].count("\n") + 1,
            ))
        return infos

    def get_prompt(self, name: str) -> str | None:
        """Get full content of a specific prompt by name.

        Args:
            name: Prompt identifier (filename stem).

        Returns:
            Raw file content or ``None`` if not found.
        """
        doc = self._docs.get(name)
        if doc is None:
            return None
        try:
            return Path(doc["path"]).read_text(encoding="utf-8")
        except OSError:
            return None

    def add_prompt(self, name: str, content: str, tags: list[str] | None = None) -> None:
        """Add a new prompt to the library and update the index.

        Creates a ``.md`` file with optional YAML frontmatter.

        Args:
            name: Prompt identifier (used as filename stem).
            content: Markdown body of the prompt.
            tags: Optional list of tags to include in frontmatter.
        """
        path = Path(self.library_path) / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)

        front = f"---\ntitle: {name}\n"
        if tags:
            front += f"tags: [{', '.join(tags)}]\n"
        front += "---\n\n"

        path.write_text(front + content, encoding="utf-8")
        self._index_file(str(path))

    def format_results(self, results: list[SearchResult]) -> str:
        """Format search results for terminal display.

        Args:
            results: List of search results to format.

        Returns:
            Human-readable string.
        """
        if not results:
            return "No results found."

        lines: list[str] = [f"🔍 Found {len(results)} result(s):\n"]
        for i, r in enumerate(results, 1):
            tag_str = ", ".join(r.tags) if r.tags else "—"
            lines.append(
                f"  {i}. [{r.score:.3f}] {r.title}\n"
                f"     {r.description}\n"
                f"     Tags: {tag_str}\n"
                f"     {r.snippet}…\n"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Indexing internals
    # ------------------------------------------------------------------

    def _build_index(self) -> None:
        """Scan all .md files in library_path and build the inverted index."""
        lib = Path(self.library_path)
        if not lib.exists():
            return

        for md_file in lib.rglob("*.md"):
            self._index_file(str(md_file))

        # Compute TF-IDF scores
        self.index.clear()
        for doc_id, doc in self._docs.items():
            tokens = doc["tokens"]
            if not tokens:
                continue
            seen: set[str] = set()
            for term in tokens:
                if term in seen:
                    continue
                seen.add(term)
                tf = self._tf(term, tokens)
                idf = self._idf(term)
                self.index.setdefault(term, {})[doc_id] = tf * idf

    def _index_file(self, filepath: str) -> None:
        """Index a single markdown file."""
        try:
            raw = Path(filepath).read_text(encoding="utf-8")
        except OSError:
            return

        meta, body = _parse_frontmatter(raw)
        doc_id = Path(filepath).stem

        # Combine searchable text: title + description + tags + body
        searchable_parts = [
            meta.get("title", ""),
            meta.get("description", ""),
            " ".join(meta.get("tags", [])),
            body,
        ]
        tokens = self._tokenize(" ".join(searchable_parts))

        self._docs[doc_id] = {
            "path": str(filepath),
            "meta": meta,
            "content": body,
            "tokens": tokens,
        }

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text: lowercase, split on non-alpha, remove stop words, basic stemming.

        Args:
            text: Raw text to tokenize.

        Returns:
            List of cleaned tokens.
        """
        text = text.lower()
        words = re.findall(r"[a-zçğıöşü0-9]+", text)
        result: list[str] = []
        for w in words:
            if w in STOP_WORDS or len(w) < 2:
                continue
            # Basic English suffix stemming
            for suffix in ("ing", "tion", "ment", "ness", "able", "ible", "ous", "ive", "ful", "less", "ly", "ed", "er", "es", "s"):
                if len(w) > len(suffix) + 2 and w.endswith(suffix):
                    w = w[: -len(suffix)]
                    break
            result.append(w)
        return result

    def _tf(self, term: str, doc_tokens: list[str]) -> float:
        """Compute term frequency (normalized).

        Args:
            term: The term to measure.
            doc_tokens: All tokens in the document.

        Returns:
            Frequency of *term* divided by total token count.
        """
        if not doc_tokens:
            return 0.0
        return doc_tokens.count(term) / len(doc_tokens)

    def _idf(self, term: str) -> float:
        """Compute inverse document frequency.

        Args:
            term: The term to measure.

        Returns:
            ``log(N / df)`` where *df* is the number of documents containing *term*.
        """
        n = len(self._docs)
        if n == 0:
            return 0.0
        df = sum(1 for doc in self._docs.values() if term in doc["tokens"])
        if df == 0:
            return 0.0
        return math.log(n / df)
