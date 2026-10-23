import { useSimulation } from '@/state/SimulationContext';
import { STADIUM_A, NODE_MAP } from '@/data/venue';
import { Settings, AlertTriangle } from 'lucide-react';

export function ScenarioConfig() {
  const { scenario } = useSimulation();

  const entryGates = scenario.entryDistribution
    .sort((a, b) => b.fraction - a.fraction)
    .map((d) => ({ ...d, label: NODE_MAP[d.gateId]?.label ?? d.gateId }));

  const crowdProv = scenario.crowdSizeOrigin || scenario.parameterProvenance?.crowdSize || 'default';
  const timingProv = scenario.timingOrigin || scenario.parameterProvenance?.timing || 'default';
  const entryProv = scenario.entryDistributionOrigin || scenario.parameterProvenance?.entryDistribution || 'default';

  return (
    <div className="cmd-panel rounded">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[var(--cmd-border)]">
        <Settings size={13} color="#89867d" />
        <span className="cmd-label">Scenario Configuration</span>
        <span className="ml-auto text-[9px] font-mono px-1.5 py-0.5 rounded text-[var(--live)] bg-[var(--live)]/10 font-bold">
          {scenario.name.toUpperCase()}
        </span>
      </div>
      <div className="p-3 space-y-3">
        {/* crowd */}
        <Section
          label="Crowd"
          provenanceBadge={crowdProv}
        >
          <KV label="Total Size" value={scenario.crowdSize.toLocaleString()} highlight />
          <KV label="Groups" value={String(scenario.crowdGroups.length)} />
          <KV label="Entry Rate" value={`${scenario.entryRate}/min`} />
          <KV label="Exit Rate" value={`${scenario.exitRate}/min`} />
        </Section>

        {/* entry distribution */}
        <Section
          label="Entry distribution"
          provenanceBadge={entryProv}
        >
          <div className="space-y-1.5">
            {entryGates.map((g) => (
              <div key={g.gateId}>
                <div className="flex items-center justify-between text-[10px] mb-0.5">
                  <span style={{ color: 'var(--cmd-text-dim)' }}>{g.label}</span>
                  <span className="cmd-mono-value" style={{ color: '#d39a5a' }}>{Math.round(g.fraction * 100)}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-[var(--cmd-bg)] overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${g.fraction * 100}%`, background: '#d39a5a' }} />
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* timing */}
        <Section
          label="Event timing"
          provenanceBadge={timingProv}
        >
          <KV
            label="Start"
            value={`${String(Math.floor(scenario.timing.startMinutesOfDay / 60)).padStart(2, '0')}:${String(scenario.timing.startMinutesOfDay % 60).padStart(2, '0')}`}
          />
          <KV label="Duration" value={`${scenario.timing.durationMin} min`} />
          <KV label="Arrival" value={scenario.timing.arrivalPattern} />
          <KV label="Departure" value={scenario.timing.departurePattern} />
        </Section>

        {/* active incidents & observations */}
        <Section label="Active Incidents & Observations">
          {scenario.incidents && scenario.incidents.length > 0 ? (
            <div className="space-y-1.5">
              {scenario.incidents.map((inc) => (
                <div
                  key={inc.id}
                  className="rounded p-2 text-[10px] border border-[var(--cmd-border)]"
                  style={{
                    background: inc.severity === 'emergency' ? 'rgba(224,77,69,0.06)' : 'rgba(211,154,90,0.04)',
                    borderColor: inc.severity === 'emergency' ? 'rgba(224,77,69,0.3)' : 'var(--cmd-border)',
                  }}
                >
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span
                      className="px-1 py-0.2 rounded font-mono text-[8px] uppercase font-bold"
                      style={{
                        background: inc.severity === 'emergency' ? 'rgba(224,77,69,0.2)' : 'rgba(211,154,90,0.2)',
                        color: inc.severity === 'emergency' ? '#e04d45' : '#d39a5a',
                      }}
                    >
                      {inc.type}
                    </span>
                    <span className="text-[9px] font-mono text-[var(--cmd-text-faint)]">
                      {inc.verification_status}
                    </span>
                  </div>
                  <div className="font-semibold text-white leading-snug">{inc.description}</div>
                  <div className="text-[9px] text-[var(--cmd-text-dim)] mt-1">
                    Location: <span className="text-white">{inc.reported_location}</span>
                    {inc.resolved_node_id && ` · [Node: ${inc.resolved_node_id}]`}
                    {inc.resolved_edge_id && ` · [Corridor: ${inc.resolved_edge_id}]`}
                    {inc.unresolved && ' · (Unresolved location)'}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[10px]" style={{ color: 'var(--cmd-text-faint)' }}>
              No incidents active
            </div>
          )}
        </Section>

        {/* unresolved locations warning */}
        {scenario.unresolvedLocations && scenario.unresolvedLocations.length > 0 && (
          <div className="rounded p-2 text-[10px] flex items-start gap-1.5"
            style={{ background: 'rgba(215,162,74,0.12)', border: '1px solid rgba(215,162,74,0.3)', color: '#d7a24a' }}>
            <AlertTriangle size={12} className="mt-0.5 flex-shrink-0" />
            <div>
              <strong>Unresolved locations:</strong> {scenario.unresolvedLocations.join(', ')}.
            </div>
          </div>
        )}

        {/* crowd groups */}
        <Section label="Crowd groups">
          <div className="space-y-1">
            {scenario.crowdGroups.map((g) => (
              <div key={g.id} className="flex items-center gap-2 text-[10px]">
                <div className="w-1.5 h-1.5 rounded-sm" style={{ background: 'var(--cmd-text-faint)' }} />
                <span className="text-white font-medium truncate flex-1">{g.name}</span>
                <span className="cmd-mono-value" style={{ color: 'var(--cmd-text-dim)' }}>
                  {g.size.toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </Section>

        {/* venue summary */}
        <Section label="Venue">
          <KV label="Name" value={STADIUM_A.name} />
          <KV label="Nodes" value={String(STADIUM_A.nodes.length)} />
          <KV label="Corridors" value={String(STADIUM_A.edges.length)} />
          <KV label="Gates" value={String(STADIUM_A.nodes.filter((n) => n.kind === 'entry' || n.kind === 'exit').length)} />
        </Section>

        {/* special conditions */}
        <Section label="Special conditions">
          {scenario.specialConditions.length === 0 ? (
            <div className="text-[10px]" style={{ color: 'var(--cmd-text-faint)' }}>None configured</div>
          ) : (
            <div className="space-y-1">
              {scenario.specialConditions.map((c) => (
                <div key={c.id} className="text-[10px] flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#d7a24a' }} />
                  <span style={{ color: 'var(--cmd-text-dim)' }}>{c.label}</span>
                </div>
              ))}
            </div>
          )}
        </Section>
      </div>
    </div>
  );
}

function Section({ label, provenanceBadge, children }: {
  label: string;
  provenanceBadge?: string;
  children: React.ReactNode;
}) {
  const provColor = provenanceBadge === 'explicit' ? '#8fa66f' : provenanceBadge === 'default' ? '#89867d' : '#d7a24a';
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <div className="cmd-label">{label}</div>
        {provenanceBadge && (
          <span className="text-[8px] font-mono uppercase font-bold" style={{ color: provColor }}>
            [{provenanceBadge}]
          </span>
        )}
      </div>
      <div className="pl-2 space-y-1">{children}</div>
    </div>
  );
}

function KV({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex items-center justify-between text-[10px]">
      <span style={{ color: 'var(--cmd-text-faint)' }}>{label}</span>
      <span className={`cmd-mono-value ${highlight ? 'font-bold text-[var(--live)]' : 'text-white'}`}>
        {value}
      </span>
    </div>
  );
}
