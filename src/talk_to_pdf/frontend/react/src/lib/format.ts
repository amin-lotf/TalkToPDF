const dateFormatter = new Intl.DateTimeFormat(undefined, {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
  hour: 'numeric',
  minute: '2-digit',
})

export function formatDateTime(value?: string | null) {
  if (!value) {
    return 'Unavailable'
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  return dateFormatter.format(date)
}

export function formatFileSize(sizeBytes?: number | null) {
  if (sizeBytes == null || Number.isNaN(sizeBytes)) {
    return 'Unknown size'
  }

  if (sizeBytes < 1024) {
    return `${sizeBytes} B`
  }

  const units = ['KB', 'MB', 'GB']
  let size = sizeBytes / 1024
  let unitIndex = 0

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex += 1
  }

  return `${size.toFixed(size >= 100 ? 0 : 1)} ${units[unitIndex]}`
}

export function formatDuration(seconds?: number | null) {
  if (seconds == null || Number.isNaN(seconds)) {
    return 'N/A'
  }

  if (seconds < 1) {
    return `${Math.round(seconds * 1000)} ms`
  }

  return `${seconds.toFixed(2)} s`
}

export function formatNumber(value?: number | null) {
  if (value == null || Number.isNaN(value)) {
    return 'N/A'
  }

  return new Intl.NumberFormat().format(value)
}

export function titleCase(value: string) {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}
