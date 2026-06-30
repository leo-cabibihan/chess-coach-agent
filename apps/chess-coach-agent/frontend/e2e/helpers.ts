import { APIRequestContext } from '@playwright/test';

const API_BASE = process.env.PLAYWRIGHT_API_BASE || 'http://127.0.0.1:8000/api';

export async function seedPlayerFromSample(request: APIRequestContext, player = 'kfctofu') {
  const sampleResponse = await request.get(`${API_BASE}/sample`);
  if (!sampleResponse.ok()) throw new Error('Could not load sample PGN');
  const sample = await sampleResponse.json();
  const analyzeResponse = await request.post(`${API_BASE}/analyze`, {
    data: {
      pgn: sample.pgn,
      player,
      platform: 'chess.com',
      max_games: 1
    }
  });
  if (!analyzeResponse.ok()) throw new Error('Could not analyze sample PGN for tests');
  return analyzeResponse.json();
}

export async function syncPlayerAccount(
  request: APIRequestContext,
  username: string,
  platform: 'chess.com' | 'lichess',
  maxGames = 2
) {
  const started = await request.post(`${API_BASE}/games/sync`, {
    data: { username, platform, max_games: maxGames }
  });
  if (!started.ok()) {
    const body = await started.text();
    throw new Error(`Could not start sync for ${username}: ${body}`);
  }
  const job = await started.json();
  const deadline = Date.now() + 240_000;
  let current = job;
  while (!['complete', 'failed'].includes(current.status)) {
    if (Date.now() > deadline) throw new Error(`Sync timed out for ${username}`);
    await new Promise((resolve) => setTimeout(resolve, 1500));
    const polled = await request.get(`${API_BASE}/games/sync/${current.id}`);
    if (!polled.ok()) throw new Error(`Could not poll sync for ${username}`);
    current = await polled.json();
  }
  if (current.status === 'failed') {
    throw new Error(current.error || `Sync failed for ${username}`);
  }
  const games = await request.get(`${API_BASE}/games/${platform}/${encodeURIComponent(username)}`);
  if (!games.ok()) throw new Error(`Could not load analyzed games for ${username}`);
  return games.json();
}

export async function clearBrowserWorkspace(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    sessionStorage.removeItem('chess-coach-workspace');
  });
}
