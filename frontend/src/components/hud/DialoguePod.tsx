import React from 'react';
import { Volume2, Mic } from 'lucide-react';
import { SessionState } from '@/types';

interface DialoguePodProps {
  state: SessionState;
  subtitle: string;
  audioRMS: number;
}

export const DialoguePod: React.FC<DialoguePodProps> = ({
  state,
  subtitle,
  audioRMS,
}) => {
  const isUserSpeaking = state === 'USER_SPEAKING';
  const isAgentSpeaking = state === 'SPEAKING';

  let speakerLabel = 'SHINRA VOICE';
  if (isUserSpeaking) speakerLabel = 'USER';
  else if (state === 'THINKING') speakerLabel = 'PROCESSING...';
  else if (isAgentSpeaking) speakerLabel = 'SHINRA';

  return (
    <div className="w-full shinra-card rounded-xl p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isUserSpeaking ? (
            <Mic className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <Volume2 className="w-3.5 h-3.5 text-[#10B981]" />
          )}
          <span className="font-['JetBrains_Mono'] text-[11px] font-bold tracking-wider text-zinc-300">
            {speakerLabel}
          </span>
        </div>

        {/* Minimalist Equalizer Pulse */}
        <div className="flex items-center gap-1 h-3">
          {[...Array(6)].map((_, i) => {
            const h = 3 + Math.sin(i * 1.8 + (audioRMS > 0.05 ? audioRMS * 15 : 1)) * 6 * (audioRMS > 0.05 ? audioRMS * 2 : 0.2);
            return (
              <div
                key={i}
                className={`w-[2.5px] rounded-full transition-all duration-75 ${
                  isUserSpeaking ? 'bg-emerald-400' : 'bg-[#10B981]'
                }`}
                style={{ height: `${Math.max(3, Math.min(12, h))}px` }}
              />
            );
          })}
        </div>
      </div>

      <p className={`font-['Space_Grotesk'] text-[15px] leading-relaxed transition-colors duration-200 ${
        isUserSpeaking
          ? 'text-emerald-300 font-medium'
          : isAgentSpeaking
          ? 'text-white font-medium'
          : 'text-zinc-400'
      }`}>
        {subtitle}
      </p>
    </div>
  );
};
