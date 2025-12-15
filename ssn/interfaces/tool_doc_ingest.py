# ssn/interfaces/tool_doc_ingest.py

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse, ErrorInfo


MAX_DOC_CHARS_DEFAULT = 60_000
MAX_LINES_DEFAULT = 2_000
MAX_CITATIONS_DEFAULT = 10
MAX_EXCERPT_CHARS = 220
MAX_SUMMARY_BULLETS_DEFAULT = 7


class _HTMLTextExtractor(HTMLParser):
    """
    Lightweight HTML -> text/link extractor using stdlib only.
    """

    def __init__(self) -> None:
        super().__init__()
        self._chunks: List[str] = []
        self._links: List[Dict[str, str]] = []
        self._current_href: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]) -> None:
        if tag.lower() == "a":
            href = None
            for k, v in attrs:
                if k.lower() == "href":
                    href = v
                    break
            self._current_href = href
        # add line breaks for structure
        if tag.lower() in ("p", "br", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a":
            self._current_href = None
        if tag.lower() in ("p", "div", "li"):
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        txt = (data or "").strip()
        if not txt:
            return
        self._chunks.append(txt)
        if self._current_href:
            # record link anchor text and href (bounded later)
            self._links.append({"text": txt, "href": self._current_href})

    def text(self) -> str:
        joined = " ".join(self._chunks)
        # normalize whitespace + newlines
        joined = re.sub(r"[ \t]+", " ", joined)
        joined = re.sub(r"\n\s*\n\s*\n+", "\n\n", joined)
        return joined.strip()

    def links(self) -> List[Dict[str, str]]:
        return self._links


def _sha256_short(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _clip_lines(lines: List[str], max_lines: int) -> List[str]:
    return lines[:max_lines] if len(lines) > max_lines else lines


def _clip_text(s: str, max_chars: int) -> str:
    return s[:max_chars] if len(s) > max_chars else s


def _split_lines(text: str, max_lines: int) -> List[str]:
    raw = (text or "").splitlines()
    # trim + drop very empty lines but keep some structure
    cleaned = []
    for ln in raw:
        ln2 = ln.strip()
        if not ln2:
            continue
        cleaned.append(ln2)
    return _clip_lines(cleaned, max_lines)


def _sentences(text: str) -> List[str]:
    # Very conservative sentence split (no external libs)
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    parts = re.split(r"(?<=[\.\?\!])\s+", text)
    out = []
    for p in parts:
        p = p.strip()
        if len(p) >= 20:
            out.append(p)
    return out


def _score_sentence(s: str) -> float:
    # Heuristic scoring: length + keyword hints
    base = min(len(s) / 120.0, 1.0)
    bonus = 0.0
    lower = s.lower()
    for kw in ("must", "should", "require", "important", "goal", "risk", "ensure", "avoid"):
        if kw in lower:
            bonus += 0.12
    return base + bonus


def _top_k_sentences(text: str, k: int) -> List[str]:
    sents = _sentences(text)
    scored = [(i, _score_sentence(s), s) for i, s in enumerate(sents)]
    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:k]
    top.sort(key=lambda x: x[0])  # preserve original order for readability
    return [t[2] for t in top]


def _make_citations(lines: List[str], max_citations: int) -> List[Dict[str, str]]:
    citations: List[Dict[str, str]] = []
    for idx, ln in enumerate(lines[:max_citations]):
        citations.append(
            {
                "ref": f"L{idx+1}",
                "excerpt": _clip_text(ln, MAX_EXCERPT_CHARS),
            }
        )
    return citations


def _try_write_trace(memory_hub: Any, payload: Dict[str, Any]) -> bool:
    """
    Best-effort trace write without assuming a specific MemoryHub API.
    """
    if memory_hub is None:
        return False

    # Common patterns
    candidates = []

    # memory_hub.trace.add_trace(...)
    trace = getattr(memory_hub, "trace", None)
    if trace is not None:
        candidates.append(getattr(trace, "add_trace", None))
        candidates.append(getattr(trace, "append", None))

    # memory_hub.trace_memory.add_trace(...)
    trace_memory = getattr(memory_hub, "trace_memory", None)
    if trace_memory is not None:
        candidates.append(getattr(trace_memory, "add_trace", None))
        candidates.append(getattr(trace_memory, "append", None))

    # memory_hub.add_trace(...)
    candidates.append(getattr(memory_hub, "add_trace", None))
    candidates.append(getattr(memory_hub, "write_trace", None))

    for fn in candidates:
        if callable(fn):
            try:
                # attempt common signatures
                try:
                    fn(payload=payload)
                except TypeError:
                    try:
                        fn(payload)
                    except TypeError:
                        fn(type=payload.get("type", "trace"), payload=payload)
                return True
            except Exception:
                continue

    return False


def doc_ingest_readonly(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
    """
    Tool: doc.ingest_readonly

    Input:
      - meta.document (preferred) OR context.document
      - meta.format: "text" | "html" (default: "text")
      - meta.title: optional
      - meta.max_chars / max_lines / max_citations / max_summary_bullets: optional bounds
      - meta.include_links: bool optional

    Output:
      - normalized text stats
      - bullet summary (heuristic)
      - line-based citations (L1..)
      - links (optional)
      - OWNER-only: writes a bounded trace event (no full raw document stored)
    """
    meta = req.meta if isinstance(req.meta, dict) else {}
    ctx = req.context if isinstance(req.context, dict) else {}

    doc = meta.get("document", None)
    if doc is None:
        doc = ctx.get("document", None)

    if not isinstance(doc, str) or not doc.strip():
        return InterfaceResponse(
            ok=False,
            action=req.action,
            role=req.role,
            error=ErrorInfo(code="DOC_MISSING", message="Provide document text via meta.document or context.document."),
        )

    fmt = meta.get("format", "text")
    if not isinstance(fmt, str):
        fmt = "text"
    fmt = fmt.lower().strip()

    title = meta.get("title", None)
    if not isinstance(title, str):
        title = None

    max_chars = int(meta.get("max_chars", MAX_DOC_CHARS_DEFAULT))
    max_lines = int(meta.get("max_lines", MAX_LINES_DEFAULT))
    max_citations = int(meta.get("max_citations", MAX_CITATIONS_DEFAULT))
    max_summary_bullets = int(meta.get("max_summary_bullets", MAX_SUMMARY_BULLETS_DEFAULT))
    include_links = bool(meta.get("include_links", True))

    raw = _clip_text(doc.strip(), max_chars)

    links: List[Dict[str, str]] = []
    text = raw

    if fmt == "html":
        parser = _HTMLTextExtractor()
        try:
            parser.feed(raw)
            text = parser.text()
            if include_links:
                # bound links
                raw_links = parser.links()[:25]
                links = [{"text": _clip_text(l.get("text", ""), 80), "href": _clip_text(l.get("href", ""), 300)} for l in raw_links]
        except Exception:
            # fallback: strip tags rudimentarily
            text = re.sub(r"<[^>]+>", " ", raw)

    # Build line model for citations
    lines = _split_lines(text, max_lines=max_lines)
    citations = _make_citations(lines, max_citations=max_citations)

    # Summary bullets from top sentences
    bullets = _top_k_sentences(text, k=max_summary_bullets)
    bullets = [_clip_text(b, 240) for b in bullets]

    # Stats
    word_count = len(re.findall(r"\b\w+\b", text))
    content_hash = _sha256_short(text)

    data: Dict[str, Any] = {
        "title": title,
        "format": fmt,
        "content_hash": content_hash,
        "stats": {
            "chars_in": len(doc),
            "chars_used": len(raw),
            "chars_text": len(text),
            "lines_used": len(lines),
            "word_count": word_count,
        },
        "summary_bullets": bullets,
        "citations": citations,
    }
    if include_links and links:
        data["links"] = links

    # OWNER: write a bounded trace (never store full doc)
    wrote_trace = False
    if req.role == "OWNER":
        memory_hub = deps.get("memory_hub")
        payload = {
            "type": "doc_ingest",
            "title": title,
            "format": fmt,
            "content_hash": content_hash,
            "summary_bullets": bullets[: max_summary_bullets],
            "citations": citations[: max_citations],
            "link_count": len(links),
            "meta": {
                "source": meta.get("source", "local"),
                "timestamp": meta.get("timestamp", None),
            },
            "notes": [
                "Read-only ingest; no external fetch performed.",
                "Raw document not stored (bounded trace only).",
            ],
        }
        wrote_trace = _try_write_trace(memory_hub, payload)

    data["trace_written"] = bool(wrote_trace)

    return InterfaceResponse(ok=True, action=req.action, role=req.role, data=data)
