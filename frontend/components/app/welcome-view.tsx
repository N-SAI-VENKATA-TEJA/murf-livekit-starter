'use client';

import { Button } from '@/components/ui/button';

/* ── Floating bubble decorations ──────────────────────────── */
function Bubble({
  size,
  color,
  top,
  left,
  delay,
  label,
}: {
  size: number;
  color: string;
  top: string;
  left: string;
  delay: string;
  label: string;
}) {
  return (
    <div
      className="absolute flex items-center justify-center rounded-full font-black text-white shadow-lg select-none pointer-events-none animate-float"
      style={{
        width: size,
        height: size,
        background: color,
        top,
        left,
        animationDelay: delay,
        fontSize: size * 0.38,
        zIndex: 0,
        opacity: 0.85,
      }}
    >
      {label}
    </div>
  );
}

/* ── Floating word bubbles ────────────────────────────────── */
function WordBubble({
  word,
  top,
  left,
  delay,
  bg,
}: {
  word: string;
  top: string;
  left: string;
  delay: string;
  bg: string;
}) {
  return (
    <div
      className="absolute rounded-full px-3 py-1.5 text-xs font-bold text-white shadow-md select-none pointer-events-none animate-float-delayed"
      style={{ top, left, background: bg, animationDelay: delay, zIndex: 0, opacity: 0.9 }}
    >
      {word}
    </div>
  );
}

/* ── Chinnu Character SVG ──────────────────────────────────── */
function ChinnuCharacter() {
  return (
    <div className="relative flex items-center justify-center animate-bounce-gentle" style={{ width: 200, height: 200 }}>
      {/* Glow behind character */}
      <div
        className="absolute rounded-full blur-2xl"
        style={{
          width: 180,
          height: 180,
          background: 'radial-gradient(circle, rgba(253,230,138,0.7) 0%, rgba(249,115,22,0.3) 60%, transparent 100%)',
        }}
      />
      <svg
        viewBox="0 0 200 200"
        width="200"
        height="200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ position: 'relative', zIndex: 1 }}
      >
        {/* Body */}
        <ellipse cx="100" cy="130" rx="52" ry="44" fill="#FDE68A" />
        {/* Head */}
        <circle cx="100" cy="82" r="46" fill="#FDE68A" />
        {/* Cheeks */}
        <circle cx="76" cy="94" r="12" fill="#F97316" opacity="0.4" />
        <circle cx="124" cy="94" r="12" fill="#F97316" opacity="0.4" />
        {/* Eyes */}
        <circle cx="86" cy="78" r="9" fill="white" />
        <circle cx="114" cy="78" r="9" fill="white" />
        <circle cx="88" cy="80" r="5" fill="#1e293b" />
        <circle cx="116" cy="80" r="5" fill="#1e293b" />
        {/* Eye shine */}
        <circle cx="90" cy="77" r="2" fill="white" />
        <circle cx="118" cy="77" r="2" fill="white" />
        {/* Beak */}
        <path d="M90 96 Q100 108 110 96 Q100 100 90 96Z" fill="#F97316" />
        {/* Smile */}
        <path d="M85 100 Q100 114 115 100" stroke="#F97316" strokeWidth="2.5" strokeLinecap="round" fill="none" />
        {/* Ears / tufts */}
        <ellipse cx="60" cy="50" rx="10" ry="16" fill="#FDE68A" transform="rotate(-20 60 50)" />
        <ellipse cx="140" cy="50" rx="10" ry="16" fill="#FDE68A" transform="rotate(20 140 50)" />
        {/* Wings */}
        <ellipse cx="52" cy="128" rx="18" ry="26" fill="#FCD34D" transform="rotate(-20 52 128)" />
        <ellipse cx="148" cy="128" rx="18" ry="26" fill="#FCD34D" transform="rotate(20 148 128)" />
        {/* Feet */}
        <ellipse cx="82" cy="172" rx="16" ry="7" fill="#F97316" />
        <ellipse cx="118" cy="172" rx="16" ry="7" fill="#F97316" />
        {/* Headphones */}
        <path d="M56 82 Q56 44 100 44 Q144 44 144 82" stroke="#7C3AED" strokeWidth="6" strokeLinecap="round" fill="none" />
        <rect x="46" y="78" width="18" height="22" rx="9" fill="#7C3AED" />
        <rect x="136" y="78" width="18" height="22" rx="9" fill="#7C3AED" />
      </svg>
    </div>
  );
}

/* ── Feature Card ──────────────────────────────────────────── */
function FeatureCard({
  emoji,
  title,
  desc,
  color,
  animClass,
}: {
  emoji: string;
  title: string;
  desc: string;
  color: string;
  animClass: string;
}) {
  return (
    <div
      className={`relative flex flex-col items-center text-center gap-3 rounded-3xl p-6 shadow-lg border border-white/60 backdrop-blur-sm ${animClass}`}
      style={{ background: color }}
    >
      <span className="text-4xl">{emoji}</span>
      <h3 className="text-base font-black text-gray-800">{title}</h3>
      <p className="text-sm text-gray-600 font-medium leading-relaxed">{desc}</p>
    </div>
  );
}

/* ── Language Badge ─────────────────────────────────────────── */
function LangBadge({ flag, lang, color }: { flag: string; lang: string; color: string }) {
  return (
    <div
      className="flex items-center gap-2 rounded-full px-4 py-2 font-bold text-white text-sm shadow-md"
      style={{ background: color }}
    >
      <span className="text-lg">{flag}</span>
      {lang}
    </div>
  );
}

/* ── Pulsing CTA Button ─────────────────────────────────────── */
function PulsingButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <div className="relative flex items-center justify-center">
      {/* Ripple rings */}
      <div
        className="absolute rounded-full animate-pulse-ring"
        style={{ width: 220, height: 220, background: 'rgba(249,115,22,0.25)', zIndex: 0 }}
      />
      <div
        className="absolute rounded-full animate-pulse-ring"
        style={{
          width: 220,
          height: 220,
          background: 'rgba(249,115,22,0.15)',
          zIndex: 0,
          animationDelay: '0.5s',
        }}
      />
      <button
        id="start-call-btn"
        onClick={onClick}
        className="relative z-10 flex items-center gap-3 rounded-full px-10 py-5 text-lg font-black text-white shadow-2xl transition-all duration-300 hover:scale-105 hover:shadow-orange-400/50 active:scale-95"
        style={{
          background: 'linear-gradient(135deg, #F97316 0%, #EA580C 60%, #C2410C 100%)',
          boxShadow: '0 8px 32px rgba(249,115,22,0.45)',
        }}
      >
        <span className="text-2xl">🎙️</span>
        {label}
      </button>
    </div>
  );
}

/* ── Main Welcome View ─────────────────────────────────────── */
interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref} className="w-full min-h-screen overflow-y-auto overflow-x-hidden">

      {/* ── HERO SECTION ──────────────────────────────────────── */}
      <section
        className="relative w-full min-h-screen flex flex-col items-center justify-center overflow-hidden pt-20 pb-16 px-4"
        style={{
          background: 'linear-gradient(150deg, #fff7ed 0%, #fef3c7 30%, #ede9fe 65%, #f0f9ff 100%)',
        }}
      >
        {/* Floating bubbles */}
        <Bubble size={64}  color="#F97316" top="8%"   left="5%"  delay="0s"    label="A" />
        <Bubble size={52}  color="#7C3AED" top="12%"  left="88%" delay="0.8s"  label="B" />
        <Bubble size={44}  color="#34D399" top="35%"  left="3%"  delay="1.4s"  label="3" />
        <Bubble size={58}  color="#F472B6" top="72%"  left="6%"  delay="0.4s"  label="🐶" />
        <Bubble size={48}  color="#60A5FA" top="78%"  left="90%" delay="1.1s"  label="🍎" />
        <Bubble size={40}  color="#FBBF24" top="55%"  left="93%" delay="0.6s"  label="C" />

        {/* Floating words */}
        <WordBubble word="🍎 Apple"    top="20%"  left="78%" delay="0.3s"  bg="#F97316" />
        <WordBubble word="🐘 Elephant" top="64%"  left="74%" delay="1.2s"  bg="#7C3AED" />
        <WordBubble word="🌈 Colors"   top="30%"  left="12%" delay="0.9s"  bg="#34D399" />
        <WordBubble word="🔢 Numbers"  top="82%"  left="18%" delay="1.6s"  bg="#F472B6" />

        {/* Hero content */}
        <div className="relative z-10 flex flex-col items-center text-center gap-6 max-w-2xl">
          <div
            className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-bold tracking-widest uppercase animate-slide-up"
            style={{ background: 'rgba(249,115,22,0.12)', color: '#EA580C' }}
          >
            🏆 Fastest TTS · Murf Falcon Powered
          </div>

          <ChinnuCharacter />

          <h1
            className="text-5xl md:text-6xl font-black leading-tight animate-slide-up-1"
            style={{ color: '#1e293b' }}
          >
            Meet{' '}
            <span
              style={{
                background: 'linear-gradient(135deg, #F97316, #7C3AED)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
              }}
            >
              Chinnu!
            </span>
          </h1>

          <p className="text-lg md:text-xl font-semibold text-gray-600 max-w-md leading-relaxed animate-slide-up-2">
            Your child's friendly voice buddy who makes learning new words{' '}
            <span style={{ color: '#F97316' }}>fun, safe, and magical</span> ✨
          </p>

          {/* Language badges */}
          <div className="flex flex-wrap items-center justify-center gap-3 animate-slide-up-3">
            <LangBadge flag="🇮🇳" lang="Telugu"  color="#F97316" />
            <LangBadge flag="🇬🇧" lang="English"  color="#7C3AED" />
            <LangBadge flag="🇮🇳" lang="Hindi"    color="#34D399" />
            <LangBadge flag="🔀"  lang="Mix it up!" color="#F472B6" />
          </div>

          {/* CTA */}
          <div className="animate-slide-up-4 mt-2">
            <PulsingButton onClick={onStartCall} label={startButtonText} />
          </div>

          <p className="text-xs text-gray-400 font-medium animate-slide-up-4">
            Free to use · No signup needed · Works on any device
          </p>
        </div>
      </section>

      {/* ── HOW IT WORKS SECTION ─────────────────────────────── */}
      <section className="w-full py-20 px-4" style={{ background: 'white' }}>
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-black text-gray-800 mb-3">
              How BoloBuddy Works
            </h2>
            <p className="text-gray-500 font-medium text-lg">
              Three simple steps to get your child learning!
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <FeatureCard
              emoji="👆"
              title="1. Tap to Start"
              desc="Press the big orange button. Chinnu will say hello and ask your child's name!"
              color="linear-gradient(135deg, #fff7ed, #fed7aa)"
              animClass="animate-slide-up-1"
            />
            <FeatureCard
              emoji="🗣️"
              title="2. Talk Freely"
              desc="Speak in Telugu, English, Hindi, or mix them! Chinnu understands and always replies in the same language."
              color="linear-gradient(135deg, #ede9fe, #ddd6fe)"
              animClass="animate-slide-up-2"
            />
            <FeatureCard
              emoji="🎉"
              title="3. Learn Together"
              desc="Chinnu plays games, teaches words, and celebrates every single attempt — no matter right or wrong!"
              color="linear-gradient(135deg, #ecfdf5, #a7f3d0)"
              animClass="animate-slide-up-3"
            />
          </div>
        </div>
      </section>

      {/* ── FEATURES SECTION ──────────────────────────────────── */}
      <section
        className="w-full py-20 px-4"
        style={{ background: 'linear-gradient(180deg, #fff7ed 0%, #ede9fe 100%)' }}
      >
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-black text-gray-800 mb-3">
              What Chinnu Can Teach 📚
            </h2>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { e: '🐘', t: 'Animals' },
              { e: '🍎', t: 'Fruits' },
              { e: '🌈', t: 'Colors' },
              { e: '🔢', t: 'Numbers' },
              { e: '🐦', t: 'Birds' },
              { e: '🏠', t: 'Objects' },
              { e: '👋', t: 'Greetings' },
              { e: '👨‍👩‍👧', t: 'Family' },
            ].map((item) => (
              <div
                key={item.t}
                className="flex flex-col items-center gap-2 rounded-2xl p-4 bg-white shadow-md border border-orange-100 hover:scale-105 transition-transform duration-200"
              >
                <span className="text-3xl">{item.e}</span>
                <span className="text-sm font-bold text-gray-700">{item.t}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── READY CTA SECTION ───────────────────────────────────── */}
      <section
        className="w-full py-20 px-4 flex flex-col items-center text-center gap-8"
        style={{
          background: 'linear-gradient(135deg, #1e1b4b 0%, #4c1d95 50%, #7c2d12 100%)',
        }}
      >
        <h2 className="text-3xl md:text-4xl font-black text-white leading-tight max-w-lg">
          Ready to start your child's language journey? 🚀
        </h2>
        <p className="text-purple-200 font-semibold text-lg max-w-md">
          Chinnu is waiting! Just tap below and let the learning begin.
        </p>

        <PulsingButton onClick={onStartCall} label={startButtonText} />

        <div className="flex flex-col items-center gap-1 pt-4 border-t border-white/10 w-full max-w-sm">
          <p className="text-purple-300 text-xs font-medium">
            Voice AI powered by{' '}
            <a
              href="https://murf.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="underline text-orange-300 hover:text-orange-200"
            >
              Murf Falcon TTS
            </a>{' '}
            — the fastest TTS API
          </p>
          <p className="text-purple-400 text-xs">
            #VoiceForBharat · 10 Days of Voice Agents
          </p>
        </div>
      </section>
    </div>
  );
};
