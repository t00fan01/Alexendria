import React, { useEffect, useRef, useState } from 'react';
import { Clock, Loader2, Sparkles, BookOpen, Layers } from 'lucide-react';
import { getAnalysis } from '../api/client';

const LOADING_MESSAGES = [
  { icon: Sparkles, text: 'Extracting key concepts...' },
  { icon: Layers,   text: 'Mapping video chapters...' },
  { icon: BookOpen, text: 'Building your timeline...' },
  { icon: Sparkles, text: 'Analysing transcript segments...' },
  { icon: Layers,   text: 'Identifying key moments...' },
  { icon: BookOpen, text: 'Structuring chapter labels...' },
];

function SkeletonChapters() {
  const widths = [48, 64, 42, 72, 55, 38];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '0.75rem' }}>
      {widths.map((w, i) => (
        <div key={i} className="skeleton-card" style={{ padding: '0.85rem', minHeight: '72px' }}>
          <div className="skeleton skeleton-line" style={{ width: `${w}%`, marginBottom: '0.6rem' }} />
          <div className="skeleton skeleton-line" style={{ width: `${w + 20}%` }} />
        </div>
      ))}
    </div>
  );
}

export default function Timeline({ videoId, onTimestampClick, isProcessing = false }) {
  const [timestamps, setTimestamps] = useState([]);
  const [loading, setLoading]       = useState(false);
  const [msgIdx, setMsgIdx]         = useState(0);
  const requestSeq = useRef(0);

  // Rotate the loading message every 1.8 s while we have no chapters yet
  useEffect(() => {
    if (timestamps.length > 0) return;
    const id = setInterval(() => setMsgIdx(i => (i + 1) % LOADING_MESSAGES.length), 1800);
    return () => clearInterval(id);
  }, [timestamps.length]);

  useEffect(() => {
    if (!videoId) return;

    const requestId = ++requestSeq.current;
    let stopped = false;
    setTimestamps([]);

    const fetchTimeline = async () => {
      setLoading(true);
      try {
        const data = await getAnalysis(videoId);
        if (stopped || requestSeq.current !== requestId) return;
        if (data && data.timestamps) {
          setTimestamps(data.timestamps);
        }
      } catch (err) {
        if (stopped || requestSeq.current !== requestId) return;
        console.error('Failed to fetch timeline', err);
      } finally {
        if (!stopped && requestSeq.current === requestId) {
          setLoading(false);
        }
      }
    };

    fetchTimeline();
    const interval = isProcessing
      ? window.setInterval(() => { void fetchTimeline(); }, 1500)
      : null;

    return () => {
      stopped = true;
      if (interval) window.clearInterval(interval);
      requestSeq.current += 1;
    };
  }, [videoId, isProcessing]);

  if (!videoId) return null;

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  /* ── Loading / building state ── */
  if (timestamps.length === 0) {
    const { icon: MsgIcon, text: msgText } = LOADING_MESSAGES[msgIdx];
    return (
      <div className="glass-panel" style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3 style={{
            display: 'flex', alignItems: 'center', gap: '0.5rem',
            fontSize: '1.1rem', margin: 0,
            fontFamily: 'Literata, serif', color: 'var(--primary)'
          }}>
            <Clock size={18} color="var(--primary)" /> Video Chapters
          </h3>
          {/* animated pill badge */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '0.5rem',
            background: 'var(--primary-fixed)', color: 'var(--on-primary-fixed-variant)',
            borderRadius: '999px', padding: '0.3rem 0.85rem',
            fontSize: '0.78rem', fontWeight: 600, border: '1px solid var(--primary-fixed-dim)',
            animation: 'fadeIn 0.4s ease',
          }}>
            <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} />
            <span key={msgIdx} style={{ animation: 'fadeIn 0.35s ease' }}>{msgText}</span>
          </div>
        </div>

        {/* Progress bar */}
        <div style={{
          height: '3px', borderRadius: '999px',
          background: 'var(--surface-container-highest)',
          overflow: 'hidden',
        }}>
          <div style={{
            height: '100%', width: '40%',
            background: 'linear-gradient(90deg, var(--primary-container), var(--inverse-primary))',
            borderRadius: '999px',
            animation: 'chapterProgress 2s ease-in-out infinite alternate',
          }} />
        </div>

        {/* Skeleton cards */}
        <SkeletonChapters />
      </div>
    );
  }

  /* ── Chapters ready ── */
  return (
    <div className="glass-panel" style={{ marginTop: '1.5rem' }}>
      <h3 style={{
        display: 'flex', alignItems: 'center', gap: '0.5rem',
        fontSize: '1.1rem', marginBottom: '1rem',
        fontFamily: 'Literata, serif', color: 'var(--primary)'
      }}>
        <Clock size={18} color="var(--primary)" /> Video Chapters
      </h3>

      <div style={{ display: 'flex', gap: '0.75rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
        {timestamps.map((ts, idx) => (
          <button
            key={idx}
            onClick={() => onTimestampClick && onTimestampClick(ts.time)}
            style={{
              flexShrink: 0,
              background: 'var(--surface-container)',
              border: '1px solid var(--glass-border)',
              color: 'var(--text-primary)',
              display: 'flex', flexDirection: 'column', alignItems: 'flex-start',
              padding: '0.5rem 1rem', minWidth: '120px',
            }}
          >
            <span style={{ fontSize: '0.8rem', color: 'var(--on-primary-fixed-variant)', marginBottom: '0.25rem', fontWeight: 600 }}>
              {formatTime(ts.time)}
            </span>
            <span style={{
              fontSize: '0.9rem', textAlign: 'left',
              display: '-webkit-box', WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical', overflow: 'hidden',
            }}>
              {ts.label}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
