import os
from .utils.similarity import keyword_similarity
from .utils.transcript_store import get_chunks
from .utils.gemini_client import generate_text, gemini_available
from .utils.summary_helper import extractive_summary


def _embeddings_enabled() -> bool:
    return os.getenv("ENABLE_EMBEDDINGS", "0").strip().lower() in {"1", "true", "yes", "on"}


def _chroma_enabled() -> bool:
    return os.getenv("ENABLE_CHROMA", "0").strip().lower() in {"1", "true", "yes", "on"}


def _format_context(chunks):
    lines = []
    for i, chunk in enumerate(chunks, start=1):
        start = chunk.get('start_time', 0)
        end = chunk.get('end_time', 0)
        lines.append(f"[{i}] ({start:.2f}-{end:.2f}s) {chunk.get('text', '').strip()}")
    return "\n".join(lines)


def _build_answer_prompt(question, context, history):
    history_text = ""
    if history:
        turns = []
        for item in history[-4:]:
            turns.append(f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}")
        history_text = "\n\nPrevious conversation:\n" + "\n\n".join(turns)
    return (
        "You are the AI Learning Companion. Answer only from the provided transcript context. "
        "If the context does not contain the answer, say you could not find it in the video. "
        "Keep the answer concise, human-like, and grounded in the transcript. Do not invent facts.\n\n"
        f"Transcript context:\n{context}\n\n"
        f"Question: {question}\n"
        f"{history_text}\n\n"
        "Answer with a short paragraph."
    )


def _build_quality_guidance(quality_score: str, quality_warnings: list[str]) -> str:
    if quality_score == "low":
        detail = "; ".join(str(w) for w in quality_warnings[:3])
        return (
            "Transcript quality is low. Be careful, brief, and explicitly note uncertainty. "
            f"If useful, mention these warnings: {detail}."
        )
    if quality_score == "medium":
        return "Transcript quality is moderate. Be concise and include a small uncertainty note if the answer is not fully supported."
    return "Transcript quality is high. Answer normally, but stay grounded in the transcript."


def _coerce_warnings(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [part.strip() for part in value.split(";") if part.strip()]
    return []


def ask_question(video_id, question, history=[]):
    try:
        if _chroma_enabled():
            import chromadb
            client = chromadb.PersistentClient(path="./chroma_db")
            collection = client.get_collection(name="transcripts")
            results = collection.get(where={"video_id": video_id})
            if not results['ids']:
                raise Exception("No data found")
            texts = results['metadatas']
            embeddings = results.get('embeddings')
        else:
            raise Exception("Chroma persistence disabled")
    except Exception as e:
        print(f"ChromaDB failed: {e}, using fallback")
        texts = get_chunks(video_id)
        embeddings = None

    if not texts:
        return (
            "I could not find transcript data for that video yet. Please ingest a video first.",
            [0, 0],
        )

    best_idx = 0
    top_indices = [0]
    if embeddings and _embeddings_enabled():
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            model_emb = SentenceTransformer('all-MiniLM-L6-v2')
            q_emb = model_emb.encode([question])[0]
            similarities = cosine_similarity([q_emb], embeddings)[0]
            best_idx = int(np.argmax(similarities))
            top_indices = list(np.argsort(similarities)[::-1][:3])
        except Exception as e:
            print(f"Embedding QA failed: {e}, falling back to text matching")
            embeddings = None

    if embeddings is None and _embeddings_enabled():
        try:
            from sentence_transformers import SentenceTransformer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            model_emb = SentenceTransformer('all-MiniLM-L6-v2')
            text_embs = model_emb.encode([t['text'] for t in texts])
            q_emb = model_emb.encode([question])[0]
            similarities = cosine_similarity([q_emb], text_embs)[0]
            best_idx = int(np.argmax(similarities))
            top_indices = list(np.argsort(similarities)[::-1][:3])
        except Exception as e:
            print(f"Text embedding failed: {e}, using keyword matching")
            scored = sorted(
                enumerate(texts),
                key=lambda item: keyword_similarity(question, item[1].get('text', '')),
                reverse=True,
            )
            if scored:
                best_idx = scored[0][0]
                top_indices = [index for index, _chunk in scored[:3]]
    elif embeddings is None or not _embeddings_enabled():
        scored = sorted(
            enumerate(texts),
            key=lambda item: keyword_similarity(question, item[1].get('text', '')),
            reverse=True,
        )
        if scored:
            best_idx = scored[0][0]
            top_indices = [index for index, _chunk in scored[:3]]

    selected_chunks = [texts[i] for i in top_indices if i < len(texts)] or [texts[best_idx]]
    best_chunk = selected_chunks[0]
    timestamps = [best_chunk.get('start_time', 0), best_chunk.get('end_time', 0)]

    source = str(best_chunk.get('source', '')).lower()
    if source in {"youtube_metadata", "url_only"}:
        return (
            "I could not answer from the actual video speech because no real transcript was available. "
            "I only have YouTube metadata for this link. Try a video with captions, upload the video/audio file, "
            "or use the AssemblyAI transcription path so I can answer from spoken content.",
            timestamps,
        )

    quality_score = str(best_chunk.get('quality_score', 'unknown')).lower()
    quality_warnings = _coerce_warnings(best_chunk.get('quality_warnings'))
    quality_note = ""
    if quality_score == "low":
        quality_note = "Note: this answer is based on a low-confidence transcript, so it may be incomplete or approximate.\n\n"
    elif quality_score == "medium":
        quality_note = "Note: this answer is based on a moderate-confidence transcript.\n\n"

    context = _format_context(selected_chunks)
    answer = None
    if gemini_available():
        prompt = _build_answer_prompt(question, context, history)
        quality_guidance = _build_quality_guidance(quality_score, quality_warnings)
        prompt = f"{quality_guidance}\n\n{prompt}"
        try:
            answer = generate_text(prompt, temperature=0.2, max_output_tokens=256)
        except Exception as e:
            print(f"Gemini QA failed: {e}")

    if not answer:
        # Create a concise local answer by extractive-summarizing the selected chunks
        try:
            combined = ' '.join([c.get('text', '') for c in selected_chunks])
            answer = extractive_summary(combined, num_sentences=2)
        except Exception:
            answer = best_chunk.get('text', '').strip()
    if not answer:
        answer = "I found a relevant section, but the transcript chunk is empty."

    if quality_note and answer:
        answer = f"{quality_note}{answer}"
        if quality_warnings:
            answer += "\n\nTranscript warnings: " + "; ".join(str(w) for w in quality_warnings[:3])

    return answer, timestamps
