'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext, useAgent } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import type { AuthedChild } from '@/components/app/login-view';
import { LoginView } from '@/components/app/login-view';
import { WelcomeView } from '@/components/app/welcome-view';
import type { Escalation } from '@/components/app/welcome-view';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(AgentSessionView_01);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: { opacity: 1, scale: 1 },
    hidden: { opacity: 0, scale: 0.97 },
  },
  initial: 'hidden' as const,
  animate: 'visible' as const,
  exit: 'hidden' as const,
  transition: { duration: 0.4, ease: 'easeInOut' },
};

/* ── Connecting Overlay ────────────────────────────────────── */
function ConnectingOverlay() {
  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-6"
      style={{
        background: 'linear-gradient(150deg, #fff7ed 0%, #fef3c7 40%, #ede9fe 100%)',
      }}
    >
      {/* Spinner */}
      <div
        className="relative flex items-center justify-center"
        style={{ width: 120, height: 120 }}
      >
        <div
          className="animate-spin-slow absolute rounded-full border-4 border-orange-200"
          style={{ width: 120, height: 120, borderTopColor: '#F97316' }}
        />
        <span className="animate-bounce-gentle text-5xl">🐥</span>
      </div>
      <div className="text-center">
        <h2 className="mb-2 text-2xl font-black text-gray-800">Chinnu is getting ready…</h2>
        <p className="font-medium text-gray-500">Connecting you to your learning buddy!</p>
      </div>
      <div className="flex gap-2">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="h-2.5 w-2.5 rounded-full bg-orange-400"
            style={{ animation: `bounce 1s ease-in-out ${i * 0.2}s infinite` }}
          />
        ))}
      </div>
    </div>
  );
}

/* ── Call Ended Screen ─────────────────────────────────────── */
function CallEndedScreen({ onRestart }: { onRestart: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-6 px-4 text-center"
      style={{
        background: 'linear-gradient(150deg, #fff7ed 0%, #fef3c7 40%, #ede9fe 100%)',
      }}
    >
      <span className="animate-bounce-gentle text-8xl">🎉</span>
      <div>
        <h2 className="mb-3 text-3xl font-black text-gray-800">Great job today!</h2>
        <p className="max-w-sm text-lg font-semibold text-gray-600">
          Chinnu had so much fun learning with you. Come back soon! 👋
        </p>
      </div>
      <div className="mt-2 flex flex-col items-center gap-4 sm:flex-row">
        <button
          id="restart-call-btn"
          onClick={onRestart}
          className="flex items-center gap-2 rounded-full px-8 py-4 text-base font-black text-white shadow-xl transition-all duration-200 hover:scale-105 active:scale-95"
          style={{
            background: 'linear-gradient(135deg, #F97316, #EA580C)',
            boxShadow: '0 6px 24px rgba(249,115,22,0.4)',
          }}
        >
          <span className="text-xl">🎙️</span>
          Talk to Chinnu Again!
        </button>
      </div>
      <p className="text-xs font-medium text-gray-400">
        Powered by Murf Falcon TTS · #VoiceForBharat
      </p>
    </div>
  );
}

/* ── Mic Permission Error Screen ───────────────────────────── */
function MicPermissionError({ onRetry }: { onRetry: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-6 px-6 text-center"
      style={{
        background: 'linear-gradient(150deg, #fff7ed 0%, #fef3c7 40%, #ede9fe 100%)',
      }}
    >
      <span className="text-7xl">🎤</span>
      <div className="max-w-sm">
        <h2 className="mb-3 text-2xl font-black text-gray-800">Microphone Access Needed</h2>
        <p className="mb-4 text-base leading-relaxed font-semibold text-gray-600">
          Chinnu needs to hear your child speak! Please allow microphone access so the learning can
          begin. 🐥
        </p>
        {/* Step-by-step instructions */}
        <div
          className="space-y-2 rounded-2xl p-4 text-left text-sm"
          style={{ background: 'rgba(249,115,22,0.08)', border: '1px solid rgba(249,115,22,0.3)' }}
        >
          <p className="mb-2 font-black text-gray-700">How to enable your microphone:</p>
          <p className="font-medium text-gray-600">
            🔒 <strong>Chrome/Edge:</strong> Click the lock icon in the address bar → Microphone →
            Allow
          </p>
          <p className="font-medium text-gray-600">
            🦊 <strong>Firefox:</strong> Click the microphone icon in the address bar → Allow
          </p>
          <p className="font-medium text-gray-600">
            🍎 <strong>Safari:</strong> Settings → Websites → Microphone → Allow
          </p>
        </div>
      </div>
      <button
        id="retry-mic-btn"
        onClick={onRetry}
        className="flex items-center gap-2 rounded-full px-8 py-4 text-base font-black text-white shadow-xl transition-all duration-200 hover:scale-105 active:scale-95"
        style={{
          background: 'linear-gradient(135deg, #F97316, #EA580C)',
          boxShadow: '0 6px 24px rgba(249,115,22,0.4)',
        }}
      >
        Try Again 🔄
      </button>
    </div>
  );
}

/* ── Agent State Banner ─────────────────────────────────────── */
function AgentStateBanner({ agentState }: { agentState: string | undefined }) {
  const stateConfig: Record<string, { text: string; emoji: string; color: string }> = {
    listening: {
      text: 'Chinnu is listening to you!',
      emoji: '👂',
      color: 'linear-gradient(90deg, #34d399, #059669)',
    },
    speaking: {
      text: 'Chinnu is speaking!',
      emoji: '🗣️',
      color: 'linear-gradient(90deg, #F97316, #ea580c)',
    },
    thinking: {
      text: 'Chinnu is thinking…',
      emoji: '🤔',
      color: 'linear-gradient(90deg, #7C3AED, #6d28d9)',
    },
  };

  const config = agentState ? stateConfig[agentState] : null;

  if (!config) return null;

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={agentState}
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
        className="fixed top-20 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-full px-5 py-2 text-sm font-bold text-white shadow-lg"
        style={{ background: config.color }}
      >
        <span className="text-base">{config.emoji}</span>
        {config.text}
      </motion.div>
    </AnimatePresence>
  );
}

/* ── Main ViewController ───────────────────────────────────── */
interface ViewControllerProps {
  appConfig: AppConfig;
}

// 'auth' is the gate before welcome — requires login/signup
type AppView = 'auth' | 'welcome' | 'connecting' | 'session' | 'ended';

// ── Escalation polling hook ───────────────────────────────────────────────────
// Polls GET /api/escalations every 30 seconds while the parent is on the
// welcome view. child_id is NOT supplied by the browser; it comes from the
// signed JWT session cookie that the API verifies server-side.
function useEscalations(active: boolean): Escalation[] {
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchEscalations = useCallback(async () => {
    try {
      const res = await fetch('/api/escalations');
      if (res.ok) {
        const data = await res.json();
        setEscalations(data.escalations ?? []);
      }
    } catch {
      // Network error — keep showing last known state
    }
  }, []);

  useEffect(() => {
    if (!active) {
      // Stop polling when not on welcome view
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Fetch immediately on activation
    fetchEscalations();

    // Then poll every 30 seconds
    intervalRef.current = setInterval(fetchEscalations, 30_000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [active, fetchEscalations]);

  return escalations;
}


export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, start, end } = useSessionContext();
  const { state: agentState } = useAgent();
  const [view, setView] = useState<AppView>('auth');
  const [micError, setMicError] = useState(false);
  const [authedChild, setAuthedChild] = useState<AuthedChild | null>(null);

  // Poll escalations only while the parent dashboard (welcome view) is visible
  const escalations = useEscalations(view === 'welcome' && !isConnected);

  // ── Check existing session on mount ────────────────────────────────────
  useEffect(() => {
    fetch('/api/auth/me')
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.authenticated) {
          setAuthedChild({ child_id: data.child_id, name: data.name });
          setView('welcome');
        }
      })
      .catch(() => {
        // No valid session — stay on 'auth'
      });
  }, []);

  // ── Sync connection state → view ────────────────────────────────────────
  useEffect(() => {
    if (isConnected) {
      setView('session');
      setMicError(false);
    } else if (view === 'session') {
      setView('ended');
    }
  }, [isConnected, view]);

  // ── Handlers ────────────────────────────────────────────────────────────
  const handleAuthenticated = (child: AuthedChild) => {
    setAuthedChild(child);
    setView('welcome');
  };

  const handleStartCall = async () => {
    setView('connecting');
    setMicError(false);
    try {
      await navigator.mediaDevices.getUserMedia({ audio: true });
      await start();
    } catch (err: unknown) {
      const error = err as Error;
      if (
        error.name === 'NotAllowedError' ||
        error.name === 'PermissionDeniedError' ||
        error.message?.toLowerCase().includes('permission')
      ) {
        setMicError(true);
        setView('welcome');
      } else {
        try {
          await start();
        } catch {
          setView('welcome');
        }
      }
    }
  };

  const handleEndCall = () => {
    end();
    setView('ended');
  };

  const handleRestart = () => {
    setView('welcome');
    setMicError(false);
  };

  const handleRetryMic = () => {
    setMicError(false);
    handleStartCall();
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/auth', { method: 'DELETE' });
    } catch {
      // ignore
    }
    setAuthedChild(null);
    setView('auth');
  };

  // ── Mic error screen ─────────────────────────────────────────────────────
  if (micError) {
    return <MicPermissionError onRetry={handleRetryMic} />;
  }

  // ── Auth gate ─────────────────────────────────────────────────────────────
  if (view === 'auth') {
    return <LoginView onAuthenticated={handleAuthenticated} />;
  }

  // ── Connecting overlay ────────────────────────────────────────────────────
  if (view === 'connecting' && !isConnected) {
    return <ConnectingOverlay />;
  }

  // ── Call ended screen ─────────────────────────────────────────────────────
  if (view === 'ended') {
    return <CallEndedScreen onRestart={handleRestart} />;
  }

  return (
    <AnimatePresence mode="wait">
      {/* ── Welcome / Landing Page ── */}
      {view === 'welcome' && !isConnected && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          startButtonText={appConfig.startButtonText}
          childName={authedChild?.name}
          onStartCall={handleStartCall}
          onLogout={handleLogout}
          escalations={escalations}
        />
      )}

      {/* ── Active Session ── */}
      {view === 'session' && isConnected && (
        <motion.div key="session" className="fixed inset-0 z-10" {...VIEW_MOTION_PROPS}>
          {/* Agent state banner: Listening / Speaking / Thinking */}
          <AgentStateBanner agentState={agentState} />

          <MotionSessionView
            key="session-view"
            {...VIEW_MOTION_PROPS}
            supportsChatInput={appConfig.supportsChatInput}
            supportsVideoInput={appConfig.supportsVideoInput}
            supportsScreenShare={appConfig.supportsScreenShare}
            isPreConnectBufferEnabled={appConfig.isPreConnectBufferEnabled}
            audioVisualizerType={appConfig.audioVisualizerType}
            audioVisualizerColor={appConfig.audioVisualizerColor}
            audioVisualizerColorShift={appConfig.audioVisualizerColorShift}
            audioVisualizerBarCount={appConfig.audioVisualizerBarCount}
            audioVisualizerGridRowCount={appConfig.audioVisualizerGridRowCount}
            audioVisualizerGridColumnCount={appConfig.audioVisualizerGridColumnCount}
            audioVisualizerRadialBarCount={appConfig.audioVisualizerRadialBarCount}
            audioVisualizerRadialRadius={appConfig.audioVisualizerRadialRadius}
            audioVisualizerWaveLineWidth={appConfig.audioVisualizerWaveLineWidth}
            preConnectMessage="Chinnu is ready to play! Say something… 🐥"
            className="fixed inset-0"
          />

          {/* End call button overlay */}
          <div className="fixed right-6 bottom-32 z-50">
            <button
              id="end-call-btn"
              onClick={handleEndCall}
              className="flex items-center gap-2 rounded-full px-5 py-3 text-sm font-black text-white shadow-lg transition-all hover:scale-105 active:scale-95"
              style={{ background: 'linear-gradient(135deg, #dc2626, #b91c1c)' }}
            >
              👋 End Call
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
