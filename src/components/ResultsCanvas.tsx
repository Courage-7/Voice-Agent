import { ExternalLink } from 'lucide-react'
import { ResultsPreview } from './ResultsPreview'

const priorities = [
  'Finalize the prototype',
  'Prepare the walkthrough',
  'Review open questions',
]

const resourceLinks = [
  { label: 'Open prototype brief', href: '#prototype-brief' },
  { label: 'View walkthrough notes', href: '#walkthrough-notes' },
]

export function ResultsCanvas() {
  return (
    <section className="results" aria-labelledby="results-heading">
      <div className="results__content">
        <header className="results__header">
          <h1 id="results-heading">Here’s what I found</h1>
          <p>Your latest notes point to three priorities.</p>
        </header>

        <ul className="results__priorities">
          {priorities.map((priority) => (
            <li key={priority}>{priority}</li>
          ))}
        </ul>

        <ResultsPreview />

        <nav className="results__links" aria-label="Related results">
          {resourceLinks.map(({ label, href }) => (
            <a href={href} key={label}>
              <span>{label}</span>
              <ExternalLink aria-hidden="true" size={17} strokeWidth={1.7} />
            </a>
          ))}
        </nav>
      </div>
    </section>
  )
}
