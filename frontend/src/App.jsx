import React, { useState, useRef } from 'react';
import { Leaf, BrainCircuit, Mic, FileText, Layout, ArrowRight, Link as LinkIcon, Image as ImageIcon, File as FileIcon } from 'lucide-react';
import Navbar from './components/Navbar';
import IngestPanel from './components/IngestPanel';
import VideoPlayer from './components/VideoPlayer';
import ChatPanel from './components/ChatPanel';
import SummaryDashboard from './components/SummaryDashboard';
import Timeline from './components/Timeline';
import customLogo from './assets/logo.png';
import './index.css';

const FAQItem = ({ question, answer }) => {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className="faq-item" onClick={() => setIsOpen(!isOpen)}>
      <div className="faq-question">
        {question}
        <div style={{ transform: isOpen ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease' }}>
          <ArrowRight size={20} />
        </div>
      </div>
      {isOpen && (
        <div className="fade-in" style={{ marginTop: '1rem', color: 'var(--text-secondary)', lineHeight: 1.6, fontSize: '1.05rem' }}>
          {answer}
        </div>
      )}
    </div>
  );
};

function App() {
  const [videoId, setVideoId] = useState(null);
  const [youtubeId, setYoutubeId] = useState(null);
  const [ingestInfo, setIngestInfo] = useState(null);
  const playerRef = useRef(null);
  const isProcessing = ingestInfo?.status === 'processing';

  const handleIngestSuccess = (id, ytId, info) => {
    setVideoId(id);
    setYoutubeId(ytId);
    setIngestInfo(info || null);
    // Smooth scroll to results
    setTimeout(() => {
      window.scrollTo({ top: 800, behavior: 'smooth' });
    }, 100);
  };

  const handleTimestampClick = (seconds) => {
    if (playerRef.current) {
      playerRef.current.seekTo(seconds);
    }
  };

  return (
    <>
      <div className="bg-aurora">
        <div className="aurora-1"></div>
        <div className="aurora-2"></div>
        <div className="aurora-3"></div>
      </div>

      <Navbar />

      <main style={{ paddingTop: '100px', minHeight: '100vh' }}>
        {/* Hero Section - Only show when no video or as top section */}
        {!videoId && (
          <>
            <section id="dashboard" className="hero-section" style={{
              textAlign: 'center',
              maxWidth: '1000px',
              margin: '6rem auto 4rem',
              padding: '0 2rem'
            }}>
              <div className="hero-badge fade-in" style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 1.25rem',
                borderRadius: '999px',
                background: 'var(--primary-fixed)',
                color: 'var(--on-primary-fixed-variant)',
                fontSize: '0.9rem',
                fontWeight: 600,
                marginBottom: '2rem',
                border: '1px solid var(--primary-fixed-dim)'
              }}>
                <BrainCircuit size={16} />
                <span>🌿 Botanical Intelligence • Trusted by 50,000+ Learners</span>
              </div>

              <h1 className="font-display fade-in" style={{ 
                fontSize: '4rem', 
                lineHeight: 1.15, 
                marginBottom: '2rem', 
                fontWeight: 800, 
                color: '#312e81',
                letterSpacing: '-0.02em'
              }}>
                Distill the <span style={{ color: '#8b5cf6' }}>noise</span>. <br />
                Discover the <span style={{ color: '#0d9488' }}>essence</span>.
              </h1>

              <p className="hero-subtitle fade-in" style={{ fontSize: '1.4rem', color: 'var(--on-surface-variant)', maxWidth: '800px', margin: '0 auto 3rem', lineHeight: 1.6 }}>
                Alexandria is the industry's <b>most intelligent</b>—get expert-level AI summaries, key moments,
                and mind maps. All in one click with no prompts required.
              </p>

              <div className="fade-in" style={{ maxWidth: '750px', margin: '0 auto', position: 'relative' }}>

                <IngestPanel onIngestSuccess={handleIngestSuccess} />

                <div className="platform-icons fade-in" style={{ animationDelay: '0.2s' }}>
                  <img src="https://cdn-icons-png.flaticon.com/512/1384/1384060.png" className="platform-icon" alt="YouTube" />
                  <img src="https://cdn-icons-png.flaticon.com/512/5968/5968812.png" className="platform-icon" alt="Twitch" />
                  <img src="https://cdn-icons-png.flaticon.com/512/2111/2111710.png" className="platform-icon" alt="Vimeo" />
                  <img src="https://cdn-icons-png.flaticon.com/512/2991/2991148.png" className="platform-icon" alt="Google Drive" />
                </div>
              </div>

              <div className="chrome-badge-container fade-in" style={{ animationDelay: '0.3s' }}>
                <a href="#" className="chrome-badge">
                  <img src="https://upload.wikimedia.org/wikipedia/commons/e/e1/Google_Chrome_icon_%28February_2022%29.svg" alt="Chrome" style={{ width: '32px' }} />
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>Featured by Chrome</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 700 }}>Add to Chrome — It's Free</div>
                  </div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, borderLeft: '1px solid rgba(255,255,255,0.2)', paddingLeft: '1rem' }}>
                    4.9/5
                  </div>
                </a>
              </div>
            </section>

            {/* Steps Section */}
            <section id="how-it-works" className="section-container">
              <h2 className="section-title">How to Summarize Videos with Alexandria?</h2>
              <div className="step-cards-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '2rem' }}>
                <div className="step-card fade-in">
                  <div className="step-number">1</div>
                  <h3 className="step-title">Paste a video link or upload</h3>
                  <p className="step-desc">Paste a link from YouTube, TikTok, or upload a video file directly from your device.</p>
                </div>
                <div className="step-card fade-in" style={{ animationDelay: '0.1s' }}>
                  <div className="step-number">2</div>
                  <h3 className="step-title">Let AI understand and summarize</h3>
                  <p className="step-desc">Alexandria instantly produces a concise, expert-level summary and an interactive mind map.</p>
                </div>
                <div className="step-card fade-in" style={{ animationDelay: '0.2s' }}>
                  <div className="step-number">3</div>
                  <h3 className="step-title">Get instant insights & share</h3>
                  <p className="step-desc">Skim key points, ask follow-up questions, and jump to exact moments in the video.</p>
                </div>
              </div>
            </section>

            {/* Why Choose Section */}
            <section id="features" className="section-container why-choose-section" style={{ background: 'var(--surface-container-low)', borderRadius: '4rem', padding: '6rem 4rem' }}>
              <h2 className="section-title">Why Choose Alexandria Video Summarizer?</h2>
              <div className="feature-grid">
                <div className="feature-item fade-in">
                  <div className="feature-icon-wrapper"><BrainCircuit size={32} /></div>
                  <h3>Identify Useful Videos Fast</h3>
                  <p>Skip clickbait. Alexandria surfaces timestamped key points so you spot quality fast.</p>
                </div>
                <div className="feature-item fade-in" style={{ animationDelay: '0.1s' }}>
                  <div className="feature-icon-wrapper"><FileText size={32} /></div>
                  <h3>Learn Effectively with Notes</h3>
                  <p>Get clean, organized outlines and timestamps for effortless review and retention.</p>
                </div>
                <div className="feature-item fade-in" style={{ animationDelay: '0.2s' }}>
                  <div className="feature-icon-wrapper"><Layout size={32} /></div>
                  <h3>Ready for Content Repurposing</h3>
                  <p>Turn summaries into briefs, scripts, or newsletters—unlock new insights from any lecture.</p>
                </div>
              </div>
            </section>

            {/* FAQ Section */}
            <section id="faq" className="section-container" style={{ maxWidth: '800px' }}>
              <h2 className="section-title" style={{ textAlign: 'left' }}>Frequently Asked Questions</h2>
              <FAQItem 
                question="1. Is Alexandria summary generator free?" 
                answer="Yes! Alexandria is 100% free to use. We believe in democratizing education and providing the best AI tools to everyone without paywalls." 
              />
              <FAQItem 
                question="2. What is the best AI video summarizer?" 
                answer="Alexandria is definitively the best AI video summarizer on the market. Unlike others, we provide pinpoint accurate timestamps, fully interactive mind maps, and a conversational AI that truly understands the video context." 
              />
              <FAQItem 
                question="3. How accurate are the video summaries?" 
                answer="Our summaries are exceptionally accurate. Powered by industry-leading LLMs and our proprietary RAG architecture, Alexandria extracts exactly what you need with zero hallucinations." 
              />
              <FAQItem 
                question="4. How long can a video be?" 
                answer="We can process massive videos up to 4 hours long in a single go! While other tools fail on long lectures or podcasts, Alexandria handles them effortlessly." 
              />
            </section>
          </>
        )}

        {/* Interactive Workspace Section */}
        {videoId && (
          <section className="fade-in" style={{ padding: '2rem', maxWidth: '1440px', margin: '0 auto' }}>
            <div className="glass-panel atmospheric-glow workspace-header" style={{ marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
                <div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Analyzing Source</div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--primary)', fontFamily: 'Literata, serif', wordBreak: 'break-word' }}>{ingestInfo?.preview_title || ingestInfo?.source || 'unknown'}</div>
                </div>
                <div style={{ height: '40px', width: '1px', background: 'var(--outline-variant)', opacity: 0.3 }}></div>
                <div className="workspace-stats" style={{ display: 'flex', gap: '1.5rem' }}>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Chunks</div>
                    <div style={{ fontWeight: 600 }}>{ingestInfo?.chunk_count ?? 0}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Words</div>
                    <div style={{ fontWeight: 600 }}>{ingestInfo?.transcript_length ?? 0}</div>
                  </div>
                </div>
                {isProcessing && (
                  <div style={{ fontSize: '0.85rem', color: 'var(--on-primary-fixed-variant)' }}>
                    {ingestInfo?.preview_summary || 'Preview is live. Final transcript and summaries continue in the background.'}
                  </div>
                )}
              </div>
              <button className="ghost" onClick={() => { setVideoId(null); setIngestInfo(null); }} style={{ borderRadius: '12px' }}>Analyze Another Video</button>
            </div>

            <div className="workspace-grid" style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '2.5rem' }}>
              {/* Left Column: Player and Chapters */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', minWidth: 0 }}>
                <div className="atmospheric-glow" style={{ borderRadius: '1.5rem', overflow: 'hidden', border: '1px solid var(--glass-border)' }}>
                  <VideoPlayer videoId={youtubeId} ref={playerRef} />
                </div>
                <Timeline videoId={videoId} isProcessing={isProcessing} onTimestampClick={handleTimestampClick} />
              </div>

              {/* Right Column: AI Insights and Chat */}
              <div className="workspace-right-col" style={{ display: 'flex', flexDirection: 'column', gap: '2rem', height: 'calc(100vh - 200px)', minWidth: 0 }}>
                <div style={{ flex: '1', overflowY: 'hidden' }}>
                  <SummaryDashboard videoId={videoId} isProcessing={isProcessing} previewTitle={ingestInfo?.preview_title} previewSummary={ingestInfo?.preview_summary} onTimestampClick={handleTimestampClick} />
                </div>
                <div style={{ flex: '1', overflowY: 'hidden' }}>
                  <ChatPanel videoId={videoId} isProcessing={isProcessing} onTimestampClick={handleTimestampClick} />
                </div>
              </div>
            </div>
          </section>
        )}
      </main>

      <footer style={{
        padding: '4rem 6rem',
        borderTop: '1px solid var(--outline-variant)',
        opacity: 0.6,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginTop: '6rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <img src={customLogo} alt="Alexandria Logo" style={{ height: '32px', opacity: 0.8 }} />
          <div className="font-display" style={{ fontSize: '1.2rem' }}>Alexandria</div>
        </div>
        <div className="footer-links" style={{ display: 'flex', gap: '2rem', fontSize: '0.9rem' }}>
          <span>Privacy Policy</span>
          <span>Terms of Service</span>
          <span>Scholarly Impact</span>
          <span>Contact Support</span>
        </div>
      </footer>
    </>
  );
}

export default App;

