import React from 'react';
import customLogo from '../assets/logo.png';

export default function Navbar() {
  return (
    <nav style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      height: '80px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 4rem',
      backdropFilter: 'blur(12px)',
      background: 'rgba(251, 249, 246, 0.8)',
      borderBottom: '1px solid rgba(0,0,0,0.05)',
      zIndex: 100
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <img src={customLogo} alt="Alexandria Logo" style={{ height: '42px', width: 'auto', objectFit: 'contain' }} />
        <span className="font-display" style={{ fontSize: '1.6rem', color: 'var(--primary)', fontWeight: 800, letterSpacing: '-0.03em' }}>Alexandria</span>
      </div>

      <div className="nav-links" style={{ display: 'flex', gap: '2.5rem', alignItems: 'center' }}>
        <a href="#dashboard" className="nav-hover" style={{ textDecoration: 'none', color: 'var(--on-surface-variant)', fontSize: '0.95rem', fontWeight: 500 }}>Dashboard</a>
        <a href="#how-it-works" className="nav-hover" style={{ textDecoration: 'none', color: 'var(--on-surface-variant)', fontSize: '0.95rem', fontWeight: 500 }}>How it Works</a>
        <a href="#features" className="nav-hover" style={{ textDecoration: 'none', color: 'var(--on-surface-variant)', fontSize: '0.95rem', fontWeight: 500 }}>Features</a>
        <a href="#faq" className="nav-hover" style={{ textDecoration: 'none', color: 'var(--on-surface-variant)', fontSize: '0.95rem', fontWeight: 500 }}>FAQ</a>
      </div>

      <div className="nav-cta-group" style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
        <button className="ghost" style={{ border: 'none', background: 'transparent' }}>Log In</button>
        <button className="nav-hover" style={{
          background: 'var(--primary)',
          color: '#fff',
          padding: '0.6rem 1.5rem',
          borderRadius: '9999px',
          boxShadow: '0 4px 12px rgba(6, 27, 14, 0.2)'
        }}>Start Building</button>
      </div>
    </nav>
  );
}
