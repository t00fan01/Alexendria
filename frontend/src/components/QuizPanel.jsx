import React, { useState, useEffect } from 'react';
import { HelpCircle, CheckCircle2, XCircle, RefreshCw, Trophy, ChevronRight, PlayCircle } from 'lucide-react';
import { getQuiz } from '../api/client';

export default function QuizPanel({ videoId, isProcessing, onTimestampClick }) {
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null);
  const [showExplanation, setShowExplanation] = useState(false);
  const [score, setScore] = useState(0);
  const [isFinished, setIsFinished] = useState(false);

  const fetchQuiz = async () => {
    if (!videoId) return;
    setLoading(true);
    setError(null);
    setCurrentIndex(0);
    setSelectedOption(null);
    setShowExplanation(false);
    setScore(0);
    setIsFinished(false);
    try {
      const data = await getQuiz(videoId);
      if (data.status === 'success' && data.questions.length > 0) {
        setQuestions(data.questions);
      } else {
        setError(data.message || 'No questions generated yet.');
      }
    } catch (err) {
      setError(err.message || 'Failed to load quiz');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (videoId && !isProcessing) {
      fetchQuiz();
    }
  }, [videoId, isProcessing]);

  const handleOptionSelect = (option) => {
    if (selectedOption !== null) return;
    setSelectedOption(option);
    setShowExplanation(true);
    if (option === questions[currentIndex].correct) {
      setScore(s => s + 1);
    }
  };

  const handleNext = () => {
    if (currentIndex < questions.length - 1) {
      setCurrentIndex(c => c + 1);
      setSelectedOption(null);
      setShowExplanation(false);
    } else {
      setIsFinished(true);
    }
  };

  const formatTime = (seconds) => {
    if (seconds === null || seconds === undefined) return null;
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '300px' }}>
        <RefreshCw className="animate-spin" size={32} color="var(--primary)" />
        <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Generating your personalized quiz...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '300px', textAlign: 'center', padding: '2rem' }}>
        <HelpCircle size={48} color="var(--outline)" style={{ marginBottom: '1rem' }} />
        <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>Quiz Not Ready</h3>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>{error}</p>
        <button className="primary" onClick={fetchQuiz} disabled={isProcessing}>
          <RefreshCw size={16} /> Try Again
        </button>
      </div>
    );
  }

  if (!videoId || questions.length === 0) {
    return (
      <div className="glass-panel" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '1rem', opacity: 0.6, minHeight: '300px' }}>
        <HelpCircle size={32} color="var(--outline)" />
        <p style={{ color: 'var(--text-secondary)' }}>Quiz will appear after analysis is complete</p>
      </div>
    );
  }

  if (isFinished) {
    const percentage = Math.round((score / questions.length) * 100);
    return (
      <div className="glass-panel fade-in" style={{ textAlign: 'center', padding: '3rem 2rem' }}>
        <Trophy size={64} color="var(--primary)" style={{ marginBottom: '1rem' }} />
        <h2 style={{ fontSize: '2rem', marginBottom: '0.5rem', color: 'var(--primary)' }}>Quiz Complete!</h2>
        <p style={{ fontSize: '1.2rem', color: 'var(--text-secondary)', marginBottom: '2rem' }}>
          You scored <strong>{score}</strong> out of <strong>{questions.length}</strong> ({percentage}%)
        </p>
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <button className="primary" onClick={fetchQuiz}>Restart Quiz</button>
          <button className="ghost" onClick={() => setIsFinished(false)}>Review Questions</button>
        </div>
      </div>
    );
  }

  const currentQ = questions[currentIndex];

  return (
    <div className="glass-panel fade-in" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <HelpCircle size={24} color="var(--primary)" />
          <h3 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--primary)', fontFamily: 'Literata, serif' }}>Knowledge Check</h3>
        </div>
        <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
          Question {currentIndex + 1} of {questions.length}
        </div>
      </div>

      <div style={{ background: 'var(--surface-container-low)', padding: '1.5rem', borderRadius: '1rem', border: '1px solid var(--outline-variant)', marginBottom: '1.5rem' }}>
        <h4 style={{ margin: 0, fontSize: '1.1rem', lineHeight: 1.5, color: 'var(--text-primary)' }}>{currentQ.question}</h4>
        {currentQ.timestamp !== null && (
          <button 
            className="ghost" 
            style={{ marginTop: '0.75rem', padding: '0.25rem 0.5rem', fontSize: '0.75rem', borderRadius: '4px' }}
            onClick={() => onTimestampClick && onTimestampClick(currentQ.timestamp)}
          >
            <PlayCircle size={12} /> Jump to Context ({formatTime(currentQ.timestamp)})
          </button>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
        {Object.entries(currentQ.options).map(([key, value]) => {
          const isSelected = selectedOption === key;
          const isCorrect = key === currentQ.correct;
          const showResult = showExplanation;
          
          let borderColor = 'var(--outline-variant)';
          let bgColor = '#fff';
          let textColor = 'var(--text-primary)';

          if (showResult) {
            if (isCorrect) {
              borderColor = '#10b981';
              bgColor = '#f0fdf4';
            } else if (isSelected) {
              borderColor = '#ef4444';
              bgColor = '#fef2f2';
            }
          } else if (isSelected) {
            borderColor = 'var(--primary)';
            bgColor = 'var(--primary-fixed)';
          }

          return (
            <button
              key={key}
              onClick={() => handleOptionSelect(key)}
              disabled={showExplanation}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '1rem',
                textAlign: 'left',
                padding: '1rem',
                borderRadius: '0.75rem',
                border: `2px solid ${borderColor}`,
                background: bgColor,
                color: textColor,
                transition: 'all 0.2s ease',
                cursor: showExplanation ? 'default' : 'pointer'
              }}
            >
              <span style={{ 
                width: '24px', height: '24px', display: 'flex', alignItems: 'center', justifyContent: 'center', 
                borderRadius: '50%', background: isSelected ? 'var(--primary)' : 'var(--outline-variant)', 
                color: '#fff', fontSize: '0.8rem', fontWeight: 700 
              }}>
                {key}
              </span>
              <span style={{ flex: 1 }}>{value}</span>
              {showResult && isCorrect && <CheckCircle2 size={20} color="#10b981" />}
              {showResult && isSelected && !isCorrect && <XCircle size={20} color="#ef4444" />}
            </button>
          );
        })}
      </div>

      {showExplanation && (
        <div className="fade-in" style={{ 
          background: 'var(--primary-fixed)', 
          padding: '1.25rem', 
          borderRadius: '1rem', 
          border: '1px solid var(--primary-fixed-dim)',
          marginBottom: '1.5rem'
        }}>
          <div style={{ fontWeight: 700, color: 'var(--primary)', marginBottom: '0.5rem', fontSize: '0.9rem', textTransform: 'uppercase' }}>
            Explanation
          </div>
          <p style={{ margin: 0, fontSize: '0.95rem', color: 'var(--text-primary)', lineHeight: 1.6 }}>{currentQ.explanation}</p>
          <button 
            className="primary" 
            style={{ marginTop: '1.25rem', width: '100%' }}
            onClick={handleNext}
          >
            {currentIndex < questions.length - 1 ? 'Next Question' : 'Finish Quiz'} <ChevronRight size={18} />
          </button>
        </div>
      )}
    </div>
  );
}
