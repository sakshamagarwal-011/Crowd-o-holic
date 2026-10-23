import { useSimulation } from '@/state/SimulationContext';
import { riskColor, formatSimClock } from '@/utils/display';
import { Activity, Flame, Route as RouteIcon, Zap, Brain, AlertTriangle, FileText, History } from 'lucide-react';
import type { TimelineEntry, TimelineEntryKind } from '@/types';

const KIND_ICON: Record<TimelineEntryKind, React.ReactNode> = {
  simulation: <Activity size={11} color="#d39a5a" />,
  bottleneck: <Flame size={11} color="#d85b52" />,
  'route-change': <RouteIcon size={11} color="#817d74" />,
  emergency: <Zap size={11} color="#e04d45" />,
  'ai-recommendation': <Brain size={11} color="#d39a5a" />,
  alert: <AlertTriangle size={11} color="#d7a24a" />,
  scenario: <FileText size={11} color="#89867d" />,
};

const KIND_LABEL: Record<TimelineEntryKind, string> = {
  simulation: 'Sim', bottleneck: 'Bottleneck', 'route-change': 'Route',
  emergency: 'Emergency', 'ai-recommendation': 'AI', alert: 'Alert', scenario: 'Scenario',
};

export function Timeline() {
  const { snapshot, scenario } = useSimulation();
  const entries = snapshot?.timeline ?? [];

  return (
    <div className="cmd-panel rounded-lg h-full flex flex-col overflow-hidden">
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <History size={13} color="#d39a5a" />
          <span className="cmd-label">Event timeline</span>
        </div>
        <span className="panel-count">{entries.length} events</span>
      </div>
      <div className="flex-1 overflow-x-auto overflow-y-hidden">
        {entries.length === 0 ? (
          <div className="empty-state empty-state--compact">
            <div className="empty-state__icon"><History size={15} /></div>
            <div>
              <div className="empty-state__title">No events yet</div>
              <div className="empty-state__copy">Start the simulation to build a live event history.</div>
            </div>
          </div>
        ) : (
          <div className="flex gap-0 min-w-max h-full">
            {entries.slice(0, 30).reverse().map((e) => (
              <TimelineItem key={e.id} e={e} startMin={scenario.timing.startMinutesOfDay} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TimelineItem({ e, startMin }: { e: TimelineEntry; startMin: number }) {
  const color = e.severity ? riskColor(e.severity) : '#89867d';
  return (
    <div className="timeline-item">
      <div className="flex items-center gap-1 mb-1">
        {KIND_ICON[e.kind]}
        <span className="text-[8px] font-bold" style={{ color }}>
          {KIND_LABEL[e.kind]}
        </span>
      </div>
      <div className="text-[9px] cmd-mono-value mb-1" style={{ color: 'var(--cmd-text-faint)' }}>
        {formatSimClock(startMin + e.atMinute)}
      </div>
      <div className="h-1 rounded-full mb-1.5" style={{ background: color + '40' }}>
        <div className="h-full rounded-full" style={{ background: color, width: '100%' }} />
      </div>
      <div className="text-[9px] text-center leading-tight line-clamp-2" style={{ color: 'var(--cmd-text-dim)' }}>
        {e.title}
      </div>
    </div>
  );
}
