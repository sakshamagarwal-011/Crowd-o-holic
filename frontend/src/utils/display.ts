import type { RiskLevel, ConnectionState } from '@/types';

export function riskColor(level: RiskLevel): string {
  switch (level) {
    case 'low': return '#8fa66f';
    case 'moderate': return '#d7a24a';
    case 'high': return '#d85b52';
    case 'critical': return '#c94b44';
    case 'emergency': return '#e04d45';
  }
}

export function riskBg(level: RiskLevel): string {
  switch (level) {
    case 'low': return 'rgba(143,166,111,0.12)';
    case 'moderate': return 'rgba(245,158,11,0.12)';
    case 'high': return 'rgba(239,68,68,0.12)';
    case 'critical': return 'rgba(220,38,38,0.15)';
    case 'emergency': return 'rgba(224,77,69,0.18)';
  }
}

export function riskLabel(level: RiskLevel): string {
  return level.charAt(0).toUpperCase() + level.slice(1);
}

export function connectionColor(c: ConnectionState): string {
  switch (c) {
    case 'live': return '#d39a5a';
    case 'connecting': return '#d7a24a';
    case 'reconnecting': return '#d7a24a';
    case 'offline': return '#d85b52';
  }
}

export function connectionLabel(c: ConnectionState): string {
  return c.charAt(0).toUpperCase() + c.slice(1);
}

export function formatSimClock(minOfDay: number): string {
  const m = ((minOfDay % 1440) + 1440) % 1440;
  const h = Math.floor(m / 60);
  const mm = Math.floor(m % 60);
  return `${String(h).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
}

export function formatDuration(min: number): string {
  if (min == null) return '—';
  const sign = min < 0 ? '-' : '';
  const abs = Math.abs(Math.round(min));
  return `${sign}${String(Math.floor(abs / 60)).padStart(2, '0')}:${String(abs % 60).padStart(2, '0')}`;
}

export function formatCountdown(min: number | null): string {
  if (min == null || min <= 0) return '—';
  const abs = Math.round(min);
  return `${String(Math.floor(abs / 60)).padStart(2, '0')}:${String(abs % 60).padStart(2, '0')}`;
}

export function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}
