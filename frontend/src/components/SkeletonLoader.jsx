import React from 'react';

export default function SkeletonLoader({ count = 3, type = 'paragraph' }) {
  if (type === 'paragraph') {
    return (
      <div className="space-y-4">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="animate-pulse">
            <div className="h-4 bg-gray-300 rounded mb-2"></div>
            <div className="h-4 bg-gray-200 rounded mb-2"></div>
            <div className="h-4 bg-gray-300 rounded w-5/6"></div>
          </div>
        ))}
      </div>
    );
  }

  if (type === 'summary') {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="bg-gray-100 rounded-lg p-4 space-y-3">
          <div className="h-6 bg-gray-300 rounded w-1/3"></div>
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-300 rounded w-5/6"></div>
          </div>
        </div>
        <div className="bg-gray-100 rounded-lg p-4 space-y-3">
          <div className="h-6 bg-gray-300 rounded w-1/4"></div>
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-300 rounded w-4/5"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-pulse space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="h-12 bg-gray-300 rounded"></div>
      ))}
    </div>
  );
}
