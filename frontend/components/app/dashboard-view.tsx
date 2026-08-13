'use client';

import { useEffect, useState } from 'react';

/* -- Types ------------------------------------------------------------------ */
interface AnalyticsData {
  total_calls: number;
  successful_calls: number;
  failed_calls: number;
}

/* -- Metric Card ------------------------------------------------------------ */
function MetricCard({
  label,
  value,
  emoji,
  gradient,
}: {
  label: string;
  value: number | string;
  emoji: string;
  gradient: string;
}) {
  return (
    <div
      className="flex flex-col items-center gap-3 rounded-3xl p-6 shadow-xl"
      style={{ background: gradient }}
    >
      <span className="text-4xl">{emoji}</span>
      <span
        className="text-5xl font-black"
        style={{ color: '#1e293b' }}
      >
        {value}
      </span>
      <span className="text-sm font-bold tracking-wide text-gray-600 uppercase">
        {label}
      </span>
    </div>
  );
}

/* -- Spinner ---------------------------------------------------------------- */
function Spinner() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16">
      <div
        className="h-14 w-14 animate-spin rounded-full border-4 border-orange-200"
        style={{ borderTopColor: '#F97316' }}
      />
      <p className="font-semibold text-gray-500">Loading analytics…</p>
    </div>
  );
}

/* -- Main DashboardView ----------------------------------------------------- */
interface DashboardViewProps {
  onBack: () => void;
}

export function DashboardView({ onBack }: DashboardViewProps) {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchAnalytics = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/analytics', { cache: 'no-store' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setError(body?.error ?? 'Failed to load analytics.');
        return;
      }
      const json = await res.json();
      setData(json);
    } catch {
      setError('Could not reach the server. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, []);

  return (
    <div
      className="min-h-screen w-full overflow-x-hidden overflow-y-auto"
      style={{
        background: 'linear-gradient(150deg, #fff7ed 0%, #fef3c7 30%, #ede9fe 65%, #f0f9ff 100%)',
      }}
    >
      {/* Header */}
      <div className="relative flex w-full items-center justify-between px-6 pt-8 pb-2">
        <button
          id="dashboard-back-btn"
          onClick={onBack}
          className="flex items-center gap-2 rounded-full bg-white/60 px-4 py-2 text-sm font-bold text-gray-700 shadow-sm backdrop-blur-md transition-all hover:bg-white/80 hover:shadow-md active:scale-95"
        >
          ← Back
        </button>

        {/* Refresh button */}
        {!loading && (
          <button
            id="dashboard-refresh-btn"
            onClick={fetchAnalytics}
            className="flex items-center gap-2 rounded-full bg-white/60 px-4 py-2 text-sm font-bold text-gray-700 shadow-sm backdrop-blur-md transition-all hover:bg-white/80 hover:shadow-md active:scale-95"
          >
            🔄 Refresh
          </button>
        )}
      </div>

      {/* Title */}
      <div className="flex flex-col items-center gap-2 px-4 pt-6 pb-10 text-center">
        <div
          className="mb-2 flex items-center justify-center rounded-full shadow-xl"
          style={{
            width: 72,
            height: 72,
            background: 'linear-gradient(135deg, #FDE68A, #F97316)',
            fontSize: 40,
          }}
        >
          📊
        </div>
        <h1
          className="text-4xl font-black"
          style={{
            background: 'linear-gradient(135deg, #F97316, #7C3AED)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
          }}
        >
          Chinnu Analytics
        </h1>
        <p className="max-w-xs text-sm font-semibold text-gray-500">
          Call performance for this child's account
        </p>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-2xl px-4 pb-20">
        {loading && <Spinner />}

        {!loading && error && (
          <div
            className="rounded-2xl px-6 py-4 text-center text-sm font-semibold text-red-700"
            style={{ background: 'rgba(254,202,202,0.7)', border: '1px solid rgba(239,68,68,0.3)' }}
          >
            {error}
          </div>
        )}

        {!loading && !error && data && (
          <>
            {/* Success definition note */}
            <div
              className="mb-8 rounded-2xl px-5 py-4 text-center text-sm font-semibold text-gray-600"
              style={{ background: 'rgba(249,115,22,0.08)', border: '1px solid rgba(249,115,22,0.2)' }}
            >
              ✅ A call is <strong>successful</strong> when the child learns at least{' '}
              <strong>2 unique words</strong> in one session.
            </div>

            {/* Metric cards */}
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
              <MetricCard
                label="Total Calls"
                value={data.total_calls}
                emoji="📞"
                gradient="linear-gradient(135deg, #fff7ed, #fed7aa)"
              />
              <MetricCard
                label="Successful Calls"
                value={data.successful_calls}
                emoji="🎉"
                gradient="linear-gradient(135deg, #ecfdf5, #a7f3d0)"
              />
              <MetricCard
                label="Failed Calls"
                value={data.failed_calls}
                emoji="📖"
                gradient="linear-gradient(135deg, #ede9fe, #ddd6fe)"
              />
            </div>

            {/* Empty state */}
            {data.total_calls === 0 && (
              <div className="mt-10 flex flex-col items-center gap-3 text-center">
                <span className="text-5xl">🐥</span>
                <p className="text-lg font-bold text-gray-600">No calls yet!</p>
                <p className="max-w-xs text-sm font-medium text-gray-400">
                  Start a conversation with Chinnu and come back to see your progress.
                </p>
              </div>
            )}
          </>
        )}
      </div>

      {/* Footer */}
      <div className="flex w-full justify-center pb-8">
        <p className="text-xs font-medium text-gray-400">
          Powered by Murf Falcon TTS · BoloBuddy Day 8
        </p>
      </div>
    </div>
  );
}
