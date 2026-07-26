import os
from .utils.summary_helper import summarize_by_topics, get_last_n_minutes_summary, extractive_summary
from .utils.transcript_store import get_chunks
from .utils.gemini_client import generate_text, gemini_available

_summary_cache = {}


def _chroma_enabled() -> bool:
    return os.getenv("ENABLE_CHROMA", "0").strip().lower() in {"1", "true", "yes", "on"}


def _normalize_chunk(metadata: dict) -> dict:
    return {
        'text': metadata.get('text', ''),
        'start': metadata.get('start', metadata.get('start_time', 0)) or 0,
        'end': metadata.get('end', metadata.get('end_time', 0)) or 0,
        'source': metadata.get('source', 'unknown'),
        'method': metadata.get('method', 'unknown'),
        'quality_score': metadata.get('quality_score', 'unknown'),
        'quality_warnings': metadata.get('quality_warnings', ''),
        'word_count': metadata.get('word_count', 0) or 0,
        'chunk_count': metadata.get('chunk_count', 0) or 0,
        'unique_ratio': metadata.get('unique_ratio', 0.0) or 0.0,
    }


def _load_chunks(video_id):
    fallback_chunks = [_normalize_chunk(chunk) for chunk in get_chunks(video_id)]
    if fallback_chunks:
        return sorted(fallback_chunks, key=lambda chunk: chunk.get('start', 0))

    if not _chroma_enabled():
        return []

    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="transcripts")
        results = collection.get(where={"video_id": video_id})
        return sorted([_normalize_chunk(m) for m in results.get('metadatas', [])], key=lambda chunk: chunk.get('start', 0))
    except Exception as e:
        print(f"Transcript load failed: {e}")
        return []


def _cache_key(video_id, chunks, kind):
    last_end = int(max([chunk.get('end', 0) or 0 for chunk in chunks], default=0))
    text_size = sum(len(chunk.get('text', '')) for chunk in chunks)
    return (kind, video_id, len(chunks), last_end, text_size)


def _clip(text, limit=900):
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(" ", 1)[0].strip()
    return clipped.rstrip(".,;:") + "."


def _fallback_topics(chunks, max_topics=5):
    if not chunks:
        return []

    topic_count = min(max_topics, len(chunks))
    step = max(1, len(chunks) // topic_count)
    topics = []
    for index in range(0, len(chunks), step):
        group = chunks[index:index + step]
        if not group:
            continue
        text = " ".join(chunk.get('text', '') for chunk in group if chunk.get('text'))
        if not text.strip():
            continue
        title = _clip(extractive_summary(text, num_sentences=1), 78)
        summary = _clip(extractive_summary(text, num_sentences=2), 260)
        topics.append({
            'topic': title or f"Key moment {len(topics) + 1}",
            'summary': summary or _clip(text, 260),
            'timestamp': group[0].get('start', 0),
        })
        if len(topics) >= max_topics:
            break
    return topics


def _build_overall_summary_prompt(chunks):
    context = []
    for chunk in chunks[:16]:
        context.append(f"({chunk.get('start', 0):.2f}-{chunk.get('end', 0):.2f}s) {chunk.get('text', '')}")
    return (
        "Write a concise overall summary of the video transcript below. "
        "Stay faithful to the transcript only. Do not add outside knowledge.\n\n"
        + "\n".join(context)
    )

def get_summary(video_id):
    # Backwards-compatible wrapper that returns only the summary text.
    summary, _method = get_summary_with_method(video_id)
    return summary


def get_summary_with_method(video_id):
    """Return a tuple (summary_text, method) where method is 'gemini' or 'extractive_fallback'.
    This allows callers to know which summarization approach produced the result."""
    chunks = _load_chunks(video_id)
    if not chunks:
        return ("Summary is not available yet. Please ingest a video first.", "none")

    key = _cache_key(video_id, chunks, "overall")
    if key in _summary_cache:
        return (_summary_cache[key], "cached")

    full_text = " ".join([c.get('text', '') for c in chunks if c.get('text')])
    summary = extractive_summary(full_text, num_sentences=4)
    method = "extractive_fallback"

    if chunks and gemini_available():
        try:
            gemini_summary = generate_text(_build_overall_summary_prompt(chunks), temperature=0.2, max_output_tokens=220)
            if gemini_summary:
                summary = gemini_summary
                method = "gemini"
        except Exception as e:
            print(f"Gemini overall summary failed: {e}")

    summary = _clip(summary, 1100)
    if not summary:
        summary = _clip(" ".join([c.get('text', '') for c in chunks[:8]]), 900)

    _summary_cache[key] = summary
    return (summary, method)

def get_topic_summaries(video_id):
    chunks = _load_chunks(video_id)
    if not chunks:
        return []

    key = _cache_key(video_id, chunks, "topics")
    if key in _summary_cache:
        return _summary_cache[key]

    full_text = " ".join([c.get('text', '') for c in chunks])
    topics = summarize_by_topics(full_text, chunks)
    if len(topics) < min(3, len(chunks)):
        topics = _fallback_topics(chunks)

    _summary_cache[key] = topics
    return topics

def get_last_minutes_summary(video_id, minutes: int = 5):
    chunks = _load_chunks(video_id)
    if not chunks:
        return {"summary": "No content available", "timestamp": 0}

    summary_text, timestamp = get_last_n_minutes_summary(chunks, minutes)
    return {"summary": _clip(summary_text, 600), "timestamp": timestamp}
