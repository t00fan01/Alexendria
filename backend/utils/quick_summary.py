"""
Fast extractive summary generation - no LLM needed, returns instantly.
Used when Gemini quota is exhausted or for quick previews.
"""

import re
from typing import Dict, List

def extract_key_sentences(transcript: str, max_sentences: int = 5) -> List[str]:
    """Extract important sentences from transcript using heuristics."""
    if not transcript or len(transcript) < 50:
        return []
    
    # Split by sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', transcript)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    if len(sentences) <= max_sentences:
        return sentences[:max_sentences]
    
    # Simple heuristic: prioritize sentences with key phrases
    key_phrases = ['important', 'key', 'learn', 'explain', 'show', 'example', 
                   'demonstrate', 'understand', 'main', 'focus', 'point', 'note']
    
    scored = []
    for sent in sentences:
        score = 0
        lower = sent.lower()
        # Keyword scoring
        for phrase in key_phrases:
            if phrase in lower:
                score += 2
        # Length preference (not too short, not too long)
        if 15 < len(sent) < 200:
            score += 1
        # Position boost (earlier sentences often set context)
        pos_idx = sentences.index(sent)
        if pos_idx < len(sentences) * 0.2:  # First 20%
            score += 1
        scored.append((sent, score))
    
    # Sort by score and return top N
    scored.sort(key=lambda x: x[1], reverse=True)
    result = [s[0] for s in scored[:max_sentences]]
    return result

def generate_quick_summary(transcript: str, word_count_threshold: int = 100) -> Dict[str, str]:
    """
    Generate extractive summary instantly (no LLM).
    
    Args:
        transcript: Full video transcript text
        word_count_threshold: Minimum words before generating summary
        
    Returns:
        Dict with 'summary' (formatted text), 'method' (always 'extractive'), 
        'word_count' (transcript length)
    """
    if not transcript:
        return {
            "summary": "No transcript available. Please check the video or try again.",
            "method": "extractive",
            "word_count": 0,
            "status": "error"
        }
    
    words = transcript.split()
    word_count = len(words)
    
    if word_count < word_count_threshold:
        # Too short - just return the whole thing
        return {
            "summary": f"**Short Video Summary** ({word_count} words)\n\n{transcript}",
            "method": "extractive",
            "word_count": word_count,
            "status": "success"
        }
    
    # Extract key points
    key_sentences = extract_key_sentences(transcript, max_sentences=5)
    
    if not key_sentences:
        return {
            "summary": "Unable to generate summary from this transcript.",
            "method": "extractive",
            "word_count": word_count,
            "status": "error"
        }
    
    # Format as bullet points
    bullet_summary = "**Key Points from Video:**\n\n"
    for i, sentence in enumerate(key_sentences, 1):
        bullet_summary += f"• {sentence}\n\n"
    
    bullet_summary += f"\n---\n*Quick summary (extractive, {word_count} total words)*"
    
    return {
        "summary": bullet_summary,
        "method": "extractive",
        "word_count": word_count,
        "status": "success"
    }

def is_gemini_error(error_msg: str) -> bool:
    """Check if error is Gemini-related (quota, API key, etc)."""
    error_lower = str(error_msg).lower()
    return any(keyword in error_lower for keyword in [
        'quota', '429', 'too many requests', 'resource exhausted',
        'api key', 'unauthorized', 'forbidden', 'gemini',
        'google', 'permission denied'
    ])
