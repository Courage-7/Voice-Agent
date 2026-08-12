import { useState } from 'react'
import { Brand } from './components/Brand'
import { Navigation } from './components/Navigation'
import { ResultsCanvas } from './components/ResultsCanvas'
import { VoiceStage } from './components/VoiceStage'

export default function App() {
  const [activeSection, setActiveSection] = useState('Voice')

  return (
    <main className="app-shell">
      <Brand />
      <Navigation activeSection={activeSection} onSelect={setActiveSection} />
      <VoiceStage />
      <ResultsCanvas />
    </main>
  )
}
