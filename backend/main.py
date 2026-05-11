from .utils.env_loader import load_project_env
load_project_env()

from fastapi import FastAPI, HTTPException
from fastapi import UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import uuid
import json
import re
import os
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from datetime import datetime
from .ingest import ingest_video, ingest_assemblyai_file
from .rag import ask_question
from .summarizer import get_summary, get_topic_summaries, get_last_minutes_summary
from .session import get_session_history, add_to_session
from .utils.transcript_store import get_chunks
from .utils.quick_summary import generate_quick_summary, is_gemini_error
from .quiz import generate_quiz_from_chunks, generate_quiz_from_text

app = FastAPI(
    title="AI Learning Companion",
    description="RAG-based video learning assistant for LMS",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=2)
ingest_jobs: dict[str, dict] = {}
ingest_jobs_lock = Lock()

class IngestRequest(BaseModel):
    video_url: str


class LocalUploadRequest(BaseModel):
    title: str | None = None

class AskRequest(BaseModel):
    video_id: str
    question: str
    session_id: str = None


def _set_ingest_job(job_id: str, payload: dict):
    with ingest_jobs_lock:
        ingest_jobs[job_id] = payload


def _get_ingest_job(job_id: str):
    with ingest_jobs_lock:
        return ingest_jobs.get(job_id)


def _extract_youtube_id(url: str) -> str | None:
    patterns = [
        r"(?:v=|/)([0-9A-Za-z_-]{11})(?:[&?]|$)",
        r"youtu\.be/([0-9A-Za-z_-]{11})(?:[&?]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def _chroma_enabled() -> bool:
    return os.getenv("ENABLE_CHROMA", "0").strip().lower() in {"1", "true", "yes", "on"}


def _build_fast_preview(video_url: str) -> dict:
    video_id = _extract_youtube_id(video_url) if video_url else None
    preview_summary = "Processing started. The transcript will appear in the background, then the summary will refresh automatically."
    preview_title = "Video preview"
    source = "video"

    if not video_id:
        return {
            "preview_title": preview_title,
            "preview_summary": preview_summary,
            "source": source,
        }

    source = "youtube"
    preview_title = f"YouTube video {video_id}"
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        request = Request(oembed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
            title = payload.get("title") or preview_title
            author = payload.get("author_name") or "YouTube"
            preview_title = title
            preview_summary = (
                f"Fast preview: {title}."
                f" We are extracting captions or audio from {author} in the background, so the final summary will update automatically."
            )
    except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
        preview_summary = (
            f"Fast preview: YouTube video {video_id} has been queued."
            " The app is extracting transcript data now, and the final summary will refresh automatically."
        )

    return {
        "preview_title": preview_title,
        "preview_summary": preview_summary,
        "source": source,
    }


def _run_ingest_video_job(job_id: str, video_id: str, video_url: str):
    """Run ingest job with progress tracking."""
    try:
        # Update progress: downloading
        existing = _get_ingest_job(job_id) or {}
        _set_ingest_job(job_id, {
            **existing,
            "job_id": job_id,
            "video_id": video_id,
            "status": "processing",
            "step": 1,
            "step_name": "Downloading video metadata and audio",
            "progress": 15,
            "message": "Fetching video information and extracting audio/captions...",
            "started_at": datetime.now().isoformat(),
        })
        
        # Run the actual ingestion
        result = ingest_video(video_url, video_id)
        
        # Update progress: processing
        _set_ingest_job(job_id, {
            **existing,
            **result,
            "job_id": job_id,
            "video_id": video_id,
            "status": "processing",
            "step": 2,
            "step_name": "Transcribing and processing",
            "progress": 50,
            "message": "Extracting and organizing transcript content...",
            "transcript_length": len(result.get("transcript", "")),
        })
        
        # Update progress: completed
        _set_ingest_job(job_id, {
            **existing,
            **result,
            "job_id": job_id,
            "video_id": video_id,
            "status": "completed",
            "step": 3,
            "step_name": "Complete",
            "progress": 100,
            "message": "Video ingested successfully.",
            "result": result,
            "completed_at": datetime.now().isoformat(),
        })
    except Exception as e:
        print(f"Ingest job failed: {e}")
        _set_ingest_job(job_id, {
            "job_id": job_id,
            "video_id": video_id,
            "status": "failed",
            "message": str(e),
            "error_details": repr(e),
            "failed_at": datetime.now().isoformat(),
        })


def _run_ingest_file_job(job_id: str, video_id: str, file_bytes: bytes, file_name: str):
    """Run file ingest job with progress tracking."""
    try:
        existing = _get_ingest_job(job_id) or {}
        _set_ingest_job(job_id, {
            **existing,
            "job_id": job_id,
            "video_id": video_id,
            "status": "processing",
            "step": 1,
            "step_name": "Uploading and transcribing",
            "progress": 25,
            "message": "Processing uploaded file...",
            "started_at": datetime.now().isoformat(),
        })
        
        result = ingest_assemblyai_file(file_bytes, file_name, video_id)
        
        existing = _get_ingest_job(job_id) or {}
        _set_ingest_job(job_id, {
            **existing,
            **result,
            "job_id": job_id,
            "video_id": video_id,
            "status": "completed",
            "step": 2,
            "step_name": "Complete",
            "progress": 100,
            "message": "File ingested successfully.",
            "result": result,
            "completed_at": datetime.now().isoformat(),
        })
    except Exception as e:
        print(f"File ingest job failed: {e}")
        _set_ingest_job(job_id, {
            "job_id": job_id,
            "video_id": video_id,
            "status": "failed",
            "message": str(e),
            "error_details": repr(e),
            "failed_at": datetime.now().isoformat(),
        })

@app.get("/")
def root():
    return {
        "message": "AI Learning Companion backend is running",
        "docs": "http://localhost:8000/docs",
        "features": [
            "Contextual Q&A from video transcripts",
            "Smart summaries (overall, topic-wise, last 5 minutes)",
            "Jump-to-moment navigation via timestamps",
            "Session memory for multi-turn conversations",
            "Free AssemblyAI transcription fallback when YouTube captions are missing"
        ]
    }

@app.get("/ping")
def ping():
    return {"message": "working", "status": "ok"}

@app.post("/ingest")
def ingest(request: IngestRequest):
    try:
        job_id = str(uuid.uuid4())
        video_id = str(uuid.uuid4())
        preview = _build_fast_preview(request.video_url)
        print(f"Ingest request received for video_url={request.video_url} assign video_id={video_id} job_id={job_id}")
        job_data = {
            "job_id": job_id,
            "video_id": video_id,
            "status": "processing",
            "step": 0,
            "step_name": "Starting...",
            "progress": 5,
            "message": "Ingest job started",
            "started_at": datetime.now().isoformat(),
            **preview,
        }
        _set_ingest_job(job_id, job_data)
        executor.submit(_run_ingest_video_job, job_id, video_id, request.video_url)
        return job_data
    except Exception as e:
        print(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)}")


@app.post("/ingest-file")
async def ingest_file(file: UploadFile = File(...), title: str | None = Form(None)):
    try:
        job_id = str(uuid.uuid4())
        video_id = str(uuid.uuid4())
        file_bytes = await file.read()
        print(f"File ingest request received for file={file.filename} assign video_id={video_id} job_id={job_id}")
        job_data = {
            "job_id": job_id,
            "video_id": video_id,
            "status": "processing",
            "step": 0,
            "step_name": "Uploading file...",
            "progress": 10,
            "message": "Ingest job started",
            "started_at": datetime.now().isoformat(),
        }
        _set_ingest_job(job_id, job_data)
        executor.submit(_run_ingest_file_job, job_id, video_id, file_bytes, file.filename or title or "upload")
        return job_data
    except Exception as e:
        print(f"File ingest failed: {e}")
        raise HTTPException(status_code=500, detail=f"File ingest failed: {str(e)}")


@app.get("/ingest-status/{job_id}")
def ingest_status(job_id: str):
    job = _get_ingest_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    return job

@app.post("/ask")
def ask(request: AskRequest):
    try:
        print(f"Ask request received for video_id={request.video_id} question={request.question}")
        history = get_session_history(request.session_id) if request.session_id else []
        answer, timestamps = ask_question(request.video_id, request.question, history)
        if request.session_id:
            add_to_session(request.session_id, request.question, answer)
        return {
            "answer": answer,
            "timestamps": timestamps,
            "session_id": request.session_id or str(uuid.uuid4()),
            "status": "success"
        }
    except Exception as e:
        print(f"Ask failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ask failed: {str(e)}")

@app.post("/ask/stream")
def ask_stream(request: AskRequest):
    try:
        print(f"Stream ask request for video_id={request.video_id}")
        history = get_session_history(request.session_id) if request.session_id else []
        answer, timestamps = ask_question(request.video_id, request.question, history)
        
        def generate():
            for char in answer:
                yield json.dumps({"chunk": char}) + "\n"
            yield json.dumps({"timestamps": timestamps, "done": True}) + "\n"
        
        if request.session_id:
            add_to_session(request.session_id, request.question, answer)
        
        return StreamingResponse(generate(), media_type="application/x-ndjson")
    except Exception as e:
        print(f"Stream ask failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stream ask failed: {str(e)}")

@app.get("/summary/{video_id}")
def summary(video_id: str):
    try:
        # Use summarizer helper that reports which method was used
        from .summarizer import get_summary_with_method
        summary_text, method = get_summary_with_method(video_id)
        status = "success"
        if method == "none":
            status = "no_data"
        return {
            "video_id": video_id,
            "summary": summary_text,
            "type": "overall",
            "method": method,
            "status": status,
        }
    except Exception as e:
        # As a last-resort fallback, try quick extractive summary
        print(f"Summary endpoint error: {e}; attempting quick extractive fallback")
        try:
            from .utils.transcript_store import get_chunks
            chunks = get_chunks(video_id)
            if chunks:
                transcript = " ".join([c.get("text", "") for c in chunks])
                quick_result = generate_quick_summary(transcript)
                return {
                    "video_id": video_id,
                    "summary": quick_result.get("summary"),
                    "type": "overall",
                    "method": "extractive_fallback",
                    "status": "success_fallback",
                    "note": "Using quick extractive summary (error path)"
                }
        except Exception as fallback_err:
            print(f"Fallback failed: {fallback_err}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/topic-summaries/{video_id}")
def topic_summaries(video_id: str):
    try:
        topics = get_topic_summaries(video_id)
        if not topics:
            return {
                "video_id": video_id,
                "topics": [],
                "status": "no_data",
                "message": "No topics found. Please ingest a video first."
            }
        return {
            "video_id": video_id,
            "topics": topics,
            "count": len(topics),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/last-minutes/{video_id}")
def last_minutes(video_id: str, minutes: int = 5):
    try:
        if minutes < 1 or minutes > 60:
            raise ValueError("Minutes must be between 1 and 60")
        result = get_last_minutes_summary(video_id, minutes)
        return {
            "video_id": video_id,
            "minutes": minutes,
            "summary": result.get("summary"),
            "timestamp": result.get("timestamp"),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/timestamps/{video_id}")
def timestamps(video_id: str):
    try:
        fs = get_chunks(video_id)
        if fs:
            ts = [
                {
                    # Preserve sub-second precision for jump-to timestamps
                    # Normalize values that are likely in milliseconds (> 10k)
                    "time": (lambda v: round(v / 1000.0, 3) if v > 10000 else round(v, 3))(float(c.get('start_time', 0.0) or 0.0)),
                    "label": (c.get('text') or f"Chunk {i + 1}")[:64],
                    "duration": (lambda s, e: round((e - s) / 1000.0, 3) if (e - s) > 10000 else round((e - s), 3))(
                        float(c.get('start_time', 0.0) or 0.0), float(c.get('end_time', 0.0) or 0.0)
                    ),
                }
                for i, c in enumerate(fs)
            ]
            return {
                "video_id": video_id,
                "timestamps": ts,
                "count": len(ts),
                "status": "success"
            }

        if not _chroma_enabled():
            return {
                "video_id": video_id,
                "timestamps": [{"time": 0.0, "label": "Start", "duration": 0.0}],
                "status": "no_data"
            }

        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="transcripts")
        results = collection.get(where={"video_id": video_id})
        if not results['ids']:
            raise Exception("No timestamps found")
        ts = [
            {
                "time": (lambda v: round(v / 1000.0, 3) if v > 10000 else round(v, 3))(float(metadata.get('start_time', 0.0) or 0.0)),
                "label": f"Chunk {i + 1}",
                "duration": (lambda s, e: round((e - s) / 1000.0, 3) if (e - s) > 10000 else round((e - s), 3))(
                    float(metadata.get('start_time', 0.0) or 0.0), float(metadata.get('end_time', 0.0) or 0.0)
                )
            }
            for i, metadata in enumerate(results['metadatas'])
        ]
        return {
            "video_id": video_id,
            "timestamps": ts,
            "count": len(ts),
            "status": "success"
        }
    except Exception as e:
        print(f"Timestamps failed: {e}")
        return {
            "video_id": video_id,
            "timestamps": [{"time": 0.0, "label": "Start", "duration": 0.0}],
            "status": "no_data"
        }


@app.get("/analysis/{video_id}")
def analysis(video_id: str):
    try:
        # Use summarizer helper that can report method
        from .summarizer import get_summary_with_method
        summary_text, _method = get_summary_with_method(video_id)
        topics = get_topic_summaries(video_id)
        recent = get_last_minutes_summary(video_id, 5)
        timeline = timestamps(video_id)
        quality_report = quality(video_id)

        has_real_summary = summary_text and not summary_text.startswith("Summary is not available yet")
        ready = bool(has_real_summary or topics or timeline.get("status") == "success")
        return {
            "video_id": video_id,
            "summary": summary_text,
            "topics": topics,
            "recent_summary": recent.get("summary"),
            "recent_timestamp": recent.get("timestamp"),
            "timestamps": timeline.get("timestamps", []),
            "quality": quality_report.get("quality"),
            "status": "success" if ready else "processing",
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/videos")
def list_videos():
    """List all video_ids currently stored in the transcripts collection."""
    try:
        if not _chroma_enabled():
            return {"video_ids": [], "count": 0, "status": "disabled"}

        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="transcripts")
        results = collection.get()
        vids = set()
        for meta in results.get('metadatas', []):
            vid = meta.get('video_id')
            if vid:
                vids.add(vid)
        return {"video_ids": sorted(list(vids)), "count": len(vids), "status": "success"}
    except Exception as e:
        print(f"List videos failed: {e}")
        return {"video_ids": [], "count": 0, "status": "error", "message": str(e)}


def _quality_response(video_id: str, first: dict, status: str = "success"):
    warnings = first.get("quality_warnings") or []
    if isinstance(warnings, str):
        warnings = [part.strip() for part in warnings.split(";") if part.strip()]
    return {
        "video_id": video_id,
        "quality": {
            "score": first.get("quality_score", "unknown"),
            "warnings": warnings,
            "word_count": int(first.get("word_count", 0) or 0),
            "chunk_count": int(first.get("chunk_count", 0) or 0),
            "unique_ratio": float(first.get("unique_ratio", 0.0) or 0.0),
            "source": first.get("source", "unknown"),
            "method": first.get("method", "unknown"),
        },
        "status": status,
    }


@app.get("/quality/{video_id}")
def quality(video_id: str):
    """Return a compact quality report for the stored transcript."""
    try:
        fs = get_chunks(video_id)
        if fs:
            return _quality_response(video_id, fs[0])

        if not _chroma_enabled():
            return {
                "video_id": video_id,
                "quality": {"score": "none", "warnings": ["No transcript data found"], "word_count": 0, "chunk_count": 0, "unique_ratio": 0.0},
                "status": "no_data",
            }

        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="transcripts")
        results = collection.get(where={"video_id": video_id})
        if not results.get("metadatas"):
            return {
                "video_id": video_id,
                "quality": {"score": "none", "warnings": ["No transcript data found"], "word_count": 0, "chunk_count": 0, "unique_ratio": 0.0},
                "status": "no_data",
            }

        first = results["metadatas"][0]
        return _quality_response(video_id, first)
    except Exception as e:
        print(f"Quality endpoint failed: {e}")
        return {
            "video_id": video_id,
            "quality": {"score": "none", "warnings": ["No transcript data found"], "word_count": 0, "chunk_count": 0, "unique_ratio": 0.0},
            "status": "no_data",
        }


@app.post("/videos/{video_id}/clear")
def clear_video(video_id: str):
    """Delete all transcript entries for a given video_id from ChromaDB and in-memory store."""
    try:
        from .utils.transcript_store import clear_chunks
        if _chroma_enabled():
            import chromadb
            client = chromadb.PersistentClient(path="./chroma_db")
            collection = client.get_collection(name="transcripts")
            try:
                collection.delete(where={"video_id": video_id})
            except Exception as e:
                print(f"Chroma delete warning: {e}")
        clear_chunks(video_id)
        return {"video_id": video_id, "status": "cleared"}
    except Exception as e:
        print(f"Clear video failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/quiz/{video_id}")
def get_quiz(video_id: str, num_questions: int = 5):
    try:
        questions = generate_quiz_from_chunks(video_id, num_questions)
        if not questions:
            return {
                "video_id": video_id,
                "questions": [],
                "status": "no_data",
                "message": "Could not generate quiz. Ensure video is ingested first."
            }
        return {
            "video_id": video_id,
            "questions": questions,
            "count": len(questions),
            "status": "success"
        }
    except Exception as e:
        print(f"Quiz generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/quiz-from-text")
def get_quiz_from_text(text: str, num_questions: int = 5):
    try:
        questions = generate_quiz_from_text(text, num_questions)
        return {
            "questions": questions,
            "count": len(questions),
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "AI Learning Companion Backend",
        "version": "1.0.0"
    }
