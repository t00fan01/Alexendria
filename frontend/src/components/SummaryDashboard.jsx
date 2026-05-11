import React, { useEffect, useRef, useState } from 'react';
import { AlignLeft, List, History, Loader2, PlayCircle, Star } from 'lucide-react';
import { getAnalysis } from '../api/client';
import PdfExport from './PdfExport';

export default function SummaryDashboard({ videoId, onTimestampClick, isProcessing = false, previewTitle = '', previewSummary = '' }) {
  const [overall, setOverall] = useState(null);
  const [topics, setTopics] = useState(null);
  const [recent, setRecent] = useState(null);
  const [quality, setQuality] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const requestSeq = useRef(0);

  useEffect(() => {
    if (!videoId) return;

    const requestId = ++requestSeq.current;
    let stopped = false;
    setOverall(previewSummary || null);
    setTopics(null);
    setRecent(previewSummary || null);
    setQuality(null);
    setError('');
    setLoading(!previewSummary);

    const fetchAnalysis = async () => {
      try {
        const data = await getAnalysis(videoId);
        if (stopped || requestSeq.current !== requestId) return 'stale';
        
        const summaryReady = data.summary && !data.summary.startsWith('Summary is not available yet');
        if (summaryReady) {
          setOverall(data.summary);
        } else if (previewSummary) {
          setOverall(previewSummary);
        }
        if (Array.isArray(data.topics)) setTopics(data.topics);
        if (data.recent_summary && data.recent_summary !== 'No content available') setRecent(data.recent_summary);
        if (data.quality) setQuality(data.quality);
        setLoading(data.status !== 'success');
        return data.status;
      } catch (err) {
        if (stopped || requestSeq.current !== requestId) return 'stale';
        if (!previewSummary) {
          setError(err.message || 'Failed to fetch summaries');
        }
        console.error("Failed to fetch summaries", err);
        setLoading(false);
        return 'error';
      }
    };

    fetchAnalysis();
    const interval = isProcessing
      ? window.setInterval(() => {
          void fetchAnalysis();
        }, 1500)
      : null;

    return () => {
      stopped = true;
      if (interval) window.clearInterval(interval);
      requestSeq.current += 1;
    };
  }, [videoId, isProcessing, previewSummary]);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };


  const hasVisibleContent = Boolean(overall || (topics && topics.length > 0) || recent || previewSummary);

  if (loading && !hasVisibleContent) {
    return (
      <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
          <div className="skeleton skeleton-line" style={{ width: '38%', height: '18px' }} />
          <Loader2 className="animate-spin" size={20} color="var(--primary)" />
        </div>
        <div className="skeleton-card" style={{ padding: '1rem' }}>
          <div className="skeleton skeleton-line" style={{ width: '24%', marginBottom: '0.75rem' }} />
          <div className="skeleton skeleton-line" style={{ width: '92%', marginBottom: '0.6rem' }} />
          <div className="skeleton skeleton-line" style={{ width: '86%', marginBottom: '0.6rem' }} />
          <div className="skeleton skeleton-line" style={{ width: '70%' }} />
        </div>
        <div className="skeleton-card" style={{ padding: '1rem' }}>
          <div className="skeleton skeleton-line" style={{ width: '30%', marginBottom: '0.9rem' }} />
          <div className="skeleton skeleton-line" style={{ width: '88%', marginBottom: '0.6rem' }} />
          <div className="skeleton skeleton-line" style={{ width: '78%', marginBottom: '0.6rem' }} />
          <div className="skeleton skeleton-line" style={{ width: '64%' }} />
        </div>
        <p style={{ color: 'var(--text-secondary)', fontWeight: 500, marginTop: 'auto', textAlign: 'center' }}>
          Building summaries in the background...
        </p>
      </div>
    );
  }

  if (error && !hasVisibleContent) {
    return (
      <div className="glass-panel" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '1rem' }}>
        <AlignLeft size={32} color="var(--danger)" />
        <p style={{ color: 'var(--danger)', textAlign: 'center' }}>{error}</p>
      </div>
    );
  }

  if (!videoId) {
    return (
      <div className="glass-panel" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '1rem', opacity: 0.6 }}>
        <AlignLeft size={32} color="var(--outline)" />
        <p style={{ color: 'var(--text-secondary)' }}>Summary will appear after ingest</p>
      </div>
    );
  }

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', gap: '2rem', height: '100%', overflowY: 'auto' }}>
      {isProcessing && (previewTitle || previewSummary) && (
        <section className="fade-in" style={{
          border: '1px solid var(--outline-variant)',
          background: 'rgba(255,255,255,0.76)',
          padding: '1rem 1.1rem',
          borderRadius: '1rem'
        }}>
          <div style={{ fontSize: '0.78rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
            Instant Preview
          </div>
          <div style={{ fontWeight: 700, color: 'var(--primary)', marginBottom: '0.4rem' }}>
            {previewTitle || 'Processing video'}
          </div>
          <p style={{ margin: 0, color: 'var(--text-primary)', lineHeight: 1.7 }}>
            {previewSummary || 'Final transcript processing is running in the background.'}
          </p>
        </section>
      )}

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          <Loader2 className="animate-spin" size={16} />
          Refreshing final transcript analysis...
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ margin: 0, fontSize: '1.5rem', color: 'var(--primary)', fontFamily: 'Literata, serif' }}>AI Insights</h2>
        <PdfExport 
          title={previewTitle || "Lecture Notes"} 
          overall={overall} 
          topics={topics} 
          recent={recent} 
        />
      </div>

      {quality && (
        <section className="fade-in" style={{ 
          border: '1px solid var(--glass-border)', 
          background: 'var(--surface-container-low)', 
          padding: '1.25rem', 
          borderRadius: '1rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.5rem'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Analysis Quality</h3>
            <span style={{
              padding: '0.2rem 0.75rem',
              borderRadius: '999px',
              fontSize: '0.75rem',
              fontWeight: 700,
              background: 'var(--primary)',
              color: '#fff',
              whiteSpace: 'nowrap'
            }}>
              {quality.score || 'A+'}
            </span>
          </div>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
             {quality.warnings?.map((w, i) => (
               <span key={i} style={{ fontSize: '0.75rem', color: 'var(--on-primary-fixed-variant)', background: 'var(--primary-fixed)', padding: '0.1rem 0.5rem', borderRadius: '4px' }}>
                 {w}
               </span>
             ))}
          </div>
        </section>
      )}
      
      {/* Overall Summary */}
      <section className="fade-in">
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.25rem', color: 'var(--primary)', fontFamily: 'Literata, serif', marginBottom: '1rem' }}>
          <Star size={20} fill="var(--primary)" /> Overall Insight
        </h3>
        <p style={{ 
          color: 'var(--text-primary)', 
          lineHeight: 1.8, 
          background: '#fff', 
          padding: '1.5rem', 
          borderRadius: '1rem',
          border: '1px solid var(--outline-variant)',
          boxShadow: '0 4px 12px rgba(0,0,0,0.02)'
        }}>
          {overall || "No overall summary available yet."}
        </p>
      </section>

      {/* Topic Summaries */}
      <section className="fade-in" style={{ animationDelay: '0.1s' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.25rem', color: 'var(--primary)', fontFamily: 'Literata, serif', marginBottom: '1rem' }}>
          <List size={20} /> Key Concepts
        </h3>
        {topics && topics.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {topics.map((t, i) => (
              <div 
                key={i} 
                style={{ 
                  background: '#fff', 
                  border: '1px solid var(--outline-variant)',
                  padding: '1.25rem', 
                  borderRadius: '1rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.01)'
                }}
                onClick={() => onTimestampClick && onTimestampClick(t.timestamp)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateX(4px)';
                  e.currentTarget.style.borderColor = 'var(--primary)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateX(0)';
                  e.currentTarget.style.borderColor = 'var(--outline-variant)';
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <h4 style={{ margin: 0, fontSize: '1rem', color: 'var(--primary)', fontWeight: 600 }}>{t.topic}</h4>
                  <span style={{ 
                    display: 'flex', alignItems: 'center', gap: '0.25rem', 
                    fontSize: '0.75rem', fontWeight: 600, color: 'var(--primary)',
                    background: 'var(--primary-fixed)',
                    padding: '0.2rem 0.6rem', borderRadius: '999px'
                  }}>
                    <PlayCircle size={12} /> {formatTime(t.timestamp)}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{t.summary}</p>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontStyle: 'italic' }}>Topic summaries will be generated as analysis progresses.</p>
        )}
      </section>

      {/* Last N Minutes */}
      <section className="fade-in" style={{ animationDelay: '0.2s' }}>
        <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.25rem', color: 'var(--primary)', fontFamily: 'Literata, serif', marginBottom: '1rem' }}>
          <History size={20} /> Recent Context
        </h3>
        <div style={{ 
          color: 'var(--text-primary)', 
          lineHeight: 1.7, 
          background: 'var(--surface-container-low)', 
          padding: '1.25rem', 
          borderRadius: '1rem',
          border: '1px solid var(--glass-border)'
        }}>
          {recent || "Awaiting more lecture data for recent summary..."}
        </div>
      </section>
    </div>
  );
}
