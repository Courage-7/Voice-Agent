import React, { useEffect, useRef } from 'react';
import { SessionState } from '@/types';

interface FluidWaveformCanvasProps {
  state: SessionState;
  audioRMS: number;
}

export const FluidWaveformCanvas: React.FC<FluidWaveformCanvasProps> = ({ state, audioRMS }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const stateRef = useRef(state);
  const audioRMSRef = useRef(audioRMS);

  stateRef.current = state;
  audioRMSRef.current = audioRMS;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let time = 0;

    const handleResize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.scale(dpr, dpr);
    };

    handleResize();
    window.addEventListener('resize', handleResize);

    const render = () => {
      time += 0.02;
      const currentState = stateRef.current;
      const rms = audioRMSRef.current;

      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      const centerY = height / 2;

      ctx.clearRect(0, 0, width, height);

      const isActive = currentState === 'USER_SPEAKING' || currentState === 'SPEAKING';
      const isListening = currentState === 'LISTENING';
      const isThinking = currentState === 'THINKING';

      // 1. Center subtle datum baseline
      ctx.beginPath();
      ctx.moveTo(0, centerY);
      ctx.lineTo(width, centerY);
      ctx.lineWidth = 1;
      ctx.strokeStyle = 'rgba(15, 23, 42, 0.12)';
      ctx.stroke();

      // 2. Wave color based on semantic state
      let strokeColor = 'rgba(100, 116, 139, 0.35)';
      if (currentState === 'USER_SPEAKING') {
        strokeColor = '#b95740'; // Terracotta coral
      } else if (currentState === 'SPEAKING') {
        strokeColor = '#2563eb'; // Crisp cobalt blue
      } else if (isThinking) {
        strokeColor = '#d97706'; // Warm amber
      } else if (isListening) {
        strokeColor = '#334155'; // Deep slate
      }

      // 3. Modulated sine waveform responding directly to speech audioRMS
      const amplitude = isActive
        ? Math.min(48, 8 + rms * 140)
        : isListening
        ? 4 + Math.sin(time * 2) * 2
        : isThinking
        ? 6 + Math.sin(time * 3) * 4
        : 1.5;

      const frequency = isActive ? 0.022 : 0.012;
      const speed = isActive ? 3.0 : 1.2;

      ctx.beginPath();
      ctx.lineWidth = isActive ? 2.5 : 2;
      ctx.strokeStyle = strokeColor;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      let isFirst = true;
      const step = 4;

      for (let x = 0; x <= width; x += step) {
        // Window damping to taper gracefully at edges
        const windowDamping = Math.sin((x / width) * Math.PI);
        const yOffset =
          Math.sin(x * frequency - time * speed) *
          amplitude *
          Math.pow(windowDamping, 1.2);

        const y = centerY + yOffset;
        if (isFirst) {
          ctx.moveTo(x, y);
          isFirst = false;
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();

      // Second harmonic wave (quieter, secondary depth)
      if (isActive || isThinking) {
        ctx.beginPath();
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = strokeColor;
        ctx.globalAlpha = 0.45;

        isFirst = true;
        for (let x = 0; x <= width; x += step) {
          const windowDamping = Math.sin((x / width) * Math.PI);
          const yOffset =
            Math.sin(x * (frequency * 1.5) + time * (speed * 0.7)) *
            (amplitude * 0.5) *
            Math.pow(windowDamping, 1.2);

          const y = centerY + yOffset;
          if (isFirst) {
            ctx.moveTo(x, y);
            isFirst = false;
          } else {
            ctx.lineTo(x, y);
          }
        }
        ctx.stroke();
        ctx.globalAlpha = 1.0;
      }

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div className="w-full h-24 sm:h-28 flex items-center justify-center overflow-hidden select-none">
      <canvas
        ref={canvasRef}
        className="w-full h-full block cursor-default pointer-events-none"
        aria-hidden="true"
      />
    </div>
  );
};

export default FluidWaveformCanvas;
