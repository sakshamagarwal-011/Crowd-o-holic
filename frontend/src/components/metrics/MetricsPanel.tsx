import { useEffect, useRef, useState } from 'react';
import { useSimulation } from '@/state/SimulationContext';
import { pct } from '@/utils/display';
import type { CrowdMetrics } from '@/types';

export function MetricsPanel() {
  const { snapshot, scenario } = useSimulation();
  const metrics = snapshot?.metrics;
  const safety = snapshot?.safety;
  const [history, setHistory] = useState<Record<string, number[]>>({ people: [], density: [], flow: [], speed: [], capacity: [] });
  const lastSample = useRef(0);

  useEffect(() => {
    if (!metrics) return;
    const now = Date.now();
    if (now - lastSample.current < 1000) return;
    lastSample.current = now;
    setHistory((prev) => ({
      people: [...prev.people, metrics.peopleCount].slice(-300),
      density: [...prev.density, metrics.avgDensity].slice(-300),
      flow: [...prev.flow, metrics.flowRate].slice(-300),
      speed: [...prev.speed, metrics.avgSpeed].slice(-300),
      capacity: [...prev.capacity, metrics.capacityUtilization].slice(-300),
    }));
  }, [metrics]);

  if (!metrics || !safety) return <div className="metrics-strip metrics-strip--empty">Awaiting live metrics…</div>;

  const risk = riskTreatment(safety.riskLevel);
  return (
    <section className="metrics-strip" aria-label="Live crowd metrics">
      <Metric
        label={scenario?.crowdSize ? `In Transit (${scenario.crowdSize.toLocaleString()} total)` : 'People In Transit'}
        value={metrics.peopleCount.toLocaleString()}
        series={history.people}
        hero
      />
      <Metric label="Density" value={pct(metrics.avgDensity)} series={history.density} />
      <Metric label="Flow" value={`${metrics.flowRate}/min`} series={history.flow} />
      <Metric label="Speed" value={`${metrics.avgSpeed.toFixed(1)} m/s`} series={history.speed} />
      <Metric label="Capacity" value={pct(metrics.capacityUtilization)} series={history.capacity} />
      <Metric label="Bottlenecks" value={String(safety.bottlenecks.length)} series={[]} tone={safety.bottlenecks.length ? 'critical' : 'safe'} />
      <div className="metric-risk" data-risk={safety.riskLevel}>
        <div className="metric-label">Risk {snapshot?.simulation?.status === 'idle' ? '(Standby)' : ''}</div>
        <div className="metric-risk__value">
          <strong style={{ color: risk.color }}>{safety.riskScore}</strong>
          <span>/100</span>
          {snapshot?.simulation?.status === 'idle' && (
            <span style={{ fontSize: '10px', color: 'var(--cmd-text-faint)', marginLeft: '6px' }}>STANDBY</span>
          )}
        </div>
        <div className="metric-risk__bar"><span style={{ width: `${Math.min(100, safety.riskScore)}%`, background: risk.color }} /></div>
      </div>
    </section>
  );
}

function Metric({ label, value, series, hero, tone }: { label: string; value: string; series: number[]; hero?: boolean; tone?: 'safe' | 'critical' }) {
  const toneColor = tone === 'critical' ? 'var(--critical)' : tone === 'safe' ? 'var(--safe)' : undefined;
  return (
    <div className={`metric-cell ${hero ? 'metric-cell--hero' : ''}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={toneColor ? { color: toneColor } : undefined}>{value}</div>
      {series.length > 1 && <Sparkline values={series} />}
    </div>
  );
}

function Sparkline({ values }: { values: number[] }) {
  const points = values.slice(-60);
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const d = points.map((v, i) => `${(i / Math.max(1, points.length - 1)) * 40},${12 - ((v - min) / range) * 10}`).join(' ');
  return <svg className="metric-spark" width="40" height="12" viewBox="0 0 40 12" aria-hidden="true"><polyline points={d} fill="none" stroke="currentColor" strokeWidth="1.2" vectorEffect="non-scaling-stroke" /></svg>;
}

function riskTreatment(level: string) {
  if (level === 'critical' || level === 'emergency' || level === 'high') return { color: 'var(--critical)' };
  if (level === 'moderate') return { color: 'var(--warning)' };
  return { color: 'var(--text-muted)' };
}

export { densityColor } from './legacyDensity';
export type { CrowdMetrics };
