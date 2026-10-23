import { FormEvent, useState } from 'react';
import { ExternalLink, Loader2, Radar, Search } from 'lucide-react';
import {
  apiSearchIntelligence,
  IntelligenceSearchResult,
  isBackendConfigured,
} from '@/services/backendClient';

export function LiveIntelligencePanel() {
  const [query, setQuery] = useState('local crowd safety and transport advisories');
  const [result, setResult] = useState<IntelligenceSearchResult | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (query.trim().length < 3) return;
    setLoading(true);
    setError('');
    try {
      setResult(await apiSearchIntelligence(query.trim()));
    } catch (caught) {
      setResult(null);
      setError(caught instanceof Error ? caught.message : 'Live research is unavailable.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="cmd-panel rounded p-3 space-y-2">
      <div className="flex items-center gap-2">
        <Radar size={14} color="#5bb8d8" />
        <span className="cmd-label">Live intelligence</span>
        <span className="ml-auto text-[9px]" style={{ color: 'var(--cmd-text-faint)' }}>TinyFish</span>
      </div>
      {!isBackendConfigured ? (
        <p className="text-[11px] leading-relaxed" style={{ color: 'var(--cmd-text-faint)' }}>
          Available when the backend is connected.
        </p>
      ) : (
        <>
          <form onSubmit={submit} className="flex gap-1.5">
            <input
              aria-label="Search public sources"
              value={query}
              maxLength={300}
              onChange={(event) => setQuery(event.target.value)}
              className="min-w-0 flex-1 rounded px-2 py-1.5 text-[11px] bg-black/20 border border-[var(--cmd-border)] text-white"
            />
            <button type="submit" disabled={loading} className="rounded px-2 py-1.5 bg-white/10 disabled:opacity-50" aria-label="Search public sources">
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
            </button>
          </form>
          {error && <p className="text-[10px] leading-snug text-red-300">{error}</p>}
          {result && (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {result.results.length === 0 && <p className="text-[11px]" style={{ color: 'var(--cmd-text-faint)' }}>No public sources found.</p>}
              {result.results.map((source) => (
                <a key={source.url} href={source.url} target="_blank" rel="noreferrer" className="block rounded p-2 bg-white/[0.03] hover:bg-white/[0.06]">
                  <div className="flex gap-1 text-[11px] font-medium text-white"><span className="truncate">{source.title}</span><ExternalLink size={11} className="shrink-0" /></div>
                  <p className="mt-1 text-[10px] leading-snug line-clamp-2" style={{ color: 'var(--cmd-text-dim)' }}>{source.snippet}</p>
                </a>
              ))}
              <p className="text-[9px] leading-snug" style={{ color: 'var(--cmd-text-faint)' }}>{result.disclaimer}</p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
