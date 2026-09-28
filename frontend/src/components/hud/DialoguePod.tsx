import React from 'react';
import { Volume2, Mic } from 'lucide-react';
import { SessionState } from '@/types';

interface DialoguePodProps {
  state: SessionState;
  subtitle: string;
  audioRMS: number;
}

const EQUALIZER_BARS = [0, 1, 2, 3, 4, 5];

export const DialoguePod: React.FC<DialoguePodProps> = ({
  state,
  subtitle,
  audioRMS,
}) => {
  const isUserSpeaking = state === 'USER_SPEAKING';
  const isAgentSpeaking = state === 'SPEAKING';

  let speakerLabel = 'STANDBY';
  if (isUserSpeaking) speakerLabel = 'OPERATOR';
  else if (state === 'THINKING') speakerLabel = 'THINKING...';
  else if (isAgentSpeaking) speakerLabel = 'ASSISTANT';

  let subtitleColor = 'text-zinc-300';
  if (isUserSpeaking) {
    subtitleColor = 'text-[#6ee7b7] font-medium';
  } else if (isAgentSpeaking) {
    subtitleColor = 'text-white font-medium';
  }

  return (
    <div className="w-full max-w-2xl mx-auto rounded-2xl bg-[#0b101d]/80 border border-white/10 p-3.5 backdrop-blur-2xl shadow-xl flex flex-col gap-1.5 transition-all">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isUserSpeaking ? (
            <Mic className="w-3.5 h-3.5 text-[#34D399]" />
          ) : (
            <Volume2 className="w-3.5 h-3.5 text-[#00F0FF]" />
          )}
          <span className="font-['JetBrains_Mono'] text-[10.5px] font-bold tracking-wider text-zinc-400 uppercase">
            {speakerLabel}
          </span>
        </div>

        {/* Dynamic Waveform Bars */}
        <div className="flex items-center gap-1 h-3.5">
          {EQUALIZER_BARS.map((idx) => {
            const h = 3 + Math.sin(idx * 1.6 + (audioRMS > 0.05 ? audioRMS * 14 : 1)) * 6 * (audioRMS > 0.05 ? audioRMS * 2 : 0.2);
            return (
              <div
                key={idx}
                className={`w-[2.5px] rounded-full transition-all duration-75 ${
                  isUserSpeaking ? 'bg-[#34D399]' : 'bg-[#00F0FF]'
                }`}
                style={{ height: `${Math.max(3, Math.min(14, h))}px` }}
              />
            );
          })}
        </div>
      </div>

      <p className={`font-['Plus_Jakarta_Sans'] text-[14px] sm:text-[15px] leading-snug line-clamp-2 transition-colors duration-200 ${subtitleColor}`}>
        {subtitle || "I'm here and ready to help. Speak naturally or type below."}
      </p>
    </div>
  );
};
