export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorDark?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;

  // agent dispatch configuration
  agentName?: string;

  // LiveKit Cloud Sandbox configuration
  sandboxId?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'BoloBuddy',
  pageTitle: 'BoloBuddy — Learn Words with Chinnu!',
  pageDescription:
    'BoloBuddy helps children aged 2–6 learn language naturally through fun voice conversations with Chinnu, their AI companion. Powered by Murf Falcon TTS.',

  supportsChatInput: false,
  supportsVideoInput: false,
  supportsScreenShare: false,
  isPreConnectBufferEnabled: true,

  logo: '/murf-logo.svg',
  accent: '#F97316',
  logoDark: '/murf-logo-dark.svg',
  accentDark: '#fb923c',
  startButtonText: 'Talk to Chinnu! 🎙️',

  // BoloBuddy uses the aura visualizer — it looks magical for children
  audioVisualizerType: 'aura',
  audioVisualizerColor: '#F97316',
  audioVisualizerColorDark: '#fb923c',
  audioVisualizerColorShift: 0.4,

  // agent dispatch configuration
  agentName: process.env.AGENT_NAME ?? undefined,

  // LiveKit Cloud Sandbox configuration
  sandboxId: undefined,
};
