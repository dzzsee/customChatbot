import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

function Icon({ children, ...props }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.7}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  )
}

export function ImageIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="3" y="4.5" width="18" height="15" rx="2.5" />
      <circle cx="8.75" cy="9.75" r="1.6" />
      <path d="m3.5 17 4.6-4.4a2 2 0 0 1 2.7-.06L15 16.6" />
      <path d="m14 14.2 1.9-1.8a2 2 0 0 1 2.7.06L21 14.6" />
    </Icon>
  )
}

export function VideoIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="2.5" y="5" width="13.5" height="14" rx="2.5" />
      <path d="M16 10.4 21.5 7.2v9.6L16 13.6z" />
    </Icon>
  )
}

export function AudioIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 10v4h3l4 3.5v-11L7 10z" />
      <path d="M15 9.4a3.6 3.6 0 0 1 0 5.2" />
      <path d="M17.8 6.6a7.4 7.4 0 0 1 0 10.8" />
    </Icon>
  )
}

export function DocumentIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M13.5 3H7a2.5 2.5 0 0 0-2.5 2.5v13A2.5 2.5 0 0 0 7 21h10a2.5 2.5 0 0 0 2.5-2.5V9z" />
      <path d="M13.5 3v6H19.5" />
      <path d="M8.5 13.5h7M8.5 16.5h5" />
    </Icon>
  )
}

export function ChatGlyph(props: IconProps) {  return (
    <Icon {...props}>
      <path d="M20.5 12.4c0 3.9-3.8 7-8.5 7a9.9 9.9 0 0 1-2.6-.34L4 20.5l1.3-3.7A6.6 6.6 0 0 1 3.5 12.4c0-3.9 3.8-7 8.5-7s8.5 3.1 8.5 7Z" />
      <path d="M8.75 12.2h.01M12 12.2h.01M15.25 12.2h.01" strokeWidth={2.4} />
    </Icon>
  )
}

export function SendIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
      <path d="M4.1 20.6 21 12.2 4.1 3.8v6.5l11.3 1.9-11.3 1.9z" />
    </svg>
  )
}

export function StopIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" {...props}>
      <rect x="6.5" y="6.5" width="11" height="11" rx="2.5" />
    </svg>
  )
}

export function ClipIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M20 11.5 12.3 19.2a5.4 5.4 0 0 1-7.6-7.6l7.9-7.9a3.6 3.6 0 0 1 5.1 5.1l-7.9 7.9a1.8 1.8 0 0 1-2.5-2.5l7.2-7.2" />
    </Icon>
  )
}

export function MicIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="9" y="2.75" width="6" height="11" rx="3" />
      <path d="M5.5 11.5a6.5 6.5 0 0 0 13 0" />
      <path d="M12 18v3.25" />
    </Icon>
  )
}

export function SpeakerIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4 9.5v5h3.2L12 18.4V5.6L7.2 9.5z" />
      <path d="M15.4 9.6a3.4 3.4 0 0 1 0 4.8" />
      <path d="M18.1 6.9a7.1 7.1 0 0 1 0 10.2" />
    </Icon>
  )
}

export function SearchIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <circle cx="10.75" cy="10.75" r="6.25" />
      <path d="m15.5 15.5 4 4" />
    </Icon>
  )
}

export function TrashIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M4.5 6.75h15" />
      <path d="M9.5 6.75V5.5A1.5 1.5 0 0 1 11 4h2a1.5 1.5 0 0 1 1.5 1.5v1.25" />
      <path d="M6.5 6.75 7.3 19a1.5 1.5 0 0 0 1.5 1.4h6.4a1.5 1.5 0 0 0 1.5-1.4l.8-12.25" />
      <path d="M10.5 10.5v6M13.5 10.5v6" />
    </Icon>
  )
}

export function PlusIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M12 5.5v13M5.5 12h13" />
    </Icon>
  )
}

export function SidebarIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <rect x="3.5" y="4.5" width="17" height="15" rx="2.5" />
      <path d="M10 4.5v15" />
    </Icon>
  )
}

export function CloseIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m6.5 6.5 11 11M17.5 6.5l-11 11" />
    </Icon>
  )
}

export function BrainIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="M9.5 4.5a2.75 2.75 0 0 0-2.75 2.75 2.5 2.5 0 0 0-1.9 4.2A2.75 2.75 0 0 0 6.5 15.5c0 .9.44 1.7 1.12 2.17.44.5.7 1.14.7 1.83V20a1.5 1.5 0 0 0 3 0v-.5a1.5 1.5 0 0 1 3 0v.5a1.5 1.5 0 0 0 3 0v-.5c0-.69.26-1.33.7-1.83A2.6 2.6 0 0 0 19.5 15.5a2.75 2.75 0 0 0 1.65-4.05 2.5 2.5 0 0 0-1.9-4.2A2.75 2.75 0 0 0 14.5 4.5a2.6 2.6 0 0 0-2.5 1.9 2.6 2.6 0 0 0-2.5-1.9Z" />
      <path d="M12 8.5v9" />
    </Icon>
  )
}

export function ChevronDownIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m6.5 9.5 5.5 5.5 5.5-5.5" />
    </Icon>
  )
}

export function CheckIcon(props: IconProps) {
  return (
    <Icon {...props}>
      <path d="m5 12.5 4.5 4.5L19 7" />
    </Icon>
  )
}
