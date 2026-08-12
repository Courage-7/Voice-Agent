import { useEffect, useRef } from 'react'

interface OrbPoint {
  angle: number
  radius: number
  phase: number
  speed: number
  brightness: number
}

const TAU = Math.PI * 2
const POINT_COUNT = 760

function buildPoints(): OrbPoint[] {
  return Array.from({ length: POINT_COUNT }, (_, index) => {
    const angle = (index / POINT_COUNT) * TAU + Math.sin(index * 1.73) * 0.08
    const band = (index % 23) / 23
    return {
      angle,
      radius: 0.2 + band * 0.75 + Math.sin(index * 2.17) * 0.035,
      phase: (index * 0.61803398875) % TAU,
      speed: 0.45 + (index % 17) / 32,
      brightness: 0.25 + ((index * 13) % 71) / 100,
    }
  })
}

const points = buildPoints()

export function VoiceOrb() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const context = canvas.getContext('2d', { alpha: true })
    if (!context) return

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
    let frame = 0
    let width = 0
    let height = 0
    let dpr = 1

    const resize = () => {
      const bounds = canvas.getBoundingClientRect()
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      width = bounds.width
      height = bounds.height
      canvas.width = Math.round(width * dpr)
      canvas.height = Math.round(height * dpr)
      context.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    const draw = (timestamp = 0) => {
      const time = reduceMotion.matches ? 0 : timestamp * 0.00034
      context.clearRect(0, 0, width, height)

      const centerX = width / 2
      const centerY = height / 2
      const baseRadius = Math.min(width, height) * 0.405

      const halo = context.createRadialGradient(
        centerX,
        centerY,
        baseRadius * 0.12,
        centerX,
        centerY,
        baseRadius * 1.1,
      )
      halo.addColorStop(0, 'rgba(12, 42, 108, 0.38)')
      halo.addColorStop(0.62, 'rgba(6, 28, 88, 0.18)')
      halo.addColorStop(1, 'rgba(3, 8, 27, 0)')
      context.fillStyle = halo
      context.beginPath()
      context.arc(centerX, centerY, baseRadius * 1.13, 0, TAU)
      context.fill()

      context.globalCompositeOperation = 'lighter'

      for (let strand = 0; strand < 46; strand += 1) {
        context.beginPath()
        const strandPhase = (strand / 46) * TAU

        for (let step = 0; step <= 90; step += 1) {
          const angle = (step / 90) * TAU
          const deformation =
            1 +
            Math.sin(angle * 3 + time * 3.2 + strandPhase) * 0.09 +
            Math.sin(angle * 5 - time * 2.1 + strandPhase * 1.7) * 0.055
          const radius = baseRadius * (0.56 + strand / 112) * deformation
          const twist = Math.sin(angle * 2 + strandPhase + time * 1.8) * 0.22
          const x = centerX + Math.cos(angle + twist) * radius * 1.02
          const y = centerY + Math.sin(angle) * radius * 0.95

          if (step === 0) context.moveTo(x, y)
          else context.lineTo(x, y)
        }

        const violet = 110 + Math.round(Math.sin(strandPhase) * 38)
        context.strokeStyle = `rgba(${34 + violet / 8}, ${112 + violet / 3}, 255, ${
          0.12 + (strand % 8) * 0.012
        })`
        context.lineWidth = strand % 7 === 0 ? 1.05 : 0.52
        context.stroke()
      }

      for (const point of points) {
        const wave =
          Math.sin(point.angle * 3 + time * point.speed * 4 + point.phase) * 0.095 +
          Math.cos(point.angle * 5 - time * 2.4 + point.phase) * 0.045
        const radius = baseRadius * point.radius * (1 + wave)
        const angle = point.angle + Math.sin(point.phase + time) * 0.17
        const x = centerX + Math.cos(angle) * radius * 1.02
        const y = centerY + Math.sin(angle) * radius * 0.95
        const violetMix = (Math.sin(point.phase + time * 2) + 1) / 2

        context.fillStyle = `rgba(${72 + violetMix * 92}, ${139 + violetMix * 53}, 255, ${
          point.brightness
        })`
        context.beginPath()
        context.arc(x, y, point.brightness > 0.72 ? 1.15 : 0.72, 0, TAU)
        context.fill()
      }

      const flareAngle = time * 1.35 + 0.45
      const flareX = centerX + Math.cos(flareAngle) * baseRadius * 0.48
      const flareY = centerY + Math.sin(flareAngle * 1.24) * baseRadius * 0.34
      const flare = context.createRadialGradient(flareX, flareY, 0, flareX, flareY, 55)
      flare.addColorStop(0, 'rgba(255,255,255,.92)')
      flare.addColorStop(0.12, 'rgba(160,189,255,.78)')
      flare.addColorStop(0.5, 'rgba(83,74,255,.20)')
      flare.addColorStop(1, 'rgba(50,40,180,0)')
      context.fillStyle = flare
      context.beginPath()
      context.arc(flareX, flareY, 55, 0, TAU)
      context.fill()

      context.globalCompositeOperation = 'source-over'
      if (!reduceMotion.matches) frame = window.requestAnimationFrame(draw)
    }

    resize()
    draw()

    const observer = new ResizeObserver(() => {
      resize()
      if (reduceMotion.matches) draw()
    })
    observer.observe(canvas)

    return () => {
      observer.disconnect()
      window.cancelAnimationFrame(frame)
    }
  }, [])

  return (
    <div className="voice-orb" aria-hidden="true">
      <canvas ref={canvasRef} />
    </div>
  )
}
