import React, { useState } from 'react';

interface AppBrandIconProps {
  name: string;
  logoUrl?: string;
  className?: string;
  size?: number;
}

export const AppBrandIcon: React.FC<AppBrandIconProps> = ({
  name,
  logoUrl,
  className = '',
  size = 24,
}) => {
  const [imgError, setImgError] = useState(false);

  if (logoUrl && !imgError) {
    return (
      <img
        src={logoUrl}
        alt={name}
        width={size}
        height={size}
        className={`object-contain rounded-md ${className}`}
        onError={() => setImgError(true)}
        loading="lazy"
      />
    );
  }

  const normalized = (name || '').toUpperCase().replace(/[^A-Z]/g, '');

  switch (normalized) {
    case 'GITHUB':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <path
            fillRule="evenodd"
            clipRule="evenodd"
            d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
            fill="#181717"
          />
        </svg>
      );

    case 'SLACK':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313z" fill="#E01E5A"/>
          <path d="M8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312z" fill="#36C5F0"/>
          <path d="M18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312z" fill="#2EB67D"/>
          <path d="M15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.527 2.527 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" fill="#ECB22E"/>
        </svg>
      );

    case 'GMAIL':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <path d="M24 5.457v13.909c0 .904-.732 1.634-1.636 1.634h-3.819V11.15L12 16.039l-6.545-4.89v9.85H1.636A1.636 1.636 0 0 1 0 19.366V5.457c0-2.023 2.309-3.178 3.927-1.964L12 9.572l8.073-6.079C21.69 2.28 24 3.434 24 5.457z" fill="#EA4335" />
          <path d="M0 5.457c0-2.023 2.309-3.178 3.927-1.964L12 9.572 0 18.57V5.457z" fill="#4285F4" opacity="0.9" />
          <path d="M24 5.457c0-2.023-2.309-3.178-3.927-1.964L12 9.572 24 18.57V5.457z" fill="#FBBC05" opacity="0.9" />
          <path d="M18.545 11.15v9.85h3.819c.904 0 1.636-.73 1.636-1.634V5.457L18.545 11.15z" fill="#34A853" />
        </svg>
      );

    case 'GOOGLECALENDAR':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <rect x="3" y="3" width="18" height="18" rx="4" fill="#FFFFFF" stroke="#E2E8F0" strokeWidth="1" />
          <path d="M3 7h18V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v2z" fill="#4285F4" />
          <path d="M19 3v4" stroke="#EA4335" strokeWidth="1.5" strokeLinecap="round" />
          <path d="M5 3v4" stroke="#34A853" strokeWidth="1.5" strokeLinecap="round" />
          <text x="12" y="17" textAnchor="middle" fill="#1E293B" fontSize="9" fontWeight="bold" fontFamily="system-ui">
            31
          </text>
        </svg>
      );

    case 'NOTION':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <path
            d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952L12.21 19s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.139c-.093-.514.28-.887.747-.933zM1.936 1.035l13.31-.98c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.047-1.448-.093-1.962-.747l-3.129-4.06c-.56-.747-.793-1.306-.793-1.96V2.667c0-.839.374-1.54 1.447-1.632z"
            fill="#000000"
          />
        </svg>
      );

    case 'LINEAR':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <rect width="24" height="24" rx="6" fill="#5E6AD2" />
          <path
            d="M5.42 16.89a8.62 8.62 0 0 1 0-9.78l9.78 9.78a8.62 8.62 0 0 1-9.78 0zm1.7-11.48a8.62 8.62 0 0 1 9.78 0l-9.78 9.78a8.62 8.62 0 0 1 0-9.78zm11.46 1.7a8.62 8.62 0 0 1 0 9.78l-9.78-9.78a8.62 8.62 0 0 1 9.78 0z"
            fill="#FFFFFF"
          />
        </svg>
      );

    case 'POSTGRESQL':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <path
            d="M12 2C6.48 2 2 6.48 2 12c0 5.52 4.48 10 10 10s10-4.48 10-10c0-5.52-4.48-10-10-10zm-1.05 4.35c.7-.35 1.5-.55 2.35-.55.75 0 1.45.15 2.1.45.95.45 1.65 1.25 2 2.2.2.45.3.95.3 1.5 0 .8-.25 1.55-.7 2.15l-.2.25c-.2.25-.45.45-.7.65.1.3.15.6.15.9 0 1.4-.7 2.65-1.8 3.4-.3.2-.65.4-1 .5-.2.05-.4.1-.6.1-.8 0-1.5-.25-2.1-.75-.3-.25-.5-.5-.7-.85-.4.35-.85.6-1.35.75-.35.1-.7.15-1.05.15-1.15 0-2.2-.55-2.85-1.45-.3-.4-.45-.85-.5-1.35 0-.15 0-.3.05-.45.1-.9.65-1.65 1.45-2.1.35-.2.7-.35 1.1-.4.15-.3.35-.6.6-.85.4-.4.85-.75 1.35-1l.4-.2c.4-.2.85-.35 1.35-.45z"
            fill="#336791"
          />
        </svg>
      );

    case 'STRIPE':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <rect width="24" height="24" rx="6" fill="#635BFF" />
          <path
            d="M13.976 9.15c-2.172-.806-3.356-1.426-3.356-2.409 0-.831.683-1.305 1.901-1.305 2.227 0 4.515.858 6.09 1.631l.89-5.494C18.252.975 15.697 0 12.165 0 9.667 0 7.589.654 6.104 1.872 4.56 3.147 3.757 4.992 3.757 7.218c0 4.039 2.467 5.76 6.476 7.219 2.585.92 3.445 1.574 3.445 2.583 0 .98-.84 1.545-2.354 1.545-1.875 0-4.965-.921-6.99-2.109l-.9 5.555C5.175 22.99 8.385 24 11.714 24c2.641 0 4.843-.624 6.328-1.813 1.664-1.305 2.525-3.236 2.525-5.732 0-4.128-2.524-5.851-6.594-7.305h.003z"
            fill="#FFFFFF"
          />
        </svg>
      );

    case 'GOOGLEDRIVE':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <path
            d="M12.01 1.485c-2.082 0-3.754.02-3.743.047.01.02 1.708 3.001 3.774 6.62l3.76 6.574h3.76c2.081 0 3.753-.02 3.742-.047-.005-.02-1.708-3.001-3.775-6.62l-3.76-6.574z"
            fill="#FFBA00"
          />
          <path
            d="M7.25 3.214a789.828 789.861 0 0 0-3.63 6.319L0 15.868l1.89 3.298 1.885 3.297 3.62-6.335 3.618-6.33-1.88-3.287C8.1 4.704 7.255 3.22 7.25 3.214z"
            fill="#0066DA"
          />
          <path
            d="M9.509 15.867l-.203.348c-.114.198-.96 1.672-1.88 3.287a423.93 423.948 0 0 1-1.698 2.97c-.01.026 3.24.042 7.222.042h7.244l1.796-3.157c.992-1.734 1.85-3.23 1.906-3.323l.104-.167h-7.249z"
            fill="#00AC47"
          />
        </svg>
      );

    case 'GOOGLEDOCS':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <rect x="3" y="2" width="18" height="20" rx="3" fill="#4285F4" />
          <path d="M14 2l7 7h-7V2z" fill="#A1C2FA" opacity="0.6" />
          <rect x="6.5" y="11" width="11" height="1.5" rx="0.75" fill="#FFFFFF" />
          <rect x="6.5" y="14" width="11" height="1.5" rx="0.75" fill="#FFFFFF" />
          <rect x="6.5" y="17" width="7" height="1.5" rx="0.75" fill="#FFFFFF" />
        </svg>
      );

    case 'WHATSAPP':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <rect width="24" height="24" rx="6" fill="#25D366" />
          <path
            d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"
            fill="#FFFFFF"
          />
        </svg>
      );

    case 'TELEGRAM':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <path
            d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"
            fill="#24A1DE"
          />
        </svg>
      );

    case 'MICROSOFTTEAMS':
    case 'TEAMS':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <rect width="24" height="24" rx="6" fill="#4B53BC" />
          <path d="M14.5 9a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM17 10.5h-5a1.5 1.5 0 0 0-1.5 1.5v3.5a3 3 0 0 0 3 3h2a3 3 0 0 0 3-3V12a1.5 1.5 0 0 0-1.5-1.5z" fill="#7B83EB" />
          <circle cx="8" cy="7.5" r="2" fill="#FFFFFF" />
          <path d="M10 11.5H6a1.5 1.5 0 0 0-1.5 1.5v3a3 3 0 0 0 3 3h1a3 3 0 0 0 3-3V13a1.5 1.5 0 0 0-1.5-1.5z" fill="#FFFFFF" />
        </svg>
      );

    case 'LINKEDIN':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <rect width="24" height="24" rx="6" fill="#0A66C2" />
          <path d="M7.1 9.3H4.3V18h2.8V9.3zM5.7 5C4.8 5 4.1 5.7 4.1 6.6c0 .9.7 1.6 1.6 1.6.9 0 1.6-.7 1.6-1.6C7.3 5.7 6.6 5 5.7 5zm13.2 8.3c0-2.6-1.4-3.8-3.3-3.8-1.5 0-2.2.8-2.6 1.4V9.3h-2.8c.04.8 0 8.7 0 8.7h2.8v-4.9c0-.26.02-.52.1-.71.21-.52.7-1.06 1.52-1.06 1.13 0 1.58.86 1.58 2.12V18h2.8v-4.7z" fill="#FFFFFF" />
        </svg>
      );

    case 'NEON':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <rect width="24" height="24" rx="6" fill="#000000" />
          <path d="M6 18V6l10.5 12H18V6h-2.5v7.8L7.8 6H6v12z" fill="#00E599" />
        </svg>
      );

    case 'ILOVEPDF':
    case 'I_LOVE_PDF':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <rect width="24" height="24" rx="6" fill="#E5322D" />
          <path d="M12 7.5c-1.5-2.2-4.5-1.5-4.5 1.2 0 2.4 4.5 5.3 4.5 5.3s4.5-2.9 4.5-5.3c0-2.7-3-3.4-4.5-1.2z" fill="#FFFFFF" />
          <text x="12" y="19" textAnchor="middle" fill="#FFFFFF" fontSize="4.5" fontWeight="bold" fontFamily="system-ui">PDF</text>
        </svg>
      );

    case 'TALLY':
      return (
        <svg width={size} height={size} viewBox="0 0 128 124" fill="none" className={className}>
          <rect width="128" height="124" rx="28" fill="#18181B" />
          <path
            d="M79.9335 17.1445C79.9335 24.2262 77.3191 33.969 73.4647 47.0615L70.7069 57.1173L79.4337 51.4172C96.022 39.7688 106.04 35.397 112.67 35.397C120.212 35.397 128 40.7864 128 51.5052C128 65.1402 113.443 69.0136 85.3379 69.4912L74.8298 69.9849L83.1169 76.5821C102.791 91.747 109.612 99.1764 109.612 108.59C109.612 115.999 102.727 123.715 94.1897 123.715C81.3632 123.715 75.5655 110.387 67.7502 87.7575L63.7662 77.922L60.0183 87.7575C51.2591 113.46 44.5174 123.479 33.343 123.479C24.334 123.479 17.9208 115.289 17.9208 108.354C17.9208 97.9942 27.3369 89.3825 44.6517 76.5821L52.9388 69.9849L42.6666 69.4912C12.8171 69.2501 0 64.957 0 51.2688C0 40.55 8.02804 35.1605 15.4268 35.1605C24.3617 35.1605 34.1064 41.1875 48.5708 51.4172L57.2976 57.1173L54.5398 47.0615C50.3616 33.2597 48.3996 23.1344 48.3996 17.1445C48.3996 7.76783 53.6838 0 64.0023 0C74.5567 1.03096e-07 79.9335 7.76783 79.9335 17.1445Z"
            fill="#FFFFFF"
            transform="scale(0.8) translate(16, 12)"
          />
        </svg>
      );

    case 'SERPAPI':
    case 'GOOGLE':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05" />
          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335" />
        </svg>
      );

    case 'PERPLEXITYAI':
    case 'PERPLEXITY':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <rect width="24" height="24" rx="6" fill="#132B32" />
          <path
            d="M12 4v16M4 12h16M6.34 6.34l11.32 11.32M17.66 6.34L6.34 17.66"
            stroke="#20B8CD"
            strokeWidth="2"
            strokeLinecap="round"
          />
          <circle cx="12" cy="12" r="3" fill="#20B8CD" />
        </svg>
      );

    case 'TAVILY':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <rect width="24" height="24" rx="6" fill="#0C1E36" />
          <path
            d="M6 7.5h12M12 7.5v10M12 12l4.5 4.5M12 12l-4.5 4.5"
            stroke="#0EA5E9"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="12" cy="7.5" r="2" fill="#38BDF8" />
          <circle cx="16.5" cy="16.5" r="1.5" fill="#0EA5E9" />
          <circle cx="7.5" cy="16.5" r="1.5" fill="#0EA5E9" />
        </svg>
      );

    case 'GOOGLESHEETS':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <rect x="3" y="2" width="18" height="20" rx="3" fill="#0F9D58" />
          <path d="M14 2l7 7h-7V2z" fill="#87CEAB" opacity="0.6" />
          <rect x="6.5" y="10" width="11" height="8" rx="1" fill="#FFFFFF" />
          <path d="M6.5 14h11M12 10v8" stroke="#0F9D58" strokeWidth="1.2" />
        </svg>
      );

    case 'OUTLOOK':
      return (
        <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
          <rect x="2" y="4" width="20" height="16" rx="4" fill="#0078D4" />
          <path d="M2 7l10 7 10-7" stroke="#FFFFFF" strokeWidth="1.5" fill="none" />
          <circle cx="8" cy="13" r="3.5" fill="#106EBE" />
          <text x="8" y="15.5" textAnchor="middle" fill="#FFFFFF" fontSize="6.5" fontWeight="bold" fontFamily="system-ui">
            O
          </text>
        </svg>
      );

    default:
      return (
        <div
          className={`rounded-lg bg-slate-900 text-white flex items-center justify-center font-['Space_Grotesk'] font-bold text-[11px] shadow-sm ${className}`}
          style={{ width: size, height: size }}
        >
          {name.slice(0, 2).toUpperCase()}
        </div>
      );
  }
};
export default AppBrandIcon;
