export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB']
  let value = bytes / 1024
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(value >= 10 || index === 0 ? 0 : 1)} ${units[index]}`
}

export function formatDuration(seconds: number | null | undefined): string | null {
  if (seconds === null || seconds === undefined) return null
  const total = Math.round(seconds)
  const minutes = Math.floor(total / 60)
  const rest = total % 60
  return minutes > 0 ? `${minutes}m ${rest}s` : `${rest}s`
}

export const KIND_LABEL: Record<string, string> = {
  image: 'Imagen',
  video: 'Video',
  audio: 'Audio',
  document: 'Documento',
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  return 'Error desconocido.'
}
