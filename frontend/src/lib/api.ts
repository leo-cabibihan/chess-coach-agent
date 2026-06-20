import type {
  AnalyzeResponse,
  CoachAnalysis,
  CriticalMoment,
  GamePreviewResponse,
  MonitoringSummary,
  Platform
} from './types';

export async function getSample(): Promise<{ player: string; pgn: string }> {
  const response = await fetch('/api/sample');
  if (!response.ok) throw new Error('Could not load sample PGN');
  return response.json();
}

export async function analyzeGames(pgn: string, player: string, maxGames: number): Promise<AnalyzeResponse> {
  const response = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pgn, player, max_games: maxGames })
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

export async function askCoach(question: string, analysis: CoachAnalysis | null): Promise<string> {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, analysis })
  });
  if (!response.ok) throw new Error('Coach chat failed');
  const payload = await response.json();
  return payload.answer;
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
