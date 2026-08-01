"""Document retriever — loads, parses, and keyword-searches Data/docs unstructured corpus."""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DocEntry:
    filename: str
    ref: str
    title: str
    content: str
    score: float = 0.0


DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "Data" / "docs"

# Terms that make a doc more relevant for different query types
RELEVANCE_BOOST: dict[str, float] = {
    "promo": 3.0,
    "promotion": 3.0,
    "price-off": 3.0,
    "stockout": 3.0,
    "shortfall": 3.0,
    "delay": 2.0,
    "supplier": 2.0,
    "supply": 2.0,
    "losing shelf": 2.0,
    "rival": 2.0,
    "cheaper": 2.0,
    "mrp": 2.0,
    "increase": 1.5,
    "decline": 1.5,
    "escalate": 1.5,
    "exception": 0.5,
    "routine": 0.3,
    "reminder": 0.1,
    "expense": 0.1,
}

# Terms that signal a doc is a distractor (low quality signal)
DISTRACTOR_TERMS = {
    "no exceptions",
    "no impact on current",
    "no major exceptions",
    "minor variance",
    "in line with plan",
    "submit",
    "expense claims",
}


class DocRetriever:
    def __init__(self):
        self.docs: list[DocEntry] = self._load_all()

    def _load_all(self) -> list[DocEntry]:
        docs = []
        if not DOCS_DIR.exists():
            return docs
        for fpath in sorted(DOCS_DIR.glob("*.txt")):
            text = fpath.read_text(encoding="utf-8")
            doc = self._parse(fpath.name, text)
            docs.append(doc)
        return docs

    def _parse(self, filename: str, text: str) -> DocEntry:
        ref = filename.replace(".txt", "")
        title = ""
        content = text
        for line in text.strip().split("\n"):
            line_stripped = line.strip()
            if line_stripped.startswith("# "):
                title = line_stripped[2:].strip()
            m = re.match(r"^Ref:\s*(.+)", line_stripped)
            if m:
                ref = m.group(1).strip()
        # Remove the header lines from content for better matching
        body_lines = []
        for line in text.strip().split("\n"):
            if line.strip().startswith("# ") or line.strip().startswith("Ref:") or line.strip().startswith("From:") or line.strip().startswith("Contact:"):
                continue
            body_lines.append(line)
        content = "\n".join(body_lines).strip()
        return DocEntry(filename=filename, ref=ref, title=title, content=content)

    def get_by_ref(self, ref: str) -> DocEntry | None:
        for doc in self.docs:
            if doc.ref == ref:
                return doc
        return None

    def search(self, query: str, top_k: int = 10) -> list[DocEntry]:
        if not query.strip():
            return []
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        scored: list[DocEntry] = []
        for doc in self.docs:
            score = self._score_doc(doc, query_lower, query_terms)
            if score > 0:
                doc.score = score
                scored.append(doc)

        scored.sort(key=lambda d: d.score, reverse=True)
        return scored[:top_k]

    def _score_doc(self, doc: DocEntry, query_lower: str, query_terms: set[str]) -> float:
        content_lower = doc.content.lower()
        ref_lower = doc.ref.lower()
        title_lower = doc.title.lower()
        haystack = f"{ref_lower} {title_lower} {content_lower}"

        # Direct keyword matching
        keyword_matches = sum(1 for term in query_terms if term in haystack)
        phrase_matches = 0
        # Check for multi-word query phrases
        query_words = query_lower.split()
        for i in range(len(query_words) - 1):
            phrase = " ".join(query_words[i:i+2])
            if phrase in haystack:
                phrase_matches += 1
        for i in range(len(query_words) - 2):
            phrase = " ".join(query_words[i:i+3])
            if phrase in haystack:
                phrase_matches += 2

        base_score = keyword_matches + phrase_matches

        if base_score == 0:
            return 0.0

        # Apply relevance boosts
        for term, boost in RELEVANCE_BOOST.items():
            if term in haystack:
                # Only boost if the term is related to the query
                if term in query_lower or any(qt in term for qt in query_terms):
                    base_score *= boost

        # Penalize distractors
        for dterm in DISTRACTOR_TERMS:
            if dterm in content_lower:
                base_score *= 0.3

        return base_score