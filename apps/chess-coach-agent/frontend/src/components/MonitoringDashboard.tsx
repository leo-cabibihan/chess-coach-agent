import { useEffect, useMemo, useState } from 'react';
import { BarChart3, RefreshCw } from 'lucide-react';
import { getMonitoring } from '../lib/api';
import type { MonitoringSummary } from '../lib/types';

export function MonitoringDashboard({ refreshKey }: { refreshKey: number }) {
  const [summary, setSummary] = useState<MonitoringSummary | null>(null);
  const [loading, setLoading] = useState(false);

  function refresh() {
    setLoading(true);
    getMonitoring().then(setSummary).catch(() => setSummary(null)).finally(() => setLoading(false));
  }

  useEffect(refresh, [refreshKey]);

  const eventRows = useMemo(() => {
    if (!summary) return [];
    const entries = Object.entries(summary.event_counts).sort((a, b) => b[1] - a[1]);
    const maximum = Math.max(...entries.map(([, count]) => count), 1);
    return entries.map(([name, count]) => ({ name, count, width: `${Math.max(8, count / maximum * 100)}%` }));
  }, [summary]);

  return (
    <section className="monitoring-panel">
      <div className="monitoring-head">
        <div className="panel-title"><BarChart3 size={18} /> Quality monitoring</div>
        <button aria-label="Refresh monitoring" title="Refresh monitoring" onClick={refresh} disabled={loading}>
          <RefreshCw className={loading ? 'spin' : ''} size={17} />
        </button>
      </div>
      {!summary ? (
        <p className="monitoring-empty">Monitoring data will appear after an analysis or practice attempt.</p>
      ) : (
        <>
          <div className="monitoring-metrics">
            <div><strong>{summary.total_events}</strong><span>Events</span></div>
            <div><strong>{summary.event_counts.analysis_completed || 0}</strong><span>Analyses</span></div>
            <div><strong>{summary.feedback_count}</strong><span>Ratings</span></div>
            <div>
              <strong>{summary.helpful_rate === null ? 'N/A' : `${Math.round(summary.helpful_rate * 100)}%`}</strong>
              <span>Helpful</span>
            </div>
            <div><strong>{summary.input_tokens + summary.output_tokens}</strong><span>Tokens</span></div>
            <div><strong>${summary.estimated_cost_usd.toFixed(4)}</strong><span>Est. cost</span></div>
            <div>
              <strong>{summary.average_chat_latency_ms === null ? 'N/A' : `${Math.round(summary.average_chat_latency_ms)} ms`}</strong>
              <span>Chat latency</span>
            </div>
            <div><strong>{summary.llm_calls}</strong><span>LLM calls</span></div>
            <div><strong>{summary.quiz_attempts}</strong><span>Quiz attempts</span></div>
            <div>
              <strong>{summary.quiz_accuracy === null ? 'N/A' : `${Math.round(summary.quiz_accuracy * 100)}%`}</strong>
              <span>Quiz accuracy</span>
            </div>
            <div>
              <strong>{summary.hint_use_rate === null ? 'N/A' : `${Math.round(summary.hint_use_rate * 100)}%`}</strong>
              <span>Hint use</span>
            </div>
            <div>
              <strong>{summary.practice_agent_runs ?? 0}</strong>
              <span>Practice agent runs</span>
            </div>
            <div>
              <strong>
                {summary.practice_agent_fallback_rate === null
                  ? 'N/A'
                  : `${Math.round(summary.practice_agent_fallback_rate * 100)}%`}
              </strong>
              <span>Agent fallback</span>
            </div>
            <div><strong>{summary.stream_failures}</strong><span>Stream failures</span></div>
          </div>
          <div className="event-bars">
            {eventRows.map((row) => (
              <div className="event-row" key={row.name}>
                <span>{row.name.replace(/_/g, ' ')}</span>
                <div><i style={{ width: row.width }} /></div>
                <strong>{row.count}</strong>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
