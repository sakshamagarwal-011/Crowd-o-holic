import { useEffect, useMemo, useRef, useState } from 'react';
import { Camera, Circle, ExternalLink, Maximize2, Video } from 'lucide-react';
import { useSimulation } from '@/state/SimulationContext';

interface Feed {
  id: string;
  name: string;
  location: string;
  source: string;
  url: string;
  license: string;
}

// Real, openly licensed footage. The feeds are intentionally external so the
// repository stays lightweight; the attribution links are shown in the UI.
const FEEDS: Feed[] = [
  {
    id: 'cctv',
    name: 'CCTV OVERVIEW',
    location: 'REMOTE CAMERA DEMO',
    source: 'Wikimedia Commons',
    url: 'https://upload.wikimedia.org/wikipedia/commons/b/b4/Witson_CMS_CCTV_live_6_remote_sites_33_cameras_total_Night_Mode.webm',
    license: 'Public domain',
  },
  {
    id: 'spectators',
    name: 'SPECTATOR VIEW',
    location: 'FOOTBALL STAND',
    source: 'Wikimedia Commons',
    url: 'https://upload.wikimedia.org/wikipedia/commons/7/70/Spectators_during_a_football_match.webm',
    license: 'CC0',
  },
  {
    id: 'stadium',
    name: 'STADIUM WIDE',
    location: 'VENUE OVERVIEW',
    source: 'Wikimedia Commons',
    url: 'https://upload.wikimedia.org/wikipedia/commons/9/9b/Video_fra_Vejle_Stadion.webm',
    license: 'CC BY-SA 4.0',
  },
];

export function CameraWall() {
  const { snapshot, liveAgents } = useSimulation();
  const [activeId, setActiveId] = useState(FEEDS[0].id);
  const [failed, setFailed] = useState<Record<string, boolean>>({});
  const videoRef = useRef<HTMLVideoElement>(null);
  const active = useMemo(() => FEEDS.find((feed) => feed.id === activeId) ?? FEEDS[0], [activeId]);

  const people = snapshot?.metrics.peopleCount ?? liveAgents.length;
  const density = snapshot?.metrics.avgDensity ?? 0;
  const flow = snapshot?.metrics.flowRate ?? 0;
  const risk = snapshot?.safety.riskLevel ?? 'low';

  useEffect(() => {
    setFailed((current) => ({ ...current, [active.id]: false }));
  }, [active.id]);

  const openFeed = () => window.open(active.url, '_blank', 'noopener,noreferrer');

  return (
    <section className="camera-wall" aria-label="Live venue camera feeds">
      <div className="camera-wall__header">
        <div className="flex items-center gap-2 min-w-0">
          <Video size={15} />
          <div>
            <div className="camera-wall__title">Live venue cameras</div>
            <div className="camera-wall__subtitle">Real footage + simulated crowd telemetry</div>
          </div>
        </div>
        <div className="camera-wall__telemetry">
          <span><b>{people.toLocaleString()}</b> people</span>
          <span><b>{Math.round(density * 100)}%</b> avg density</span>
          <span><b>{flow}</b>/min flow</span>
          <span className={`risk-chip risk-chip--${risk}`}>{risk.toUpperCase()}</span>
        </div>
      </div>

      <div className="camera-wall__body">
        <div className="camera-main">
          {!failed[active.id] ? (
            <video
              ref={videoRef}
              key={active.id}
              className="camera-main__video"
              src={active.url}
              autoPlay
              muted
              loop
              playsInline
              controls
              preload="metadata"
              onError={() => setFailed((current) => ({ ...current, [active.id]: true }))}
            />
          ) : (
            <div className="camera-main__offline">
              <Camera size={28} />
              <strong>Feed unavailable</strong>
              <span>The public video source could not be loaded.</span>
              <button onClick={openFeed}>Open source <ExternalLink size={12} /></button>
            </div>
          )}
          <div className="camera-main__overlay">
            <span className="live-badge"><Circle size={7} fill="currentColor" /> LIVE FEED</span>
            <span>{active.name}</span>
            <span className="ml-auto">DEMO TELEMETRY</span>
          </div>
        </div>

        <div className="camera-feed-list">
          {FEEDS.map((feed) => (
            <button
              key={feed.id}
              onClick={() => setActiveId(feed.id)}
              className={`camera-feed ${active.id === feed.id ? 'camera-feed--active' : ''}`}
            >
              <div className="camera-feed__thumb">
                <video src={feed.url} muted playsInline preload="metadata" aria-hidden="true" />
                <span><Circle size={6} fill="currentColor" /> {active.id === feed.id ? 'SELECTED' : 'CAMERA'}</span>
              </div>
              <div className="camera-feed__meta">
                <strong>{feed.name}</strong>
                <small>{feed.location}</small>
              </div>
            </button>
          ))}
          <div className="camera-source">
            <div className="cmd-label">Footage source</div>
            <div className="flex items-center gap-1 mt-1 text-[10px]">
              <span>{active.source} · {active.license}</span>
              <button onClick={openFeed} title="Open original footage" aria-label="Open original footage">
                <ExternalLink size={11} />
              </button>
            </div>
          </div>
        </div>
      </div>

      <button className="camera-expand" title="Open footage in a new tab" onClick={openFeed}>
        <Maximize2 size={13} />
      </button>
    </section>
  );
}
