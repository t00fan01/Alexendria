from pathlib import Path

def load_transcript():
    base = Path(__file__).resolve().parent.parent
    transcript_path = base / 'data' / 'transcript.txt'
    try:
        # Return empty string instead of demo content so ingestion fails loudly
        text = transcript_path.read_text(encoding='utf-8')
        return text.strip()
    except Exception:
        return ""
