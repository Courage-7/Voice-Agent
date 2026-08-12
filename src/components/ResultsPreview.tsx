export function ResultsPreview() {
  return (
    <figure className="results-preview" aria-label="Prototype interface preview">
      <div className="results-preview__rail">
        <span />
        <span />
        <span />
        <span />
        <span />
      </div>
      <div className="results-preview__main">
        <div className="results-preview__hero">
          <div className="results-preview__image">
            <svg aria-hidden="true" viewBox="0 0 120 70">
              <path d="m10 59 29-31 26 25 20-21 25 27" />
              <circle cx="85" cy="20" r="7" />
            </svg>
          </div>
          <div className="results-preview__lines" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </div>
        </div>
        <div className="results-preview__cards" aria-hidden="true">
          <i />
          <i />
          <i />
        </div>
      </div>
      <div className="results-preview__side" aria-hidden="true">
        <div className="results-preview__metric">
          <span className="results-preview__ring" />
          <i />
          <i />
        </div>
        <svg className="results-preview__chart" viewBox="0 0 130 90">
          <path d="M8 73 29 55l18 9 21-28 18 8 18-26 17 10" />
          <path className="results-preview__chart-baseline" d="M8 78h113" />
        </svg>
      </div>
    </figure>
  )
}
