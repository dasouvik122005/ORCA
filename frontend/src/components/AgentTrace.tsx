import type { AgentTrace as AgentTraceType } from '../types';

interface AgentTraceProps {
  traces: AgentTraceType[];
}

const AGENT_ICONS: Record<string, string> = {
  'Orchestrator Agent': '🧠',
  'Weather Intelligence Agent': '🌦',
  'Ocean Intelligence Agent': '🌊',
  'PFZ Discovery Agent': '🐟',
  'Geospatial Intelligence Agent': '📍',
  'Risk Assessment Agent': '⚠️',
  'Explainability & Response Agent': '💡',
  'Safe Route Planning Agent': '🧭',
};

const STATUS_CONFIG = {
  pending: { color: '#4a5a8a', bg: '#4a5a8a15', label: '⏸ Pending' },
  running: { color: '#3498db', bg: '#3498db15', label: '⏳ Running' },
  completed: { color: '#2ecc71', bg: '#2ecc7115', label: '✅ Done' },
  error: { color: '#e74c3c', bg: '#e74c3c15', label: '❌ Error' },
};

export function AgentTrace({ traces }: AgentTraceProps) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-base">🧠</span>
        <h3 className="text-xs font-semibold text-teal-accent uppercase tracking-wider">
          ORCA's Reasoning Trace
        </h3>
      </div>

      <div className="space-y-1 trace-connector">
        {traces.map((trace, i) => {
          const icon = AGENT_ICONS[trace.agent_name] || '🔧';
          const status = STATUS_CONFIG[trace.status] || STATUS_CONFIG.pending;

          return (
            <div
              key={i}
              className="relative pl-9 py-2 animate-slide-up"
              style={{ animationDelay: `${i * 80}ms` }}
            >
              {/* Node dot */}
              <div
                className="absolute left-[11px] top-[12px] w-[12px] h-[12px] rounded-full border-2 z-10"
                style={{
                  borderColor: status.color,
                  backgroundColor: trace.status === 'completed' ? status.color : 'transparent',
                }}
              />

              <div
                className="rounded-lg px-3 py-2 border transition-all"
                style={{
                  backgroundColor: status.bg,
                  borderColor: status.color + '30',
                }}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-slate-300">
                    {icon} {trace.agent_name}
                  </span>
                  <span className="text-[10px]" style={{ color: status.color }}>
                    {status.label}
                  </span>
                </div>
                <p className="text-[11px] text-ocean-400 leading-relaxed">
                  {trace.message}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
