import {
  AudioWaveform,
  Boxes,
  ChevronLeft,
  ChevronRight,
  Puzzle,
  ScrollText,
  Settings,
  Sparkles,
  Wrench,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { BrandMark } from './BrandMark'

interface NavigationProps {
  activeSection: string
  onSelect: (section: string) => void
}

interface NavigationItem {
  label: string
  icon: LucideIcon
  separated?: boolean
}

const navigationItems: NavigationItem[] = [
  { label: 'Voice', icon: AudioWaveform },
  { label: 'Capabilities', icon: Boxes },
  { label: 'Skills', icon: Sparkles },
  { label: 'Tools', icon: Wrench },
  { label: 'Plugins', icon: Puzzle },
  { label: 'Logs', icon: ScrollText, separated: true },
  { label: 'Settings', icon: Settings },
]

export function Navigation({ activeSection, onSelect }: NavigationProps) {
  const [isOpen, setIsOpen] = useState(false)
  const navigationId = useId()
  const navigationRef = useRef<HTMLElement>(null)

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (
        isOpen &&
        navigationRef.current &&
        !navigationRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setIsOpen(false)
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen])

  return (
    <nav className="navigation" ref={navigationRef} aria-label="VAgent sections">
      <button
        aria-controls={navigationId}
        aria-expanded={isOpen}
        aria-label={isOpen ? 'Close navigation' : 'Open navigation'}
        className="navigation__trigger"
        onClick={() => setIsOpen((open) => !open)}
        type="button"
      >
        <BrandMark className="navigation__trigger-mark" size={27} />
        {isOpen ? (
          <ChevronLeft aria-hidden="true" className="navigation__chevron" size={18} />
        ) : (
          <ChevronRight aria-hidden="true" className="navigation__chevron" size={18} />
        )}
      </button>

      <div
        aria-hidden={!isOpen}
        className="navigation__panel"
        data-open={isOpen}
        id={navigationId}
      >
        {navigationItems.map(({ label, icon: Icon, separated }) => {
          const isActive = label === activeSection

          return (
            <button
              aria-current={isActive ? 'page' : undefined}
              className="navigation__item"
              data-active={isActive}
              data-separated={separated || undefined}
              key={label}
              onClick={() => {
                onSelect(label)
                setIsOpen(false)
              }}
              tabIndex={isOpen ? 0 : -1}
              type="button"
            >
              <Icon aria-hidden="true" size={21} strokeWidth={1.7} />
              <span>{label}</span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}
