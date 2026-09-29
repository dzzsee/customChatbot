import { AudioIcon, DocumentIcon, ImageIcon, VideoIcon } from './icons'

/** Mapa de tipo de adjunto a icono. Vive aparte para no romper el fast refresh. */
export const KIND_GLYPH = {
  image: ImageIcon,
  video: VideoIcon,
  audio: AudioIcon,
  document: DocumentIcon,
} as const
