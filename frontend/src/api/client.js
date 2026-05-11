const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

async function parseResponse(response, fallbackMessage) {
  const result = await response.json().catch(() => ({}));
  if (response.ok) {
    return result;
  }
  throw new Error(result.detail || result.message || fallbackMessage);
}

export async function ingestVideo(videoUrl) {
  try {
    const response = await fetch(`${API_BASE}/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_url: videoUrl })
    });
    return await parseResponse(response, 'Failed to ingest video');
  } catch (error) {
    throw new Error(`Backend unreachable at ${API_BASE}. Start the API server and try again.`);
  }
}

export async function ingestFile(file, title = '') {
  const formData = new FormData();
  formData.append('file', file);
  if (title) {
    formData.append('title', title);
  }

  try {
    const response = await fetch(`${API_BASE}/ingest-file`, {
      method: 'POST',
      body: formData,
    });
    return await parseResponse(response, 'Failed to ingest file');
  } catch (error) {
    throw new Error(`Backend unreachable at ${API_BASE}. Start the API server and try again.`);
  }
}

export async function getIngestStatus(jobId) {
  const response = await fetch(`${API_BASE}/ingest-status/${jobId}`);
  return await parseResponse(response, 'Failed to get ingest status');
}

export async function getAnalysis(videoId) {
  const response = await fetch(`${API_BASE}/analysis/${videoId}`);
  if (response.ok) {
    return await response.json();
  }

  if (response.status !== 404) {
    const result = await response.json().catch(() => ({}));
    throw new Error(result.detail || result.message || 'Failed to get analysis');
  }

  const [overall, topics, recent, timestamps, quality] = await Promise.all([
    getOverallSummary(videoId).catch(() => null),
    getTopicSummaries(videoId).catch(() => null),
    getLastMinutesSummary(videoId, 5).catch(() => null),
    getTimestamps(videoId).catch(() => null),
    getQuality(videoId).catch(() => null),
  ]);

  const summary = overall?.summary || 'Summary is not available yet. Please ingest a video first.';
  const topicList = Array.isArray(topics?.topics) ? topics.topics : [];
  const timestampList = Array.isArray(timestamps?.timestamps) ? timestamps.timestamps : [];
  const ready = !summary.startsWith('Summary is not available yet') || topicList.length > 0 || timestamps?.status === 'success';

  return {
    video_id: videoId,
    summary,
    topics: topicList,
    recent_summary: recent?.summary,
    recent_timestamp: recent?.timestamp,
    timestamps: timestampList,
    quality: quality?.quality,
    status: ready ? 'success' : 'processing',
  };
}

export async function getOverallSummary(videoId) {
  const response = await fetch(`${API_BASE}/summary/${videoId}`);
  if (!response.ok) throw new Error('Failed to get summary');
  return await response.json();
}

export async function getTopicSummaries(videoId) {
  const response = await fetch(`${API_BASE}/topic-summaries/${videoId}`);
  if (!response.ok) throw new Error('Failed to get topic summaries');
  return await response.json();
}

export async function getLastMinutesSummary(videoId, minutes = 5) {
  const response = await fetch(`${API_BASE}/last-minutes/${videoId}?minutes=${minutes}`);
  if (!response.ok) throw new Error('Failed to get recent summary');
  return await response.json();
}

export async function getTimestamps(videoId) {
  const response = await fetch(`${API_BASE}/timestamps/${videoId}`);
  if (!response.ok) throw new Error('Failed to get timestamps');
  return await response.json();
}

export async function getQuality(videoId) {
  const response = await fetch(`${API_BASE}/quality/${videoId}`);
  if (!response.ok) throw new Error('Failed to get quality');
  return await response.json();
}

// Helper to handle the NDJSON streaming response from /ask/stream
export async function askQuestionStream(videoId, question, sessionId, onChunk, onTimestamps, onDone, onError) {
  try {
    const response = await fetch(`${API_BASE}/ask/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        video_id: videoId,
        question: question,
        session_id: sessionId
      })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Streaming failed');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const json = JSON.parse(line);
          if (json.chunk) {
            onChunk(json.chunk);
          }
          if (json.timestamps && json.timestamps.length > 0) {
            onTimestamps(json.timestamps);
          }
        } catch (e) {
          console.warn('Failed to parse NDJSON line:', line);
        }
      }
    }
    if (buffer.trim()) {
      try {
        const json = JSON.parse(buffer);
        if (json.chunk) onChunk(json.chunk);
        if (json.timestamps && json.timestamps.length > 0) onTimestamps(json.timestamps);
      } catch (e) {
        console.warn('Failed to parse final NDJSON line:', buffer);
      }
    }
    onDone();
  } catch (error) {
    onError(error);
  }
}

export async function getQuiz(videoId, numQuestions = 5) {
  const response = await fetch(`${API_BASE}/quiz/${videoId}?num_questions=${numQuestions}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  return await parseResponse(response, 'Failed to generate quiz');
}
