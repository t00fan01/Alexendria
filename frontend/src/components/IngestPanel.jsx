import React, { useState } from 'react';
import { Video, ArrowRight, Loader2, CheckCircle, AlertCircle, Upload, Copy, Plus } from 'lucide-react';
import { ingestVideo, ingestFile, getIngestStatus } from '../api/client';
import SkeletonLoader from './SkeletonLoader';

export default function IngestPanel({ onIngestSuccess }) {
  const [url, setUrl] = useState('');
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [result, setResult] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');

  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [startTime, setStartTime] = useState(null);

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const waitForJobCompletion = async (jobId) => {
    const maxAttempts = 180;
    setStartTime(Date.now());
    
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      const job = await getIngestStatus(jobId);
      
      // Extract progress info
      const step = job.step || 0;
      const stepName = job.step_name || `Processing... (${attempt + 1}/${maxAttempts})`;
      const progressPercent = job.progress || Math.min(15 + (attempt * 0.5), 95);
      
      setCurrentStep(stepName);
      setProgress(progressPercent);
      
      // Calculate and show time estimate
      if (startTime && attempt > 3) {
        const elapsed = (Date.now() - startTime) / 1000;
        const estimatedPercent = Math.max(progressPercent, 15);
        const estimatedTotal = (elapsed / (estimatedPercent / 100));
        const remaining = Math.max(0, estimatedTotal - elapsed);
        
        if (remaining > 5) {
          setStatusMessage(`${stepName} - Est. ${Math.ceil(remaining)}s remaining...`);
        } else {
          setStatusMessage(stepName);
        }
      } else {
        setStatusMessage(stepName);
      }
      
      if (job.status === 'completed' || job.status === 'failed') {
        return job;
      }
      
      await sleep(500); // Poll faster for better UX
    }
    throw new Error('Ingest is taking longer than expected. Please check again in a moment.');
  };

  const startBackgroundMonitoring = async (jobId, ytId) => {
    try {
      const jobResult = await waitForJobCompletion(jobId);
      if (jobResult.status === 'failed') {
        throw new Error(jobResult.message || 'Ingest failed');
      }

      const finalInfo = {
        ...(jobResult.result || {}),
        status: 'completed',
        job_id: jobResult.job_id,
        video_id: jobResult.video_id,
      };

      setSuccess(true);
      setResult(finalInfo);
      setStatusMessage('Transcript ready. Final summary is refreshing now...');
      onIngestSuccess(jobResult.video_id, ytId, finalInfo);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleIngest = async (e) => {
    if (e) e.preventDefault();
    if (!url && !file) return;
    
    setLoading(true);
    setError('');
    setSuccess(false);
    setStatusMessage('');

    let ytId = null;
    if (url) {
      try {
        const urlObj = new URL(url);
        if (urlObj.hostname.includes('youtube.com')) {
          ytId = urlObj.searchParams.get('v');
        } else if (urlObj.hostname === 'youtu.be') {
          ytId = urlObj.pathname.slice(1);
        }
      } catch (e) {
        console.warn('Could not parse YouTube ID');
      }
    }
    
    try {
      const ingestResult = url 
        ? await ingestVideo(url)
        : await ingestFile(file, title || file.name);
      const isPreviewJob = ingestResult.status === 'processing' && Boolean(ingestResult.job_id);

      if (isPreviewJob) {
        setSuccess(true);
        const previewInfo = {
          ...ingestResult,
          status: 'processing',
          preview: true,
        };
        setResult(previewInfo);
        setStatusMessage(`Preview ready in seconds. Final processing continues in the background... job ${ingestResult.job_id.slice(0, 8)}`);
        onIngestSuccess(ingestResult.video_id, ytId, previewInfo);
        void startBackgroundMonitoring(ingestResult.job_id, ytId);
        return;
      }

      setSuccess(true);
      setResult(ingestResult);
      
      onIngestSuccess(ingestResult.video_id, ytId, ingestResult);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setUrl(''); // Clear URL if file is selected
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Search Bar Style Input */}
      <div className="glass-panel" style={{ 
        padding: '0.4rem', 
        borderRadius: '999px', 
        display: 'flex', 
        alignItems: 'center',
        gap: '0.5rem',
        background: '#ffffff',
        boxShadow: '0 20px 40px -10px rgba(0,0,0,0.05)',
        border: '1px solid rgba(0, 0, 0, 0.05)'
      }}>
        <div style={{ padding: '0 1.25rem', color: '#9ca3af' }}>
          <Video size={24} />
        </div>
        <input 
          type="text" 
          value={url} 
          onChange={(e) => {setUrl(e.target.value); setFile(null);}} 
          placeholder="Paste a video link or upload a video" 
          disabled={loading}
          style={{ 
            flex: 1, 
            border: 'none', 
            background: 'transparent', 
            color: '#1e293b',
            fontSize: '1.25rem',
            boxShadow: 'none',
            padding: '1rem 0',
            fontWeight: 500
          }}
        />
        <button 
          onClick={handleIngest}
          disabled={loading || (!url && !file)}
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            background: '#10b981',
            color: '#fff',
            width: '80px',
            height: '60px',
            borderRadius: '999px',
            padding: 0
          }}
        >
          {loading ? <Loader2 className="animate-spin" size={24} /> : <ArrowRight size={28} />}
        </button>
      </div>

      {/* Sub-buttons Row */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginTop: '0.5rem' }}>
         <button style={{ background: '#ffffff', color: '#4b5563', border: '1px solid rgba(0,0,0,0.05)', borderRadius: '12px', padding: '0.8rem 1.5rem', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem', boxShadow: '0 4px 12px rgba(0,0,0,0.02)' }} onClick={() => document.getElementById('file-input').click()}>
            <Upload size={16} /> Upload
         </button>
         <button style={{ background: '#ffffff', color: '#4b5563', border: '1px solid rgba(0,0,0,0.05)', borderRadius: '12px', padding: '0.8rem 1.5rem', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem', boxShadow: '0 4px 12px rgba(0,0,0,0.02)' }}>
            <Copy size={16} /> YouTube Video Link
         </button>
         <button style={{ background: '#ffffff', color: '#4b5563', border: '1px solid rgba(0,0,0,0.05)', borderRadius: '12px', padding: '0.8rem 1.5rem', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem', boxShadow: '0 4px 12px rgba(0,0,0,0.02)' }}>
            <Plus size={16} /> Other Links
         </button>
      </div>

      <input 
        id="file-input"
        type="file" 
        hidden 
        onChange={handleFileChange}
        accept="audio/*,video/*,application/pdf"
      />

      {file && !loading && (
        <div className="fade-in glass-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--primary-fixed)' }}>
           <span style={{ fontWeight: 600 }}>Selected: {file.name}</span>
           <button onClick={handleIngest} style={{ background: 'var(--primary)', color: '#fff' }}>Process File</button>
        </div>
      )}

      {error && (
        <div className="fade-in glass-panel" style={{ color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'var(--error-container)' }}>
          <AlertCircle size={18} /> {error}
        </div>
      )}

      {statusMessage && !error && loading && (
        <div className="fade-in glass-panel" style={{ 
          display: 'flex', 
          flexDirection: 'column',
          gap: '0.75rem',
          background: 'var(--surface-container-low)',
          padding: '1.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Loader2 size={20} className="animate-spin" style={{ color: '#16e059' }} /> 
            <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
              {statusMessage}
            </span>
          </div>
          
          {/* Progress bar */}
          <div style={{
            width: '100%',
            height: '8px',
            background: '#333',
            borderRadius: '4px',
            overflow: 'hidden',
            marginTop: '0.5rem'
          }}>
            <div style={{
              height: '100%',
              width: `${progress}%`,
              background: 'linear-gradient(90deg, #16e059, #6ef585)',
              borderRadius: '4px',
              transition: 'width 0.3s ease',
              boxShadow: '0 0 10px rgba(22, 224, 89, 0.5)'
            }} />
          </div>
          
          {/* Progress percentage */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: '0.85rem',
            color: '#aaa',
            marginTop: '0.25rem'
          }}>
            <span>{currentStep}</span>
            <span>{Math.round(progress)}%</span>
          </div>
        </div>
      )}

      {loading && !statusMessage && (
        <div className="fade-in glass-panel" style={{ 
          minHeight: '150px',
          display: 'flex',
          flexDirection: 'column',
          gap: '1rem',
          background: 'var(--surface-container-low)',
          padding: '1.5rem'
        }}>
          <SkeletonLoader count={2} type="paragraph" />
        </div>
      )}
    </div>
  );
}
