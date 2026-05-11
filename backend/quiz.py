"""
quiz.py – MCQ quiz generation from video transcript chunks or raw text.
Uses Gemini when available, falls back to extractive heuristics.
"""
from __future__ import annotations

import json
import os
import re
import random
from .utils.transcript_store import get_chunks
from .utils.gemini_client import generate_text, gemini_available


# ─── helpers ──────────────────────────────────────────────────────────────────

def _build_chunk_context(chunks: list[dict], max_chars: int = 6000) -> str:
    parts = []
    total = 0
    for c in chunks:
        text = (c.get("text") or "").strip()
        if not text:
            continue
        start = c.get("start_time") or c.get("start") or 0
        snippet = f"[{int(start)}s] {text}"
        if total + len(snippet) > max_chars:
            break
        parts.append(snippet)
        total += len(snippet)
    return "\n".join(parts)


_MCQ_PROMPT = """\
You are an expert quiz generator. Read the following lecture transcript and create {n} high-quality multiple-choice questions to test student comprehension.

Return ONLY a valid JSON array (no markdown, no prose) with exactly {n} objects, each in this exact shape:
{{
  "question": "<question text>",
  "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
  "correct": "A",
  "explanation": "<why correct, 1-2 sentences, cite the lecture>",
  "timestamp": <integer seconds or null>,
  "topic": "<short topic label>"
}}

Rules:
- Questions must be answerable ONLY from the transcript — no outside knowledge.
- Distractors must be plausible but clearly wrong.
- Vary difficulty: mix recall, comprehension, and application questions.
- timestamp = the approximate second in the lecture where the answer is found (null if unknown).

TRANSCRIPT:
{context}
"""


def _parse_quiz_json(raw: str) -> list[dict]:
    """Extract a JSON array from raw LLM output, robust to markdown fences."""
    raw = raw.strip()
    # Strip ```json ... ``` fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    # Try direct parse
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # Try to find JSON array in the string
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return []


def _validate_question(q: dict) -> bool:
    return (
        isinstance(q, dict)
        and isinstance(q.get("question"), str) and len(q["question"]) > 8
        and isinstance(q.get("options"), dict)
        and all(k in q["options"] for k in ("A", "B", "C", "D"))
        and q.get("correct") in ("A", "B", "C", "D")
    )


def _fallback_quiz(chunks: list[dict], num_questions: int = 5) -> list[dict]:
    """Very basic heuristic quiz when Gemini is unavailable."""
    questions = []
    usable = [c for c in chunks if len((c.get("text") or "").split()) > 10]
    random.shuffle(usable)
    for chunk in usable[:num_questions]:
        text = (chunk.get("text") or "").strip()
        sentences = [s.strip() for s in re.split(r"[.!?]", text) if len(s.strip()) > 20]
        if not sentences:
            continue
        sentence = sentences[0]
        words = sentence.split()
        if len(words) < 5:
            continue
        # Blank out a key word for fill-in style MCQ
        key_idx = len(words) // 2
        answer_word = words[key_idx]
        blank = " ".join(words[:key_idx] + ["_____"] + words[key_idx + 1:])
        # Generate 3 wrong options from other chunks
        distractors = []
        for other in usable:
            if other is chunk:
                continue
            other_words = (other.get("text") or "").split()
            if other_words:
                w = random.choice(other_words)
                if w not in distractors and w != answer_word and len(w) > 3:
                    distractors.append(w)
            if len(distractors) >= 3:
                break
        while len(distractors) < 3:
            distractors.append(f"Option {len(distractors)+1}")

        options_list = [answer_word] + distractors[:3]
        random.shuffle(options_list)
        correct_letter = "ABCD"[options_list.index(answer_word)]
        start = chunk.get("start_time") or chunk.get("start") or 0

        questions.append({
            "question": f'Complete the sentence from the lecture: "{blank}"',
            "options": {"A": options_list[0], "B": options_list[1], "C": options_list[2], "D": options_list[3]},
            "correct": correct_letter,
            "explanation": f'The original text says: "{sentence}"',
            "timestamp": int(start),
            "topic": "Lecture Content",
        })

    return questions


# ─── public API ───────────────────────────────────────────────────────────────

def generate_quiz_from_chunks(video_id: str, num_questions: int = 10) -> list[dict]:
    """Generate MCQ quiz from an already-ingested video's transcript."""
    raw_chunks = get_chunks(video_id)
    if not raw_chunks:
        return []

    chunks = sorted(raw_chunks, key=lambda c: c.get("start_time") or c.get("start") or 0)

    if gemini_available():
        context = _build_chunk_context(chunks)
        prompt = _MCQ_PROMPT.format(n=num_questions, context=context)
        try:
            raw = generate_text(prompt, temperature=0.4, max_output_tokens=4096)
            questions = _parse_quiz_json(raw or "")
            valid = [q for q in questions if _validate_question(q)]
            if len(valid) >= min(3, num_questions):
                return valid[:num_questions]
        except Exception as e:
            print(f"[quiz] Gemini MCQ generation failed: {e}")

    # Fallback
    return _fallback_quiz(chunks, num_questions)


def generate_quiz_from_text(text: str, num_questions: int = 10) -> list[dict]:
    """Generate MCQ quiz from arbitrary raw text (e.g., pasted notes or PDF extract)."""
    if not text or len(text.strip()) < 100:
        return []

    if gemini_available():
        # Chunk the text naively for the prompt
        excerpt = text[:6000]
        prompt = _MCQ_PROMPT.format(n=num_questions, context=excerpt)
        try:
            raw = generate_text(prompt, temperature=0.4, max_output_tokens=4096)
            questions = _parse_quiz_json(raw or "")
            valid = [q for q in questions if _validate_question(q)]
            if len(valid) >= min(3, num_questions):
                return valid[:num_questions]
        except Exception as e:
            print(f"[quiz] Gemini text quiz failed: {e}")

    # Fallback — synthesise fake chunks from text paragraphs
    sentences = [s.strip() for s in re.split(r"[.!?\n]", text) if len(s.strip()) > 20]
    fake_chunks = [{"text": s, "start_time": i * 30} for i, s in enumerate(sentences)]
    return _fallback_quiz(fake_chunks, num_questions)
