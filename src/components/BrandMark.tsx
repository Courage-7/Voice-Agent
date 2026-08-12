interface BrandMarkProps {
  size?: number
  className?: string
}

export function BrandMark({ size = 42, className = '' }: BrandMarkProps) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      height={size}
      viewBox="0 0 48 48"
      width={size}
    >
      <defs>
        <linearGradient id="vagent-mark" x1="6" x2="43" y1="8" y2="42">
          <stop offset="0" stopColor="#1768ff" />
          <stop offset="1" stopColor="#7a5cff" />
        </linearGradient>
      </defs>
      <circle
        cx="24"
        cy="24"
        fill="none"
        r="19"
        stroke="url(#vagent-mark)"
        strokeDasharray="5 4"
        strokeLinecap="round"
        strokeWidth="1.8"
      />
      <path
        d="M13 14.5 24 35l11-20.5"
        fill="none"
        stroke="url(#vagent-mark)"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="5"
      />
      <circle cx="24" cy="5" fill="#7a5cff" r="2" />
      <circle cx="43" cy="24" fill="#596dff" r="2" />
      <circle cx="24" cy="43" fill="#1768ff" r="2" />
      <circle cx="5" cy="24" fill="#3b7bff" r="2" />
    </svg>
  )
}
