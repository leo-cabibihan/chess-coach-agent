import type { CoachAnalysis } from './types';

export async function getSample(): Promise<{ player: string; pgn: string }> {
  const response = await fetch('/api/sample');
  if (!response.ok) throw new Error('Could not load sample PGN');
  return response.json();
}

export async function analyzeGame(pgn: string, player: string): Promise<CoachAnalysis> {
  const response = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pgn, player, max_games: 1 })
  });
  if (!response.ok) throw new Error('Analysis failed');
  const payload = await response.json();
  return payload.analyses[0];
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
