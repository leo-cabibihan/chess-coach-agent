import type { AnalyzeResponse, CoachAnalysis, Platform } from './types';

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
