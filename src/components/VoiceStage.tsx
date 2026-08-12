import { VoiceOrb } from './VoiceOrb'

export function VoiceStage() {
  return (
    <section className="voice-stage" id="voice-stage" aria-labelledby="voice-state">
      <VoiceOrb />
      <p className="voice-stage__status" id="voice-state" role="status" aria-live="polite">
        Listening
      </p>
    </section>
  )
}
