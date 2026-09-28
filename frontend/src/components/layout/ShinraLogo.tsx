import React from 'react';

interface ShinraLogoProps {
  size?: number;
  className?: string;
  variant?: 'badge' | 'minimal';
}

export const ShinraLogo: React.FC<ShinraLogoProps> = ({ 
  size = 24, 
  className = '',
  variant = 'badge' 
}) => {
  return (
    <div
      className={`relative inline-flex items-center justify-center flex-shrink-0 select-none ${className}`}
      style={{ width: size, height: size }}
      title="Shinra Voice Assistant"
    >
      <svg
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full"
      >
        {variant === 'badge' && (
          <rect 
            width="32" 
            height="32" 
            rx="7" 
            fill="#ffffff" 
            stroke="#dedbd3" 
            strokeWidth="1" 
          />
        )}

        {/* Clean, editorial geometric S mark for voice audio */}
        <path
          d="M 22 10.5 C 22 8 19.5 6.5 16 6.5 C 11.5 6.5 9 9 9 12.5 C 9 16 12 17.5 16 18.5 L 17.5 19 C 21 20 23 21.5 23 24.5 C 23 28 20 29.5 16 29.5 C 11 29.5 9 27 9 23.5"
          stroke="#1d1d1b"
          strokeWidth="2.75"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Restrained coral voice dot representing active acoustic input */}
        <circle cx="16" cy="18" r="1.6" fill="#b95740" />
      </svg>
    </div>
  );
};

export default ShinraLogo;
