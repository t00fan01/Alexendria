import re
import html
from typing import List, Tuple
from .gemini_client import generate_text, gemini_available

# Small, self-contained extractive summarizer (no external deps)
_STOPWORDS = {
    'the','and','is','in','it','of','to','a','that','this','for','on','with','as','are','was','be','by','an','or','from','at','which','but'
}


def _clean_text_fragment(text: str) -> str:
    text = html.unescape(str(text or ""))
    text = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", " ", text)
    text = re.sub(r"</?c(?:\.[^>]*)?>", " ", text)
    text = re.sub(r"</?[^>]+>", " ", text)
    text = re.sub(r"\{\\an\d+\}", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" -")
    return text


def extractive_summary(text: str, num_sentences: int = 3) -> str:
    """Return an extractive summary of `text` by scoring sentences with word frequencies."""
    text = _clean_text_fragment(text)
    # Split into sentences / lines and remove duplicates while preserving order
    raw_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if s.strip()]
    sentences = []
    seen_sentences = set()
    for sentence in raw_sentences:
        key = re.sub(r'\s+', ' ', sentence).lower()
        if key in seen_sentences:
            continue
        seen_sentences.add(key)
        sentences.append(sentence)
    if not sentences:
        return text.strip()
    if len(text.split()) < 30:
        return ' '.join(sentences[:num_sentences]).strip()

    # Build word frequency
    freq = {}
    for word in re.findall(r"\w+", text.lower()):
        if word in _STOPWORDS or len(word) <= 2:
            continue
        freq[word] = freq.get(word, 0) + 1

    if not freq:
        return ' '.join(sentences[:num_sentences])

    # Score sentences
    scores = []
    for sent in sentences:
        words = re.findall(r"\w+", sent.lower())
        score = sum(freq.get(w, 0) for w in words)
        # penalize extremely long sentences slightly
        score = score / (1 + 0.01 * max(0, len(words) - 30))
        scores.append(score)

    # Select top sentences but preserve order
    ranked_idx = sorted(range(len(sentences)), key=lambda i: scores[i], reverse=True)[:num_sentences]
    ranked_idx.sort()
    selected = [sentences[i] for i in ranked_idx]
    # Remove adjacent duplicates in the final text as a last line of defense
    cleaned = []
    last_key = None
    for sentence in selected:
        key = re.sub(r'\s+', ' ', sentence).lower()
        if key != last_key:
            cleaned.append(sentence)
        last_key = key
    return ' '.join(cleaned)


def _chunk_context(chunks: List[dict], limit: int = 12) -> str:
    parts = []
    for chunk in chunks[:limit]:
        start = chunk.get('start', 0)
        end = chunk.get('end', 0)
        parts.append(f"({start:.2f}-{end:.2f}s) {_clean_text_fragment(chunk.get('text', '').strip())}")
    return "\n".join(parts)

def extract_topics(text: str, num_topics: int = 5) -> List[str]:
    """Extract key topics from text using simple heuristics."""
    text = _clean_text_fragment(text)
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    topics = []
    seen = set()
    for sentence in sentences[:20]:
        words = sentence.lower().split()
        key_words = [w for w in words if len(w) > 5 and w not in {'about', 'which', 'would', 'there', 'their', 'these'}]
        if key_words:
            topic = ' '.join(key_words[:3])
            if topic not in seen:
                topics.append(sentence[:100])
                seen.add(topic)
                if len(topics) >= num_topics:
                    break
    return topics

def summarize_by_topics(text: str, chunks: List[dict]) -> List[dict]:
    """Create topic-wise summaries from chunks."""
    if not chunks:
        return []
    text = _clean_text_fragment(text)
    topics = extract_topics(text, num_topics=5)
    result = []
    for i, topic in enumerate(topics):
        relevant_chunks = []
        for chunk in chunks:
            chunk_text = _clean_text_fragment(chunk.get('text', '')).lower()
            if any(word in chunk_text for word in topic.lower().split()[:2]):
                relevant_chunks.append(chunk)
        if relevant_chunks:
            relevant_text = " ".join([_clean_text_fragment(c.get('text', '')) for c in relevant_chunks[:4]])
            summary_text = extractive_summary(relevant_text, num_sentences=2) or relevant_text[:220]
            if gemini_available():
                prompt = (
                    "Summarize the following transcript snippets as a short topic summary. "
                    "Stay faithful to the text, avoid adding facts, and keep it concise.\n\n"
                    f"Topic: {topic}\n\nSnippets:\n{_chunk_context(relevant_chunks, limit=6)}"
                )
                try:
                    gemini_summary = generate_text(prompt, temperature=0.2, max_output_tokens=160)
                    if gemini_summary:
                        summary_text = gemini_summary
                except Exception:
                    pass
            result.append({
                'topic': topic[:80],
                'summary': summary_text,
                'timestamp': relevant_chunks[0].get('start', 0)
            })
    return result

def get_last_n_minutes_summary(chunks: List[dict], minutes: int = 5) -> Tuple[str, float]:
    """Get summary of last N minutes based on timestamps."""
    if not chunks:
        return ("No content available", 0)
    last_chunk = chunks[-1]
    end_time = last_chunk.get('end', 0)
    start_time = end_time - (minutes * 60)
    relevant_chunks = [
        c for c in chunks
        if c.get('end', 0) > start_time
    ]
    if relevant_chunks:
        summary_text = extractive_summary(" ".join([_clean_text_fragment(c.get('text', '')) for c in relevant_chunks]), num_sentences=3)
        if gemini_available():
            prompt = (
                f"Summarize the last {minutes} minutes of this transcript in 2-4 sentences. "
                "Be grounded only in the transcript, concise, and human-readable.\n\n"
                f"Transcript:\n{_chunk_context(relevant_chunks, limit=16)}"
            )
            try:
                gemini_summary = generate_text(prompt, temperature=0.2, max_output_tokens=220)
                if gemini_summary:
                    summary_text = gemini_summary
            except Exception:
                pass
        return (summary_text[:500], relevant_chunks[0].get('start', end_time))
    fallback_text = " ".join([_clean_text_fragment(c.get('text', '')) for c in chunks[-3:]])
    return (extractive_summary(fallback_text, num_sentences=2) or fallback_text, end_time - 300)

def format_timestamp(seconds: float) -> str:
    """Format seconds to HH:MM:SS."""
    seconds = max(0, seconds)
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
