import { useState } from 'react';
import { useSimulation } from '@/state/SimulationContext';
import { Sparkles, Loader2, CheckCircle2, ChevronRight, Shuffle, Check, AlertTriangle, ShieldAlert } from 'lucide-react';

const SAMPLE = `A concert with 20,000 people starts at 7 PM. Most people enter through the east gate and food stalls are near the north corridor.`;
const ACCEPTANCE_SAMPLE = `A music festival is hosting 30,000 attendees across multiple zones. One attendee collapses near the front-stage area, and security requests immediate medical assistance. Meanwhile, camera observations show increasing crowd density near the front stage, restricted movement along the medical access corridor, and moderate congestion near the main entrance.`;

const TEST_SCENARIOS = [
  ACCEPTANCE_SAMPLE,
  'An IPL match with 32,000 spectators starts at 7 PM. 60% arrive through the east gate, 25% through the west gate, and the rest through the south gate.',
  'A music concert with 18,000 people begins at 8 PM. Heavy rain starts 30 minutes before entry, so most visitors arrive in a short surge through the west gate.',
  'A college festival expects 12,500 visitors from 4 PM to 10 PM. Food court visitors use the south gate while the main stage audience enters through east and west gates.',
  'A football match has 28,000 attendees at 6 PM. The east gate is partially restricted, so redirect most arrivals to the west and south gates.',
  'A medical emergency closes the north corridor during a 15,000-person concert at 7 PM. Keep the crowd moving toward the main stage through east and south entries.',
];

export function AIScenarioAssistant() {
  const { interpretScenario, applyExtractedScenario, aiStage, aiNotes, aiExtracted, scenario } = useSimulation();
  const [text, setText] = useState('');
  const [justApplied, setJustApplied] = useState(false);

  function loadTestScenario() {
    const next = TEST_SCENARIOS[Math.floor(Math.random() * TEST_SCENARIOS.length)];
    setText(next);
  }

  function handleApply() {
    applyExtractedScenario();
    setJustApplied(true);
    setTimeout(() => setJustApplied(false), 3000);
  }

  const isProcessing = aiStage === 'understanding' || aiStage === 'extracting' || aiStage === 'validating';
  const isReady = aiStage === 'ready' && aiExtracted;

  return (
    <div className="cmd-panel rounded p-3 space-y-3">
      <div className="flex items-center gap-2">
        <Sparkles size={14} style={{ color: '#d39a5a' }} />
        <span className="cmd-label">AI Scenario Assistant</span>
      </div>

      <div className="relative">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Describe your event scenario, crowd size, emergency incidents, camera observations, or restrictions in natural language…"
          rows={3}
          className="w-full bg-[var(--cmd-bg)] border border-[var(--cmd-border)] rounded p-2.5 text-[12px] text-[var(--cmd-text)] placeholder:text-[var(--cmd-text-faint)] resize-none focus:outline-none focus:border-[var(--live)] focus:ring-1 focus:ring-[var(--live)]/30 transition-colors"
        />
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={() => text.trim() && interpretScenario(text)}
          disabled={!text.trim() || isProcessing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[11px] font-semibold transition-all disabled:opacity-40"
          style={{ background: 'rgba(211,154,90,0.12)', border: '1px solid rgba(211,154,90,0.55)', color: '#d39a5a' }}
        >
          {isProcessing ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
          <span>{isProcessing ? 'INTERPRETING…' : 'INTERPRET'}</span>
        </button>
        <button
          onClick={() => setText(ACCEPTANCE_SAMPLE)}
          className="text-[10px] text-[var(--cmd-text-dim)] hover:text-[var(--cmd-text)] underline underline-offset-2"
        >
          Acceptance prompt
        </button>
        <button
          onClick={() => setText(SAMPLE)}
          className="text-[10px] text-[var(--cmd-text-dim)] hover:text-[var(--cmd-text)] underline underline-offset-2"
        >
          Sample
        </button>
        <button
          onClick={loadTestScenario}
          className="ml-auto flex items-center gap-1 text-[10px] text-[var(--cmd-text-dim)] hover:text-[var(--cmd-text)] underline underline-offset-2"
        >
          <Shuffle size={10} /> Test scenario
        </button>
      </div>

      {/* processing pipeline */}
      {aiStage !== 'idle' && (
        <div className="space-y-1.5 pt-1">
          <PipelineStage
            active={aiStage === 'understanding'}
            done={aiStage === 'extracting' || aiStage === 'validating' || aiStage === 'ready'}
            label="Understanding scenario & incidents"
          />
          <PipelineStage
            active={aiStage === 'extracting'}
            done={aiStage === 'validating' || aiStage === 'ready'}
            label="Extracting parameters & resolving venue locations"
          />
          <PipelineStage
            active={aiStage === 'validating'}
            done={aiStage === 'ready'}
            label="Validating configuration against venue graph"
          />
          {isReady && <PipelineStage active={false} done={true} label="Validated scenario ready" />}
        </div>
      )}

      {/* extracted parameters */}
      {isReady && aiExtracted && (
        <div className="space-y-2 pt-2 border-t border-[var(--cmd-border)]">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 size={12} color="#8fa66f" />
            <span className="cmd-label">Validated Parameters</span>
            <span className="ml-auto text-[9px] px-1.5 py-0.5 rounded font-mono uppercase font-semibold"
              style={{ background: 'rgba(143,166,111,0.15)', color: '#8fa66f' }}>
              Validated
            </span>
          </div>

          {/* Notes list */}
          {aiNotes.map((n, i) => (
            <div key={i} className="flex items-start gap-1.5 text-[11px]" style={{ color: 'var(--cmd-text-dim)' }}>
              <ChevronRight size={11} color="#d39a5a" className="mt-0.5 flex-shrink-0" />
              <span>{n}</span>
            </div>
          ))}

          {/* Unresolved location warning banner */}
          {aiExtracted.unresolvedLocations && aiExtracted.unresolvedLocations.length > 0 && (
            <div className="rounded p-2 text-[11px] flex items-start gap-1.5"
              style={{ background: 'rgba(215,162,74,0.12)', border: '1px solid rgba(215,162,74,0.3)', color: '#d7a24a' }}>
              <AlertTriangle size={13} className="flex-shrink-0 mt-0.5" />
              <div>
                <strong>Unresolved location:</strong> {aiExtracted.unresolvedLocations.join(', ')}.
                Preserved as unmapped without inventing node identifiers.
              </div>
            </div>
          )}

          {/* Parameter grid */}
          <div className="grid grid-cols-2 gap-1.5 pt-1">
            {aiExtracted.crowdSize != null && (
              <ParamRow
                label="Crowd Size"
                value={aiExtracted.crowdSize.toLocaleString()}
                provenance={aiExtracted.crowdSizeOrigin || 'explicit'}
              />
            )}
            {aiExtracted.timing && (
              <ParamRow
                label="Event Start"
                value={`${String(Math.floor(aiExtracted.timing.startMinutesOfDay / 60)).padStart(2, '0')}:${String(aiExtracted.timing.startMinutesOfDay % 60).padStart(2, '0')}`}
                provenance={aiExtracted.timingOrigin || 'default'}
              />
            )}
            {aiExtracted.entryDistribution && aiExtracted.entryDistribution.length > 0 && (() => {
              const sorted = [...aiExtracted.entryDistribution].sort((a, b) => b.fraction - a.fraction);
              const isEgress = Boolean(
                aiExtracted.timing?.departurePattern === 'surge' ||
                /leaving|ended|egress|exit|evacuat/i.test(aiExtracted.name || '')
              );
              return (
                <ParamRow
                  label={isEgress ? "Primary Flow / Gate" : "Primary Entry"}
                  value={sorted[0] ? `${gateLabel(sorted[0].gateId)} (${Math.round(sorted[0].fraction * 100)}%)` : '—'}
                  provenance={aiExtracted.entryDistributionOrigin || 'default'}
                />
              );
            })()}
            {aiExtracted.name && (
              <ParamRow
                label="Event Type"
                value={aiExtracted.name}
                provenance="inferred"
              />
            )}
          </div>

          {/* Extracted Incidents */}
          {aiExtracted.incidents && aiExtracted.incidents.length > 0 && (
            <div className="space-y-1.5 pt-1">
              <div className="cmd-label text-[10px] text-[var(--cmd-text-faint)] flex items-center gap-1">
                <ShieldAlert size={11} color="#e04d45" /> Active Incidents & Observations ({aiExtracted.incidents.length})
              </div>
              <div className="space-y-1">
                {aiExtracted.incidents.map((inc) => (
                  <div key={inc.id} className="text-[10px] rounded p-1.5 border border-[var(--cmd-border)] bg-[var(--cmd-bg)] flex items-start gap-1.5">
                    <span className="px-1 py-0.2 rounded font-mono text-[8px] uppercase font-bold"
                      style={{
                        background: inc.severity === 'emergency' ? 'rgba(224,77,69,0.2)' : 'rgba(211,154,90,0.2)',
                        color: inc.severity === 'emergency' ? '#e04d45' : '#d39a5a'
                      }}>
                      {inc.type}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-white truncate">{inc.description}</div>
                      <div className="text-[9px] text-[var(--cmd-text-dim)]">
                        Location: {inc.reported_location}
                        {inc.resolved_node_id && ` → [Node: ${inc.resolved_node_id}]`}
                        {inc.resolved_edge_id && ` → [Corridor: ${inc.resolved_edge_id}]`}
                        {inc.unresolved && ' (Unresolved)'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Apply button */}
          <div className="pt-2">
            <button
              onClick={handleApply}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded text-[12px] font-bold tracking-wide transition-all shadow-sm cursor-pointer hover:brightness-110"
              style={{
                background: justApplied ? 'rgba(143,166,111,0.25)' : 'rgba(211,154,90,0.20)',
                border: `1px solid ${justApplied ? '#8fa66f' : 'rgba(211,154,90,0.7)'}`,
                color: justApplied ? '#8fa66f' : '#d39a5a',
              }}
            >
              {justApplied ? <Check size={14} /> : <CheckCircle2 size={14} />}
              <span>{justApplied ? 'APPLIED TO SIMULATION' : 'APPLY TO SIMULATION'}</span>
            </button>
            <div className="text-[10px] text-center pt-1.5" style={{ color: justApplied ? '#8fa66f' : '#d39a5a' }}>
              {justApplied
                ? '✓ Active on engine! Press Play (▶) in top controls to run simulation'
                : 'Click to load this scenario & incidents into the active simulation'}
            </div>
          </div>

          <div className="text-[10px] text-[var(--cmd-text-faint)] pt-1 flex items-center justify-between">
            <span>Active scenario:</span>
            <span className="text-[var(--cmd-text-dim)] font-semibold">
              {scenario.name} ({scenario.crowdSize.toLocaleString()} attendees)
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function gateLabel(id: string): string {
  const map: Record<string, string> = {
    'gate-e': 'East Gate',
    'gate-w': 'West Gate',
    'gate-s': 'South Gate',
  };
  return map[id] ?? id;
}

function PipelineStage({ active, done, label }: {
  active: boolean; done: boolean; label: string;
}) {
  return (
    <div className="flex items-center gap-2 text-[11px]">
      {done ? <CheckCircle2 size={12} color="#8fa66f" />
        : active ? <Loader2 size={12} className="animate-spin" color="#d39a5a" />
        : <div className="w-3 h-3 rounded-full border border-[var(--cmd-border-bright)]" />}
      <span style={{ color: done ? '#8fa66f' : active ? '#d39a5a' : 'var(--cmd-text-faint)' }}>
        {label}
      </span>
    </div>
  );
}

function ParamRow({ label, value, provenance }: { label: string; value: string; provenance?: string }) {
  const provColor = provenance === 'explicit' ? '#8fa66f' : provenance === 'default' ? '#89867d' : '#d7a24a';
  return (
    <div className="cmd-surface-2 rounded px-2 py-1.5">
      <div className="flex items-center justify-between">
        <div className="cmd-label text-[9px]">{label}</div>
        {provenance && (
          <span className="text-[8px] font-mono uppercase font-bold" style={{ color: provColor }}>
            [{provenance}]
          </span>
        )}
      </div>
      <div className="text-[12px] font-semibold text-white">{value}</div>
    </div>
  );
}
