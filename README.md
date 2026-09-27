#  Alexandria – AI Video Learning Companion

<div align="center">

![Alexandria Banner](https://img.shields.io/badge/Alexandria-AI%20Learning%20Companion-06b6d4?style=for-the-badge&logo=leaflet&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)

**The #1 Free AI-powered video summarizer — get expert-level summaries, key moments, and interactive Q&A from any YouTube video in one click.**

[🚀 Live Demo](#) · [📖 API Docs](#api-reference) · [🐛 Report Bug](https://github.com/t00fan01/Alexendria/issues) · [✨ Request Feature](https://github.com/t00fan01/Alexendria/issues)

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎬 **YouTube Ingestion** | Paste any YouTube URL — captions extracted instantly |
| 📁 **File Upload** | Upload `.mp4`, `.mp3`, `.webm` for AssemblyAI transcription |
| 🧠 **AI Summaries** | Gemini-powered overall, topic-wise, and last-N-minutes summaries |
| 💬 **Contextual Q&A** | RAG-based chat with streaming responses and timestamp citations |
| ⏱️ **Timeline Navigation** | Click any timestamp to jump to that exact moment in the video |
| 📊 **Video Chapters** | Auto-generated chapters with animated loading state |
| 🗺️ **Topic Mind Map** | Visual breakdown of key concepts from the video |
| 📱 **Fully Responsive** | Works beautifully on desktop, tablet, and mobile |

---

## 🏗️ Architecture

```
Alexendria/
├── backend/                  # FastAPI Python backend
│   ├── main.py               # API routes & job orchestration
│   ├── ingest.py             # YouTube & file ingestion pipeline
│   ├── rag.py                # Retrieval-Augmented Generation (Q&A)
│   ├── summarizer.py         # Multi-mode AI summarization
│   ├── quiz.py               # Quiz generation via Gemini
│   ├── session.py            # Conversation memory
│   ├── requirements.txt      # Python dependencies
│   └── utils/
│       ├── chunker.py
│       ├── transcript_store.py
│       ├── quick_summary.py
│       └── env_loader.py
├── frontend/                 # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx           # Main application layout
│   │   ├── index.css         # Design system & global styles
│   │   ├── responsive.css    # Mobile/tablet breakpoints
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   ├── IngestPanel.jsx
│   │   │   ├── VideoPlayer.jsx
│   │   │   ├── ChatPanel.jsx
│   │   │   ├── SummaryDashboard.jsx
│   │   │   ├── Timeline.jsx
│   │   │   ├── QuizPanel.jsx
│   │   │   ├── PdfExport.jsx
│   │   │   └── SkeletonLoader.jsx
│   │   └── api/              # API client helpers
│   └── index.html
├── render.yaml               # One-click Render.com deploy config
├── .env.example              # Environment variable template (safe to commit)
└── README.md
```

---

## 🚀 Quick Start (For Developers)

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- A **Google Gemini API key** → [Get one free](https://aistudio.google.com/app/apikey)
- An **AssemblyAI API key** *(optional, for file upload)* → [Get one free](https://www.assemblyai.com/)

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/t00fan01/Alexendria.git
cd Alexendria
```

---

### Step 2 — Configure Environment Variables

```bash
# Copy the safe template
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux
```

Open `.env` and fill in your API keys:

```env
GOOGLE_API_KEY=your_google_gemini_api_key_here
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
```

> ⚠️ **Never commit your `.env` file.** It is already listed in `.gitignore`.

---

### Step 3 — Set Up & Run the Backend

```powershell
# Create a virtual environment
python -m venv .venv

# Activate it (Windows)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt

# Start the API server
python -m uvicorn backend.main:app --reload --port 8000
```

The backend API will be live at:
- **API Root:** http://localhost:8000
- **Swagger Docs:** http://localhost:8000/docs

---

### Step 4 — Set Up & Run the Frontend

Open a **new terminal** (keep the backend running):

```powershell
cd frontend
npm install
npm run dev
```

The app will be available at **http://localhost:5173** 🎉

---

### One-liner to launch both (Windows)

```powershell
# From the project root — opens two PowerShell windows
start powershell -ArgumentList '-NoExit', '-Command', 'python -m uvicorn backend.main:app --reload --port 8000'
start powershell -ArgumentList '-NoExit', '-Command', 'cd .\frontend; npm run dev'
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check & feature list |
| `POST` | `/ingest` | Ingest a YouTube video by URL |
| `POST` | `/ingest-file` | Upload a local audio/video file |
| `GET` | `/ingest-status/{job_id}` | Poll ingestion job progress |
| `POST` | `/ask` | Ask a question about a video |
| `POST` | `/ask/stream` | Streaming Q&A with NDJSON response |
| `GET` | `/summary/{video_id}` | Get overall AI summary |
| `GET` | `/topic-summaries/{video_id}` | Get topic-wise breakdown |
| `GET` | `/timestamps/{video_id}` | Get chapter timeline |
| `GET` | `/analysis/{video_id}` | Full analysis (summary + topics + timeline) |
| `GET` | `/health` | Service health status |

---

## ☁️ Deployment

### Deploy to Render (Recommended — Free Tier)

1. Fork this repo to your GitHub account
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your GitHub repo — Render will auto-detect `render.yaml`
4. Add your environment variables in the Render dashboard:
   - `GOOGLE_API_KEY`
   - `ASSEMBLYAI_API_KEY`
5. Deploy! 🎉

### Deploy Frontend to Vercel

```bash
cd frontend
npm run build
# Upload the dist/ folder to Vercel or Netlify
```

---

## 🔧 Configuration

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | ✅ Yes | Google Gemini API key for AI summarization & Q&A |
| `ASSEMBLYAI_API_KEY` | ⚠️ Optional | AssemblyAI key for file upload transcription |
| `YOUTUBE_API_KEY` | ⚠️ Optional | YouTube Data API for richer video metadata |
| `ENABLE_CHROMA` | ❌ No | Set to `1` to enable persistent ChromaDB vector store |
| `ENABLE_EMBEDDINGS` | ❌ No | Set to `1` to enable semantic embedding search |
| `ENABLE_YOUTUBE_ASR` | ❌ No | Set to `0` to disable YouTube caption extraction |

---

## 🗺️ Roadmap

- [x] YouTube ingestion pipeline
- [x] Local file upload with AssemblyAI
- [x] Streaming Q&A chat
- [x] Timeline navigation with animated loading state
- [x] Topic-wise summaries
- [x] PDF export of study notes
- [x] Quiz generation via Gemini
- [x] Fully responsive design
- [ ] **Chrome Extension** *(coming soon)*
- [ ] User accounts & saved sessions
- [ ] Multi-language support

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License.

---

<div align="center">
  Made with 🌿 by Team Lemon
</div>
