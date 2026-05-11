import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ASSEMBLYAI_UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
ASSEMBLYAI_TRANSCRIPT_URL = "https://api.assemblyai.com/v2/transcript"


def _get_api_key() -> str | None:
    return os.getenv("ASSEMBLYAI_API_KEY") or os.getenv("ASSEMBLY_API_KEY")


def assemblyai_available() -> bool:
    return bool(_get_api_key())


def _request_json(url: str, method: str = "GET", headers: dict | None = None, body: dict | None = None):
    payload = None
    request_headers = headers or {}
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=payload, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"AssemblyAI request failed ({error.code}): {error_body}") from error


def _upload_file(path: str) -> str:
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("ASSEMBLYAI_API_KEY is not configured")

    request = urllib.request.Request(
        ASSEMBLYAI_UPLOAD_URL,
        method="POST",
        headers={
            "authorization": api_key,
            "Content-Type": "application/octet-stream",
            "Accept": "application/json",
        },
    )
    with open(path, "rb") as file_handle:
        data = file_handle.read()
    request.data = data

    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["upload_url"]
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"AssemblyAI upload failed ({error.code}): {error_body}") from error


def _transcript_payload(audio_url: str) -> dict:
    return {
        "audio_url": audio_url,
        "punctuate": True,
        "format_text": True,
        "speaker_labels": False,
        "language_detection": False,
        "language_code": "en",
        "speech_models": ["universal-2"],
        "word_boost": [],
    }


def _poll_transcript(transcript_id: str, timeout_seconds: int = 900):
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("ASSEMBLYAI_API_KEY is not configured")

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        response = _request_json(
            f"{ASSEMBLYAI_TRANSCRIPT_URL}/{urllib.parse.quote(transcript_id)}",
            headers={"authorization": api_key},
        )
        status = response.get("status")
        if status == "completed":
            return response
        if status == "error":
            raise RuntimeError(response.get("error", "AssemblyAI transcription failed"))
        time.sleep(4)

    raise TimeoutError("AssemblyAI transcription timed out")


def transcribe_file(path: str) -> dict:
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("ASSEMBLYAI_API_KEY is not configured")

    upload_url = _upload_file(path)
    transcript = _request_json(
        ASSEMBLYAI_TRANSCRIPT_URL,
        method="POST",
        headers={"authorization": api_key},
        body=_transcript_payload(upload_url),
    )
    transcript_id = transcript["id"]
    return _poll_transcript(transcript_id)


def transcribe_uploaded_file(file_bytes: bytes, file_name: str | None = None) -> dict:
    suffix = Path(file_name or "upload").suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name
    try:
        return transcribe_file(temp_path)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass