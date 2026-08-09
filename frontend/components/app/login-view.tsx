'use client';

import { useState } from 'react';

/* ── Types ──────────────────────────────────────────────────────────────── */
export type AuthedChild = {
  child_id: string;
  name: string;
};

interface LoginViewProps {
  onAuthenticated: (child: AuthedChild) => void;
}

/* ── Sub-components ─────────────────────────────────────────────────────── */
function InputField({
  id,
  label,
  type,
  value,
  onChange,
  placeholder,
  disabled,
}: {
  id: string;
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  disabled?: boolean;
}) {
  return (
    <div className="flex w-full flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-bold text-gray-700">
        {label}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full rounded-2xl border-2 border-orange-200 bg-white px-4 py-3 text-sm font-semibold text-gray-800 transition-all duration-200 placeholder:text-gray-400 focus:border-orange-400 focus:ring-2 focus:ring-orange-100 focus:outline-none disabled:opacity-60"
      />
    </div>
  );
}

function SubmitButton({
  label,
  loading,
  loadingLabel,
}: {
  label: string;
  loading: boolean;
  loadingLabel: string;
}) {
  return (
    <button
      type="submit"
      disabled={loading}
      className="w-full rounded-full py-4 text-base font-black text-white shadow-xl transition-all duration-200 hover:scale-105 active:scale-95 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:scale-100"
      style={{
        background: 'linear-gradient(135deg, #F97316 0%, #EA580C 60%, #C2410C 100%)',
        boxShadow: '0 8px 32px rgba(249,115,22,0.4)',
      }}
    >
      {loading ? (
        <span className="flex items-center justify-center gap-2">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          {loadingLabel}
        </span>
      ) : (
        label
      )}
    </button>
  );
}

/* ── Auth Form ──────────────────────────────────────────────────────────── */
function AuthForm({ onAuthenticated }: LoginViewProps) {
  const [tab, setTab] = useState<'login' | 'signup'>('login');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!name.trim() || !password.trim()) {
      setError('Please enter both name and password.');
      return;
    }
    if (tab === 'signup' && password.length < 4) {
      setError('Password must be at least 4 characters.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch('/api/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: tab, name: name.trim(), password }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error ?? 'Something went wrong. Please try again.');
        return;
      }

      onAuthenticated({ child_id: data.child_id, name: data.name });
    } catch {
      setError('Could not connect to server. Please check your internet connection.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="w-full max-w-sm rounded-3xl border border-white/60 p-8 shadow-2xl backdrop-blur-sm"
      style={{ background: 'rgba(255,255,255,0.92)' }}
    >
      {/* Tabs */}
      <div className="mb-6 flex overflow-hidden rounded-2xl border-2 border-orange-100">
        {(['login', 'signup'] as const).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => {
              setTab(t);
              setError('');
            }}
            className="flex-1 py-2.5 text-sm font-black transition-all duration-200"
            style={
              tab === t
                ? {
                    background: 'linear-gradient(135deg, #F97316, #EA580C)',
                    color: 'white',
                  }
                : { color: '#9a6500' }
            }
          >
            {t === 'login' ? '👋 Log In' : '✨ Sign Up'}
          </button>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <InputField
          id="child-name"
          label="Child's Name"
          type="text"
          value={name}
          onChange={setName}
          placeholder="e.g. Arjun"
          disabled={loading}
        />
        <InputField
          id="child-password"
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          placeholder={tab === 'signup' ? 'Create a password' : 'Enter password'}
          disabled={loading}
        />

        {/* Error message */}
        {error && (
          <div
            className="rounded-xl px-4 py-3 text-sm font-semibold text-red-700"
            style={{ background: 'rgba(254,202,202,0.7)', border: '1px solid rgba(239,68,68,0.3)' }}
          >
            {error}
          </div>
        )}

        <SubmitButton
          label={tab === 'login' ? "🎙️ Let's Learn!" : '🐥 Create Account'}
          loading={loading}
          loadingLabel={tab === 'login' ? 'Logging in…' : 'Creating account…'}
        />
      </form>

      {tab === 'signup' && (
        <p className="mt-4 text-center text-xs font-medium text-gray-400">
          Each child gets their own private account. Passwords are stored securely.
        </p>
      )}
    </div>
  );
}

/* ── Main Login View ─────────────────────────────────────────────────────── */
export function LoginView({ onAuthenticated }: LoginViewProps) {
  return (
    <div
      className="fixed inset-0 flex flex-col items-center justify-center gap-6 overflow-y-auto px-4 py-8"
      style={{
        background: 'linear-gradient(150deg, #fff7ed 0%, #fef3c7 30%, #ede9fe 65%, #f0f9ff 100%)',
      }}
    >
      {/* Character + title */}
      <div className="flex flex-col items-center gap-3 text-center">
        <div
          className="flex items-center justify-center rounded-full shadow-xl"
          style={{
            width: 88,
            height: 88,
            background: 'linear-gradient(135deg, #FDE68A, #F97316)',
            fontSize: 52,
          }}
        >
          🐥
        </div>
        <div>
          <h1
            className="text-3xl font-black"
            style={{
              background: 'linear-gradient(135deg, #F97316, #7C3AED)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            BoloBuddy
          </h1>
          <p className="mt-1 text-sm font-semibold text-gray-500">
            Sign in or create your child&apos;s account
          </p>
        </div>
      </div>

      {/* Form card */}
      <AuthForm onAuthenticated={onAuthenticated} />

      {/* Footer note */}
      <p className="max-w-xs text-center text-xs font-medium text-gray-400">
        Each child has a private account with their own learning memory. Two children in the same
        family can have separate accounts! 👨‍👩‍👧‍👦
      </p>
    </div>
  );
}
