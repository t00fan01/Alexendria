import React, { useState, useRef, useEffect } from 'react';
import { Send, MessageSquare, Clock } from 'lucide-react';
import { askQuestionStream } from '../api/client';

export default function ChatPanel({ videoId, onTimestampClick, isProcessing = false }) {
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isAsking, setIsAsking] = useState(false);
  const [sessionId, setSessionId] = useState(`session_${Date.now()}`);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatHistory]);

  useEffect(() => {
    setChatHistory([]);
    setQuestion('');
    setIsAsking(false);
    setSessionId(`session_${Date.now()}`);
  }, [videoId]);

  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim() || !videoId) return;

    const currentQuestion = question;
    setQuestion('');
    
    // Add user question to history
    const userMsgId = Date.now().toString();
    setChatHistory(prev => [...prev, { id: userMsgId, role: 'user', content: currentQuestion }]);
    
    setIsAsking(true);
    
    // Create placeholder for AI response
    const aiMsgId = (Date.now() + 1).toString();
    setChatHistory(prev => [...prev, { id: aiMsgId, role: 'ai', content: '', timestamps: [] }]);

    let accumulatedContent = '';

    await askQuestionStream(
      videoId,
      currentQuestion,
      sessionId,
      (chunk) => {
        accumulatedContent += chunk;
        setChatHistory(prev => 
          prev.map(msg => 
            msg.id === aiMsgId ? { ...msg, content: accumulatedContent } : msg
          )
        );
      },
      (timestamps) => {
        setChatHistory(prev => 
          prev.map(msg => 
            msg.id === aiMsgId ? { ...msg, timestamps: [...(msg.timestamps || []), ...timestamps] } : msg
          )
        );
        // Jump to first timestamp if any
        if (timestamps.length > 0 && onTimestampClick) {
          onTimestampClick(timestamps[0]);
        }
      },
      () => {
        setIsAsking(false);
      },
      (error) => {
        setIsAsking(false);
        setChatHistory(prev => 
          prev.map(msg => 
            msg.id === aiMsgId ? { ...msg, content: accumulatedContent + '\n\n**Error:** ' + error.message } : msg
          )
        );
      }
    );
  };

  const formatTime = (seconds) => {
    if (!seconds && seconds !== 0) return '';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const splitAnswer = (content) => {
    const lines = String(content || '').split('\n');
    const noteLines = [];
    const bodyLines = [];
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.toLowerCase().startsWith('note:') || trimmed.toLowerCase().startsWith('transcript warnings:')) {
        noteLines.push(trimmed);
      } else if (trimmed) {
        bodyLines.push(line);
      }
    }
    return { note: noteLines.join(' • '), body: bodyLines.join('\n').trim() };
  };

  return (
    <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <h2 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.25rem', marginBottom: '1rem', fontFamily: 'Literata, serif', color: 'var(--primary)' }}>
        <MessageSquare color="var(--primary)" /> Q&A Chat
      </h2>
      
      <div style={{ flex: 1, overflowY: 'auto', paddingRight: '0.5rem', display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1rem' }}>
        {chatHistory.length === 0 ? (
          <div style={{ margin: 'auto', color: 'var(--text-secondary)', textAlign: 'center' }}>
            <p>Ask a question about the video.</p>
            <p style={{ fontSize: '0.85rem', opacity: 0.7 }}>Try "What is the main topic?" or "Explain the concept at 2:00"</p>
          </div>
        ) : (
          chatHistory.map((msg) => {
            const isAi = msg.role === 'ai';
            const parsed = isAi ? splitAnswer(msg.content) : { note: '', body: msg.content };
            const isStreaming = isAi && isAsking && !msg.content;

            return (
            <div key={msg.id} className="fade-in" style={{
              alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
              background: msg.role === 'user' ? 'var(--primary)' : '#fff',
              color: msg.role === 'user' ? 'var(--on-primary)' : 'var(--on-surface)',
              padding: '1.25rem',
              borderRadius: '1.5rem',
              borderBottomRightRadius: msg.role === 'user' ? '0.25rem' : '1.5rem',
              borderBottomLeftRadius: msg.role === 'ai' ? '0.25rem' : '1.5rem',
              maxWidth: '85%',
              lineHeight: 1.6,
              boxShadow: '0 10px 20px -10px rgba(0,0,0,0.1)',
              border: msg.role === 'ai' ? '1px solid var(--outline-variant)' : 'none'
            }}>
              {isStreaming && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', minWidth: '280px' }}>
                  <div className="skeleton skeleton-line" style={{ width: '72%', height: '12px' }} />
                  <div className="skeleton skeleton-line" style={{ width: '92%', height: '12px' }} />
                  <div className="skeleton skeleton-line" style={{ width: '64%', height: '12px' }} />
                  <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                    Thinking...
                  </div>
                </div>
              )}
              {parsed.note && (
                <div style={{ marginBottom: '0.75rem', padding: '0.6rem 0.75rem', borderRadius: '10px', background: 'rgba(245, 158, 11, 0.12)', border: '1px solid rgba(245, 158, 11, 0.25)', color: '#fbbf24', fontSize: '0.85rem' }}>
                  {parsed.note}
                </div>
              )}
              <div style={{ whiteSpace: 'pre-wrap' }}>{parsed.body || msg.content}</div>
              
              {/* Render Timestamps as clickable badges */}
              {isAi && msg.timestamps && msg.timestamps.length > 0 && (
                <div style={{ marginTop: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {msg.timestamps.map((ts, idx) => (
                    <button 
                      key={idx}
                      onClick={() => onTimestampClick && onTimestampClick(ts)}
                      style={{
                        padding: '0.25rem 0.5rem',
                        fontSize: '0.75rem',
                        background: 'var(--primary-fixed)',
                        border: '1px solid var(--primary-fixed-dim)',
                        color: 'var(--on-primary-fixed-variant)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.25rem',
                        boxShadow: 'none'
                      }}
                    >
                      <Clock size={12} /> {formatTime(ts)}
                    </button>
                  ))}
                </div>
              )}
            </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleAsk} style={{ display: 'flex', gap: '0.5rem' }}>
        <input 
          type="text" 
          value={question} 
          onChange={(e) => setQuestion(e.target.value)} 
          placeholder={isProcessing ? 'Ask now; answers improve as transcript finishes...' : 'Ask a question...'} 
          disabled={!videoId || isAsking}
          style={{ flex: 1, borderRadius: '24px', paddingLeft: '1.25rem', background: 'var(--surface-container-lowest)' }}
        />
        <button 
          type="submit" 
          disabled={!videoId || isAsking || !question.trim()} 
          style={{ borderRadius: '50%', width: '48px', height: '48px', padding: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
        >
          <Send size={18} style={{ marginLeft: '2px' }} />
        </button>
      </form>
    </div>
  );
}
