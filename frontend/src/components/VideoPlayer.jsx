import React, { useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import YouTube from 'react-youtube';

const VideoPlayer = forwardRef(({ videoId }, ref) => {
  const playerRef = useRef(null);

  useImperativeHandle(ref, () => ({
    seekTo: (seconds) => {
      if (playerRef.current) {
        playerRef.current.internalPlayer.seekTo(seconds, true);
        playerRef.current.internalPlayer.playVideo();
      }
    }
  }));

  const onReady = (event) => {
    // Access to player in all event handlers via event.target
    playerRef.current = { internalPlayer: event.target };
  };

  const opts = {
    height: '100%',
    width: '100%',
    playerVars: {
      autoplay: 0,
    },
  };

  if (!videoId) {
    return (
      <div className="glass-panel video-placeholder" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '400px', aspectRatio: '16/9' }}>
        <p style={{ color: 'var(--text-secondary)' }}>Ingest a video to get started</p>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: 'auto', aspectRatio: '16/9', display: 'flex', background: '#000' }}>
      <YouTube 
        videoId={videoId} 
        opts={opts} 
        onReady={onReady} 
        style={{ width: '100%', height: '100%', display: 'block' }}
      />
    </div>
  );
});

export default VideoPlayer;
