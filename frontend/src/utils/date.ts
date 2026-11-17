/**
 * Utility for uniform Indian Standard Time (IST, UTC+5:30) date & time formatting.
 * Safely parses UTC dates (including naive UTC strings without 'Z') and displays
 * exact local time across the entire application (e.g. "17/11/2026, 03:57:01 pm").
 */

export function parseUTCDate(dateVal?: string | Date | null): Date | null {
  if (!dateVal) return null;
  if (dateVal instanceof Date) return isNaN(dateVal.getTime()) ? null : dateVal;

  let s = String(dateVal).trim();
  if (!s) return null;

  // If missing timezone offset or 'Z', append 'Z' so browsers parse as UTC
  if (!s.endsWith('Z') && !/[+-]\d{2}:?\d{2}$/.test(s)) {
    if (s.includes('T')) {
      s += 'Z';
    } else if (s.includes(' ')) {
      s = s.replace(' ', 'T') + 'Z';
    }
  }

  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

export function formatDateTime(dateVal?: string | Date | null, options?: Intl.DateTimeFormatOptions): string {
  const d = parseUTCDate(dateVal);
  if (!d) return '';

  return d.toLocaleString('en-IN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
    ...options,
  });
}

export function formatDate(dateVal?: string | Date | null): string {
  const d = parseUTCDate(dateVal);
  if (!d) return '';

  return d.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

export function formatTime(dateVal?: string | Date | null): string {
  const d = parseUTCDate(dateVal);
  if (!d) return '';

  return d.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  });
}
