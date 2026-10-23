import type { ConnectionState } from '@/types';
import { WifiOff, Loader2 } from 'lucide-react';

export function ConnectionOverlay({ state }: { state: ConnectionState }) {
  if (state === 'live') return null;

  const label = state === 'connecting' ? 'Connecting to live simulation…'
    : state === 'reconnecting' ? 'Connection lost. Reconnecting…'
    : 'Live connection unavailable. Operating in offline mode.';

  const color = state === 'offline' ? '#d85b52' : '#d7a24a';
  const icon = state === 'offline' ? <WifiOff size={14} /> : <Loader2 size={14} className="animate-spin" />;

  return (
    <div className="flex items-center gap-2 px-4 h-8 flex-shrink-0 text-[11px]"
      style={{ background: color + '12', borderBottom: `1px solid ${color}33`, color }}>
      {icon}
      <span>{label}</span>
    </div>
  );
}
