import re
import importlib
import os
import subprocess
import sys
import time
import tempfile
import shutil
import hashlib
import html
from .utils.chunker import chunk_transcript
from .utils.transcript_loader import load_transcript
from .utils.transcript_store import store_chunks
from .utils.assemblyai_client import transcribe_uploaded_file, assemblyai_available, transcribe_file

_youtube_transcript_spec = importlib.util.find_spec("youtube_transcript_api")
if _youtube_transcript_spec is not None:
    YouTubeTranscriptApi = importlib.import_module("youtube_transcript_api").YouTubeTranscriptApi
else:
    YouTubeTranscriptApi = None


def _extract_youtube_id(url: str) -> str | None:
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?]|$)",
        r"youtu\.be\/([0-9A-Za-z_-]{11})(?:[&?]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _canonical_youtube_url(url: str) -> str:
    video_id = _extract_youtube_id(url)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return url


def _load_youtube_transcript(url: str):
    if not YouTubeTranscriptApi:
        print("YouTubeTranscriptApi not installed; skipping YouTube subtitle load.")
        return None
    video_id = _extract_youtube_id(url)
    if not video_id:
        return None
    try:
        # Newer versions expose `list_transcripts` as a classmethod
        if hasattr(YouTubeTranscriptApi, "list_transcripts"):
            print(f"Using YouTubeTranscriptApi.list_transcripts for {video_id}")
            transcripts = YouTubeTranscriptApi.list_transcripts(video_id)

            # Prefer English transcripts first.
            for finder in ("find_manually_created_transcript", "find_generated_transcript", "find_transcript"):
                if hasattr(transcripts, finder):
                    try:
                        t = getattr(transcripts, finder)(["en"])
                        return list(t.fetch())
                    except Exception:
                        pass

            # Use any directly available transcript before attempting translation.
            for t in transcripts:
                try:
                    entries = list(t.fetch())
                    if entries:
                        print(f"Using available transcript without translation: {len(entries)} entries from {t}")
                        return entries
                except Exception:
                    continue

            # Translation is a later fallback.
            for t in transcripts:
                try:
                    translated = t.translate("en")
                    entries = list(translated.fetch())
                    if entries:
                        print(f"Translated transcript fetched: {len(entries)} entries")
                        return entries
                except Exception:
                    continue

            try:
                entries = YouTubeTranscriptApi.get_transcript(video_id)
                entries = list(entries)
                print(f"get_transcript returned {len(entries)} entries")
                return entries
            except Exception as e:
                print(f"YouTube subtitle load failed: {e}")
                return None

        # Older versions use instance methods `list` and `fetch`
        print(f"Falling back to instance API for {video_id}")
        api = YouTubeTranscriptApi()
        try:
            transcripts = api.list(video_id)
        except Exception:
            transcripts = None

        # If we got a TranscriptList, try to pick English or any available transcript.
        if transcripts is not None:
            for finder in ("find_manually_created_transcript", "find_generated_transcript", "find_transcript"):
                if hasattr(transcripts, finder):
                    try:
                        t = getattr(transcripts, finder)(["en"])
                        return list(t.fetch())
                    except Exception:
                        pass

            for t in transcripts:
                try:
                    entries = list(t.fetch())
                    if entries:
                        print(f"Using available instance transcript without translation: {len(entries)} entries from {t}")
                        return entries
                except Exception:
                    continue

        # Last resort: instance fetch (returns a reasonable transcript if available)
        try:
            entries = api.fetch(video_id)
            entries = list(entries)
            print(f"api.fetch returned {len(entries)} entries")
            return entries
        except Exception as e:
            print(f"YouTube subtitle load failed: {e}")
            return None
    except Exception as e:
        print(f"YouTube transcript listing failed: {e}")
        return None


def _get_entry_value(entry, key, default=""):
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _fast_mode_enabled() -> bool:
    return os.getenv("ENABLE_EMBEDDINGS", "0").strip().lower() in {"1", "true", "yes", "on"}


def _chroma_enabled() -> bool:
    return os.getenv("ENABLE_CHROMA", "0").strip().lower() in {"1", "true", "yes", "on"}


def _youtube_asr_enabled() -> bool:
    return os.getenv("ENABLE_YOUTUBE_ASR", "1").strip().lower() in {"1", "true", "yes", "on"}


def _metadata_fallback_enabled() -> bool:
    return os.getenv("ENABLE_METADATA_FALLBACK", "0").strip().lower() in {"1", "true", "yes", "on"}


def _lightweight_embedding(text: str, dimensions: int = 384) -> list[float]:
    """Create a tiny local embedding so Chroma never invokes its slow default model."""
    vector = [0.0] * dimensions
    tokens = re.findall(r"\w+", (text or "").lower())[:220]
    if not tokens:
        vector[0] = 1.0
        return vector

    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
        bucket = int.from_bytes(digest, "little") % dimensions
        vector[bucket] += 1.0

    norm = sum(value * value for value in vector) ** 0.5 or 1.0
    return [round(value / norm, 6) for value in vector]


def _parse_timestamp(value: str) -> float:
    value = value.strip()
    match = re.match(r"(?:(\d+):)?(\d{2}):(\d{2})[\.,](\d{3})", value)
    if not match:
        return 0.0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    millis = int(match.group(4) or 0)
    return hours * 3600 + minutes * 60 + seconds + millis / 1000.0


def _clean_caption_payload(payload: str) -> str:
    payload = html.unescape(str(payload or ""))
    payload = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", " ", payload)
    payload = re.sub(r"</?c(?:\.[^>]*)?>", " ", payload)
    payload = re.sub(r"</?[^>]+>", " ", payload)
    payload = re.sub(r"\{\\an\d+\}", " ", payload)
    payload = re.sub(r"\s+", " ", payload).strip(" -")
    return payload


def _trim_caption_overlap(current_text: str, previous_text: str) -> str:
    current_words = current_text.split()
    previous_words = previous_text.split()
    if not current_words or not previous_words:
        return current_text

    max_overlap = min(len(current_words), len(previous_words), 32)
    for overlap in range(max_overlap, 0, -1):
        current_prefix = [word.lower() for word in current_words[:overlap]]
        previous_suffix = [word.lower() for word in previous_words[-overlap:]]
        if current_prefix == previous_suffix:
            trimmed = " ".join(current_words[overlap:]).strip()
            return trimmed
    return current_text


def _parse_caption_file(path: str):
    entries = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as file_handle:
            text = file_handle.read()
    except Exception:
        return entries

    blocks = re.split(r"\n\s*\n", text)
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        time_line = None
        payload_lines = []
        for line in lines:
            if "-->" in line and time_line is None:
                time_line = line
            elif not line.isdigit() and not line.startswith("WEBVTT"):
                payload_lines.append(line)
        if not time_line:
            continue
        try:
            start_raw, end_raw = [part.strip().split(" ")[0] for part in time_line.split("-->")[:2]]
            start = _parse_timestamp(start_raw)
            end = _parse_timestamp(end_raw)
            payload = _clean_caption_payload(" ".join(payload_lines))
            if payload:
                entries.append({"text": payload, "start": start, "duration": max(0.5, end - start)})
        except Exception:
            continue
    return entries


def _load_youtube_subtitles(url: str):
    """Try yt-dlp subtitle download before heavier transcription paths."""
    try:
        import yt_dlp  # type: ignore
    except Exception:
        yt_dlp = None

    temp_dir = tempfile.mkdtemp(prefix="alc_subs_")
    try:
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                if yt_dlp is not None:
                    ydl_opts = {
                        "skip_download": True,
                        "writesubtitles": True,
                        "writeautomaticsub": True,
                        "subtitleslangs": ["en", "en-US", "en-GB"],
                        "subtitlesformat": "vtt",
                        "outtmpl": os.path.join(temp_dir, "%(id)s.%(ext)s"),
                        "quiet": True,
                        "no_warnings": True,
                        "socket_timeout": 5,
                        "retries": 1,
                        "fragment_retries": 1,
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        video_id = info.get("id", "video")
                else:
                    video_id = "video"
                    subprocess.run([
                        sys.executable,
                        "-m",
                        "yt_dlp",
                        "--skip-download",
                        "--write-subs",
                        "--write-auto-subs",
                        "--sub-langs", "en,en-US,en-GB",
                        "--sub-format", "vtt",
                        "--socket-timeout", "5",
                        "--retries", "1",
                        "--fragment-retries", "1",
                        "-o", os.path.join(temp_dir, "%(id)s.%(ext)s"),
                        url,
                    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # success: break out of retry loop
                break
            except Exception as e:
                # If this was the last attempt, re-raise so outer handler logs and continues
                if attempt + 1 >= max_attempts:
                    raise
                wait = 2 ** attempt
                print(f"Subtitle download attempt {attempt+1} failed: {e}; retrying in {wait}s")
                time.sleep(wait)

        subtitle_files = []
        for root, _dirs, files in os.walk(temp_dir):
            for file_name in files:
                if file_name.endswith(('.vtt', '.srt')):
                    subtitle_files.append(os.path.join(root, file_name))

        for subtitle_file in subtitle_files:
            entries = _parse_caption_file(subtitle_file)
            if entries:
                print(f"Loaded {len(entries)} caption entries from {subtitle_file}")
                return entries
    except Exception as e:
        print(f"yt-dlp subtitle fallback failed: {e}")
    finally:
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
    return None


def _load_youtube_metadata(url: str) -> dict | None:
    try:
        import yt_dlp  # type: ignore

        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 6,
            "retries": 1,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info if isinstance(info, dict) else None
    except Exception as package_error:
        print(f"yt-dlp package metadata fallback failed: {package_error}; trying module command")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "yt_dlp", "--dump-single-json", "--skip-download", url],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=8,
            )
            import json

            return json.loads(result.stdout)
        except Exception as e:
            print(f"yt-dlp metadata fallback failed: {e}")
            return None


def _download_youtube_audio(url: str) -> str | None:
    temp_dir = tempfile.mkdtemp(prefix="alc_audio_")
    output_template = os.path.join(temp_dir, "%(id)s.%(ext)s")
    try:
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                try:
                    import yt_dlp  # type: ignore

                    ydl_opts = {
                        "format": "bestaudio/best",
                        "outtmpl": output_template,
                        "quiet": True,
                        "no_warnings": True,
                        "noplaylist": True,
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.extract_info(url, download=True)
                except Exception as package_error:
                    print(f"yt-dlp package audio download failed: {package_error}; trying module command")
                    subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "yt_dlp",
                            "--no-playlist",
                            "-f",
                            "bestaudio/best",
                            "-o",
                            output_template,
                            url,
                        ],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                break
            except Exception as e:
                if attempt + 1 >= max_attempts:
                    raise
                wait = 2 ** attempt
                print(f"Audio download attempt {attempt+1} failed: {e}; retrying in {wait}s")
                time.sleep(wait)

        audio_files = []
        for root, _dirs, files in os.walk(temp_dir):
            for file_name in files:
                if file_name.lower().endswith((".mp3", ".m4a", ".webm", ".wav", ".ogg")):
                    audio_files.append(os.path.join(root, file_name))
        if not audio_files:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

        source_path = audio_files[0]
        fd, stable_path = tempfile.mkstemp(prefix="alc_audio_", suffix=os.path.splitext(source_path)[1] or ".mp3")
        os.close(fd)
        shutil.copyfile(source_path, stable_path)
        shutil.rmtree(temp_dir, ignore_errors=True)
        return stable_path
    except Exception as e:
        print(f"yt-dlp audio fallback failed: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None


def _create_segments_from_entries(entries):
    segments = []
    previous_text = ""
    for entry in entries:
        text = _clean_caption_payload(_get_entry_value(entry, "text", ""))
        text = _trim_caption_overlap(text, previous_text)
        if not text:
            continue
        start = float(_get_entry_value(entry, "start", 0.0) or 0.0)
        duration = float(_get_entry_value(entry, "duration", 0.0) or 0.0)
        end = start + duration if duration > 0 else start + 2.0
        segments.append({"text": text, "start": start, "end": end})
        previous_text = text
    return segments


def _create_segments_from_assemblyai(result):
    words = result.get("words") or []
    segments = []
    if words:
        # If AssemblyAI provided word-level timing info, use it. If timings
        # appear to be missing (all zeros or None), fall back to an
        # estimated per-word timing approach so timestamps aren't all 0.
        total_start_values = sum([float(w.get("start") or 0.0) for w in words])
        use_word_timing = total_start_values > 0.0

        if use_word_timing:
            current_words = []
            segment_start = None
            segment_end = None
            for word in words:
                text = str(word.get("text", "")).strip()
                if not text:
                    continue
                if segment_start is None:
                    segment_start = float(word.get("start") or 0.0)
                segment_end = float(word.get("end") or segment_start or 0.0)
                current_words.append(text)
                if len(current_words) >= 40:
                    segments.append(
                        {
                            "text": " ".join(current_words).strip(),
                            "start": float(segment_start or 0.0),
                            "end": float(segment_end or (segment_start or 0.0) + 2.0),
                        }
                    )
                    current_words = []
                    segment_start = None
                    segment_end = None
            if current_words:
                segments.append(
                    {
                        "text": " ".join(current_words).strip(),
                        "start": float(segment_start or 0.0),
                        "end": float(segment_end or (segment_start or 0.0) + 2.0),
                    }
                )
        else:
            # Estimate timings: assume ~0.5s per word when real timings missing.
            transcript_text = str(result.get("text", "") or "").strip()
            words_list = transcript_text.split()
            if words_list:
                seconds_per_word = 0.5
                total_duration = max(2.0, len(words_list) * seconds_per_word)
                # Create segments of approx 40 words each
                seg_size = 40
                for i in range(0, len(words_list), seg_size):
                    seg_words = words_list[i : i + seg_size]
                    start = (i / len(words_list)) * total_duration
                    end = ((i + len(seg_words)) / len(words_list)) * total_duration
                    segments.append({"text": " ".join(seg_words).strip(), "start": float(start), "end": float(end)})

    if not segments:
        transcript_text = str(result.get("text", "")).strip()
        if transcript_text:
            segments = [{"text": transcript_text, "start": 0.0, "end": max(2.0, len(transcript_text.split()) * 0.5)}]

    return segments


def _assess_transcript_quality(transcript: str, segments: list[dict], source: str, method: str) -> dict:
    text = (transcript or "").strip()
    words = text.split()
    unique_ratio = len({w.lower().strip('.,!?;:"\'()[]{}') for w in words if w.strip()}) / max(1, len(words)) if words else 0.0
    warnings = []
    if not text:
        warnings.append("Empty transcript")
    if len(words) < 120:
        warnings.append("Short transcript")
    if len(segments) < 3:
        warnings.append("Few transcript chunks")
    if unique_ratio < 0.25 and len(words) >= 40:
        warnings.append("Highly repetitive transcript")
    if source == "unknown":
        warnings.append("Transcript source unknown")
    if source in {"youtube_metadata", "url_only"}:
        warnings.append("No real transcript was available")

    if not warnings:
        score = "high"
    elif len(warnings) == 1:
        score = "medium"
    else:
        score = "low"

    return {
        "score": score,
        "warnings": warnings,
        "word_count": len(words),
        "chunk_count": len(segments),
        "unique_ratio": round(unique_ratio, 3),
    }


def ingest_transcript(transcript, video_id, segments, source="unknown", method="unknown"):
    if not transcript:
        transcript = load_transcript()
    if not segments:
        segments = [{"text": transcript, "start": 0.0, "end": max(2.0, len(transcript.split()) * 0.5)}]

    quality = _assess_transcript_quality(transcript, segments, source, method)

    # Normalize segment timings BEFORE chunking. AssemblyAI may return
    # millisecond timestamps (large integers). If we don't normalize here,
    # `chunk_transcript` will iterate up to a huge `last_end` and produce
    # an enormous number of chunks (one per small window). Convert values
    # > 10000 to seconds and ensure end > start.
    def _normalize_segment(seg: dict) -> dict:
        def _nv(v):
            try:
                vv = float(v or 0.0)
            except Exception:
                vv = 0.0
            if vv > 10000:
                return round(vv / 1000.0, 3)
            return round(vv, 3)

        s = _nv(seg.get('start', seg.get('start_time', 0.0)))
        e = _nv(seg.get('end', seg.get('end_time', 0.0)))
        if e <= s:
            e = s + max(0.5, (len(str(seg.get('text', '')).split()) * 0.5))
        return {"text": seg.get('text', ''), "start": s, "end": e}

    norm_segments = [_normalize_segment(s) for s in segments]

    debug_norm_segments_count = len(norm_segments)
    debug_last_end = float(norm_segments[-1]['end']) if norm_segments else 0.0

    # Debug info: log last_end and transcript estimate to help diagnose
    try:
        transcript_estimate = max(2.0, len(str(transcript or "").split()) * 0.5)
        print(f"ingest_transcript: norm_segments_count={len(norm_segments)} last_end={norm_segments[-1]['end'] if norm_segments else 'N/A'} transcript_estimate={transcript_estimate}")
    except Exception:
        pass

    # Defensive clamp: if the last segment end is absurdly larger than a
    # transcript-based estimate, reduce it to avoid producing enormous
    # numbers of chunks (caused by ASR returning values in unexpected units).
    try:
        transcript_estimate = max(2.0, len(str(transcript or "").split()) * 0.5)
        last_end = norm_segments[-1]['end'] if norm_segments else transcript_estimate
        if last_end > transcript_estimate * 20:
            print(f"Warning: last_end {last_end} >> transcript_estimate {transcript_estimate}, clamping to safe value")
            norm_segments[-1]['end'] = round(transcript_estimate + 5.0, 3)
    except Exception:
        pass

    chunks = chunk_transcript(transcript, norm_segments)
    try:
        print(f"ingest_transcript: produced {len(chunks)} chunks (post-chunk)")
    except Exception:
        pass
    def _normalize_time_value(v: float) -> float:
        try:
            v = float(v or 0.0)
        except Exception:
            return 0.0
        # If timings appear to be in milliseconds (large values), convert to seconds
        if v > 10000:  # values > 10k likely in milliseconds
            return round(v / 1000.0, 3)
        return round(v, 3)

    stored_chunks = []
    for chunk in chunks:
        startv = _normalize_time_value(chunk.get('start', 0.0))
        endv = _normalize_time_value(chunk.get('end', 0.0))
        if endv <= startv:
            endv = startv + max(0.5, (len(str(chunk.get('text', '')).split()) * 0.5))
        stored_chunks.append({
            "text": chunk['text'],
            "start_time": startv,
            "end_time": endv,
            "video_id": video_id,
            "source": source,
            "method": method,
            "quality_score": quality["score"],
            "quality_warnings": quality["warnings"],
            "word_count": quality["word_count"],
            "chunk_count": quality["chunk_count"],
            "unique_ratio": quality["unique_ratio"],
        })
    store_chunks(video_id, stored_chunks)

    if not _chroma_enabled():
        return {
            "video_id": video_id,
            "chunk_count": len(chunks),
            "transcript_length": len(transcript.split()) if transcript else 0,
            "quality": quality,
            "source": source,
            "method": method,
            "debug_norm_segments_count": debug_norm_segments_count,
            "debug_last_end": debug_last_end,
        }

    embeddings = None
    if _fast_mode_enabled():
        try:
            from sentence_transformers import SentenceTransformer
            model_emb = SentenceTransformer('all-MiniLM-L6-v2')
            embeddings = model_emb.encode([c['text'] for c in chunks])
        except Exception as e:
            print(f"Embeddings failed: {e}, using keyword fallback")
            embeddings = None

    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_or_create_collection(name="transcripts")
        try:
            collection.delete(where={"video_id": video_id})
        except Exception:
            pass

        ids = [f"{video_id}_{i}" for i in range(len(chunks))]
        documents = [chunk['text'] for chunk in chunks]
        metadatas = [
            {
                "text": chunk['text'],
                "start_time": chunk['start'],
                "end_time": chunk['end'],
                "video_id": video_id,
                "source": source,
                "method": method,
                "quality_score": quality["score"],
                "quality_warnings": "; ".join(quality["warnings"]),
                "word_count": quality["word_count"],
                "chunk_count": quality["chunk_count"],
                "unique_ratio": quality["unique_ratio"],
            }
            for chunk in chunks
        ]

        if embeddings is not None and len(embeddings) != len(ids):
            print(f"Embedding length {len(embeddings)} != chunks {len(ids)}, dropping embeddings")
            embeddings = None

        if embeddings is None:
            embeddings = [_lightweight_embedding(document) for document in documents]

        collection.add(ids=ids, embeddings=[[float(value) for value in embedding] for embedding in embeddings], documents=documents, metadatas=metadatas)
    except Exception as e:
        print(f"ChromaDB failed: {e}; continuing with fast in-memory transcript store")


    return {
        "video_id": video_id,
        "chunk_count": len(chunks),
        "transcript_length": len(transcript.split()) if transcript else 0,
        "quality": quality,
        "source": source,
        "method": method,
        "debug_norm_segments_count": debug_norm_segments_count,
        "debug_last_end": debug_last_end,
    }


def ingest_assemblyai_file(file_bytes: bytes, file_name: str, video_id: str):
    if not assemblyai_available():
        raise RuntimeError("AssemblyAI is not configured. Set ASSEMBLYAI_API_KEY in .env.")
    result = transcribe_uploaded_file(file_bytes, file_name)
    transcript = str(result.get("text", "")).strip()
    segments = _create_segments_from_assemblyai(result)
    payload = ingest_transcript(transcript, video_id, segments, source="upload", method="assemblyai_file")
    payload.update({"source": "upload", "method": "assemblyai_file"})
    return payload


def ingest_video(video_url, video_id):
    transcript = None
    segments = []
    source = "unknown"
    canonical_url = _canonical_youtube_url(video_url)
    if video_url and ("youtube.com" in video_url or "youtu.be" in video_url):
        entries = _load_youtube_transcript(canonical_url)
        if entries:
            segments = _create_segments_from_entries(entries)
            transcript = " ".join([seg["text"] for seg in segments])
            source = "youtube_captions"
    # If we couldn't obtain a transcript from YouTube, avoid silently falling back
    # to a demo transcript. Ask the caller to provide a file or configure a
    # transcription provider instead.
    if not transcript:
        # Fast fallback: try auto subtitles via yt-dlp before expensive ASR.
        entries = _load_youtube_subtitles(canonical_url)
        if entries:
            segments = _create_segments_from_entries(entries)
            transcript = " ".join([seg["text"] for seg in segments])
            source = "youtube_auto_subtitles"

    if not transcript:
        # Fallback: transcribe the downloaded audio with AssemblyAI when enabled.
        if assemblyai_available() and _youtube_asr_enabled():
            tmp_path = None
            try:
                tmp_path = _download_youtube_audio(canonical_url)
                if tmp_path:
                    print(f"Downloaded audio to {tmp_path} for AssemblyAI transcription")
                    result = transcribe_file(tmp_path)
                    transcript = str(result.get("text", "")).strip()
                    segments = _create_segments_from_assemblyai(result)
                    source = "assemblyai_audio"
                else:
                    print("No audio file could be downloaded for AssemblyAI transcription")
            except Exception as e:
                print(f"yt-dlp/AssemblyAI path failed: {e}")
                transcript = None
            finally:
                try:
                    if tmp_path and os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    pass

        # Optional emergency fallback for demos: metadata-only pseudo transcript.
        # Disabled by default because it does not represent real spoken content.
        if not transcript:
            metadata = _load_youtube_metadata(canonical_url) if video_url and _metadata_fallback_enabled() else None
            if metadata and _metadata_fallback_enabled():
                title = metadata.get("title") or "Unknown title"
                description = metadata.get("description") or ""
                uploader = metadata.get("uploader") or metadata.get("channel") or "Unknown channel"
                tags = metadata.get("tags") or []
                pieces = [
                    f"Video title: {title}",
                    f"Channel: {uploader}",
                ]
                if description:
                    pieces.append(f"Description: {description[:1000]}")
                if tags:
                    pieces.append(f"Tags: {', '.join(tags[:20])}")
                transcript = "\n".join(pieces)
                segments = [{"text": transcript, "start": 0.0, "end": 4.0}]
                source = "youtube_metadata"
            else:
                raise RuntimeError(
                    "No transcript could be extracted from this YouTube video. "
                    "Try a video with auto-captions enabled, upload the file directly, "
                    "or configure ASSEMBLYAI_API_KEY for audio transcription fallback."
                )

    payload = ingest_transcript(transcript, video_id, segments, source=source, method=source)
    payload.update({"source": source, "method": source})
    return payload
