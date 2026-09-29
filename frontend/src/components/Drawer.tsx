import { useEffect, useRef, type ReactNode } from 'react'
import { animate, motion, useMotionValue, useReducedMotion, useTransform } from 'motion/react'

import { useMediaQuery } from '../hooks/useMediaQuery'

interface Props {
  open: boolean
  onClose: () => void
  children: ReactNode
}

const WIDTH = 288
const CLOSE_SLOP = 0.35
const VELOCITY_SLOP = 480
const SPRING = { type: 'spring', bounce: 0.2, duration: 0.3 } as const

/** Proyeccion de momento: donde acabaria el panel con esta velocidad (px/ms). */
function project(velocityPerMs: number, rate = 0.998): number {
  return (velocityPerMs * 1000 / 1000) * (rate / (1 - rate))
}

/** Resistencia progresiva mas alla del limite, en vez de un tope seco. */
function rubberband(overshoot: number, dimension: number, constant = 0.55): number {
  return (overshoot * dimension * constant) / (dimension + constant * Math.abs(overshoot))
}

export function Drawer({ open, onClose, children }: Props) {
  const wide = useMediaQuery('(min-width: 1024px)')
  const reduceMotion = useReducedMotion()
  const x = useMotionValue(0)
  const panelRef = useRef<HTMLDivElement>(null)
  const openRef = useRef(open)

  const scrimOpacity = useTransform(x, [-WIDTH, 0], [0, 1])

  useEffect(() => {
    openRef.current = open
  }, [open])

  useEffect(() => {
    if (wide) {
      x.set(0)
      return
    }
    animate(x, open ? 0 : -WIDTH, reduceMotion ? { duration: 0.001 } : SPRING)
  }, [open, wide, reduceMotion, x])

  const startDrag = (event: React.PointerEvent<HTMLDivElement>) => {
    if (wide) return
    if (event.pointerType === 'mouse' && event.button !== 0) return

    const node = panelRef.current
    if (!node) return
    const startX = event.clientX
    const base = x.get()
    // Historial corto de (tiempo, posicion): la velocidad sale de los dos ultimos.
    const samples: Array<{ t: number; x: number }> = [{ t: event.timeStamp, x: base }]
    node.setPointerCapture(event.pointerId)

    const onMove = (move: PointerEvent) => {
      const delta = move.clientX - startX
      const next = base + delta
      // Al arrastrar a la derecha desde cerrado, resiste de forma progresiva.
      x.set(next > 0 ? rubberband(next, WIDTH) : next)
      samples.push({ t: move.timeStamp, x: next })
      if (samples.length > 6) samples.shift()
    }

    const end = (up: PointerEvent) => {
      node.removeEventListener('pointermove', onMove)
      node.removeEventListener('pointerup', end)
      node.removeEventListener('pointercancel', end)
      try {
        node.releasePointerCapture(up.pointerId)
      } catch {
        /* el puntero ya se habia liberado */
      }

      if (reduceMotion) {
        x.set(openRef.current ? 0 : -WIDTH)
        return
      }

      const first = samples[0]
      const last = samples[samples.length - 1]
      const dt = first && last ? last.t - first.t : 0
      const velocity = dt > 0 && first && last ? ((last.x - first.x) / dt) * 1000 : 0
      const current = x.get()

      // Proyecta el punto de reposo y elige el destino mas cercano a el.
      // Un fling rapido manda sobre la posicion: decision por signo de velocidad.
      const flingClosed = velocity < -VELOCITY_SLOP
      const flingOpen = velocity > VELOCITY_SLOP
      const projected = current + project(velocity)
      const shouldClose = flingClosed || (!flingOpen && projected < -WIDTH * CLOSE_SLOP)

      // Entrega la velocidad del gesto al resorte: sin costura entre arrastre y animacion.
      animate(x, shouldClose ? -WIDTH : 0, { ...SPRING, velocity })
      if (shouldClose !== openRef.current) onClose()
    }

    node.addEventListener('pointermove', onMove)
    node.addEventListener('pointerup', end)
    node.addEventListener('pointercancel', end)
  }

  if (wide) {
    return (
      <aside className="glass-sidebar relative z-10 h-full w-72 shrink-0 border-r border-edge/60">
        {children}
      </aside>
    )
  }

  return (
    <>
      <motion.div
        className="fixed inset-0 z-30"
        style={{ opacity: scrimOpacity, background: 'var(--mat-veil)' }}
        onClick={onClose}
        aria-hidden="true"
      />
      <motion.aside
        ref={panelRef}
        className="glass-sidebar fixed inset-y-0 left-0 z-40 w-72 touch-pan-y border-r border-edge/60"
        style={{ x }}
        onPointerDown={startDrag}
      >
        {children}
      </motion.aside>
    </>
  )
}
