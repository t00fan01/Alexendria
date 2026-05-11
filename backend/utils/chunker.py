def chunk_transcript(transcript, segments, chunk_duration=30, overlap=0):
    chunks = []
    current_start = 0.0
    last_end = segments[-1]['end'] if segments else len(transcript.split()) * 0.5
    while current_start < last_end:
        current_end = current_start + chunk_duration
        chunk_text_parts = []
        for seg in segments:
            # Only include segments that primarily fall within this window
            # to avoid duplication across chunks.
            seg_center = (seg['start'] + seg['end']) / 2
            if current_start <= seg_center < current_end:
                chunk_text_parts.append(seg['text'])
        
        if chunk_text_parts:
            chunk_text = " ".join(chunk_text_parts).strip()
        else:
            # Fallback for when no segments are found in the window
            words = transcript.split()
            start_word = int(current_start / 0.5)
            end_word = int(min(len(words), int(current_end / 0.5)))
            chunk_text = " ".join(words[start_word:end_word])
            
        if chunk_text:
            chunks.append({
                "text": chunk_text.strip(),
                "start": current_start,
                "end": min(current_end, last_end)
            })
        current_start += chunk_duration
    return chunks