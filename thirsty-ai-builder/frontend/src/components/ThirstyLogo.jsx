// Placeholder ThirstyLogo. Replace this SVG with the official Thirsty's
// Projects LLC mark when ready; the rest of the UI does not depend on
// the visual content of this component.
import React from "react";

export default function ThirstyLogo({ className = "w-8 h-8" }) {
  return (
    <svg
      className={className}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="ThirstyAI Builder logo"
    >
      <defs>
        <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#e08a3f" />
          <stop offset="100%" stopColor="#4a5f8e" />
        </linearGradient>
      </defs>
      <path
        d="M32 4 L58 18 V46 L32 60 L6 46 V18 Z"
        fill="url(#g)"
        stroke="rgba(255,255,255,0.25)"
        strokeWidth="1.2"
      />
      <path
        d="M22 22 H42 M32 22 V44 M22 44 H42"
        stroke="white"
        strokeWidth="2.4"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}
