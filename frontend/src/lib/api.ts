import type {
  AnalyzeResponse,
  ChatResponse,
  CoachAnalysis,
  CriticalMoment,
  GamePreviewResponse,
  MonitoringSummary,
  Platform,
  CoachSession,
  CoachPanel,
  ProgressSummary,
  TrainingSession
} from './types';

export async function getSample(): Promise<{ player: string; pgn: string }> {
  const response = await fetch('/api/sample');
  if (!response.ok) throw new Error('Could not load sample PGN');
  return response.json();
}

export async function analyzeGames(
  pgn: string,
  player: string,
  maxGames: number,
  platform: Platform | 'pgn' = 'pgn'
): Promise<AnalyzeResponse> {
  const response = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pgn, player, max_games: maxGames, platform })
  });
  if (!response.ok) throw new Error('Analysis failed');
  return response.json();
}

export async function importGames(username: string, platform: Platform, maxGames: number): Promise<AnalyzeResponse> {
  const response = await fetch('/api/import', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, platform, max_games: maxGames })
  });
  if (!response.ok) throw new Error(`Could not import games from ${platform}`);
  return response.json();
}

export async function previewPlayerGames(
  username: string,
  platform: Platform,
  maxGames = 50
): Promise<GamePreviewResponse> {
  const response = await fetch('/api/games/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, platform, max_games: maxGames })
  });
  if (!response.ok) throw new Error(`Could not find games for ${username} on ${platform}`);
  return response.json();
}

export async function askCoach(question: string, analysis: CoachAnalysis | null): Promise<ChatResponse> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, analysis })
  });
  if (!response.ok) throw new Error('Coach chat failed');
  return response.json();
}

export async function sendMomentFeedback(
  moment: CriticalMoment,
  rating: 'helpful' | 'not_helpful',
  comment = ''
): Promise<void> {
  const response = await fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      moment_id: moment.id,
      game_id: moment.game_id,
      rating,
      theme: moment.theme,
      fen: moment.fen_before,
      comment
    })
  });
  if (!response.ok) throw new Error('Could not record feedback');
}

export async function getMonitoring(): Promise<MonitoringSummary> {
  const response = await fetch('/api/monitoring');
  if (!response.ok) throw new Error('Could not load monitoring summary');
  return response.json();
}

export async function createCoachSession(
  username: string,
  platform: Platform,
  focusTheme?: string
): Promise<CoachSession> {
  const response = await fetch('/api/coach/sessions', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, platform, focus_theme: focusTheme || 'general improvement' })
  });
  if (!response.ok) throw new Error('Could not start coach session');
  return response.json();
}

export async function getCoachSession(sessionId: string): Promise<CoachSession> {
  const response = await fetch(`/api/coach/sessions/${sessionId}`);
  if (!response.ok) throw new Error('Could not load coach session');
  return response.json();
}

export async function sendCoachMessage(sessionId: string, content: string): Promise<string> {
  const response = await fetch(`/api/coach/sessions/${sessionId}/messages`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ content })
  });
  if (!response.ok) throw new Error('Coach message failed');
  const payload = await response.json();
  return payload.message_id;
}

export async function readCoachEvents(
  sessionId: string,
  messageId: string,
  onEvent: (type: string, payload: Record<string, unknown>) => void
): Promise<void> {
  const response = await fetch(`/api/coach/sessions/${sessionId}/stream?message_id=${messageId}`);
  if (!response.ok || !response.body) throw new Error('Coach stream failed');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const frames = buffer.split('\n\n');
    buffer = frames.pop() || '';
    for (const frame of frames) {
      const event = frame.match(/^event: (.+)$/m)?.[1];
      const data = frame.match(/^data: (.+)$/m)?.[1];
      if (event && data) onEvent(event, JSON.parse(data));
    }
    if (done) break;
  }
}

export async function createTrainingSession(
  username: string,
  platform: Platform,
  theme?: string
): Promise<TrainingSession> {
  const response = await fetch('/api/training/sessions', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, platform, theme: theme || null, position_count: 5 })
  });
  if (!response.ok) throw new Error('Could not build training session');
  return response.json();
}

export async function submitTrainingAttempt(
  trainingSessionId: string,
  positionId: string,
  move: string,
  hintsUsed: number,
  elapsedMs: number
): Promise<Extract<CoachPanel, { type: 'evaluation' }>> {
  const response = await fetch(`/api/training/sessions/${trainingSessionId}/attempts`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ position_id: positionId, move, hints_used: hintsUsed, elapsed_ms: elapsedMs })
  });
  if (!response.ok) throw new Error('Could not evaluate move');
  return response.json();
}

export async function getProgress(username: string, platform: Platform): Promise<ProgressSummary> {
  const response = await fetch(`/api/progress/${platform}/${encodeURIComponent(username)}`);
  if (!response.ok) throw new Error('Could not load progress');
  return response.json();
}

export async function getAnalyzedGames(
  username: string,
  platform: Platform
): Promise<AnalyzeResponse> {
  const response = await fetch(`/api/games/${platform}/${encodeURIComponent(username)}`);
  if (!response.ok) throw new Error('Could not load analyzed games');
  return response.json();
}
