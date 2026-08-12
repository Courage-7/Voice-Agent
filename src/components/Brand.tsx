import { BrandMark } from './BrandMark'

export function Brand() {
  return (
    <a className="brand" href="#voice-stage" aria-label="VAgent home">
      <BrandMark size={44} />
      <span className="brand__name">VAgent</span>
    </a>
  )
}
