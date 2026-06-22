import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import {
  analyzeGames,
  getAnalyzedGames,
  getGameSync,
  getSample,
  sendMomentFeedback,
  startGameSync
} from '../lib/api';
import type { CoachAnalysis, CriticalMoment, Platform } from '../lib/types';

const STORAGE_KEY = 'chess-coach-workspace';

type StoredWorkspace = {
  analyses: CoachAnalysis[];
  activeGameId: string;
  player: string;
  pgn: string;
  platform?: Platform;
};

type WorkspaceContextValue = {
  pgn: string;
  setPgn: (value: string) => void;
  player: string;
  setPlayer: (value: string) => void;
  platform: Platform;
  setPlatform: (value: Platform) => void;
  analyses: CoachAnalysis[];
  activeGameId: string;
  loading: boolean;
  status: string;
  error: string;
  feedbackStatus: string;
  monitoringRefresh: number;
  openGame: (gameId: string) => void;
  runAnalysis: () => Promise<CoachAnalysis | null>;
  syncAllGames: () => Promise<CoachAnalysis | null>;
  recordFeedback: (moment: CriticalMoment, rating: 'helpful' | 'not_helpful') => Promise<void>;
  clearFeedbackStatus: () => void;
  restoreAnalyses: (items: CoachAnalysis[]) => void;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

function loadStoredWorkspace(): StoredWorkspace | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) as StoredWorkspace : null;
  } catch {
    return null;
  }
}

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const stored = useMemo(loadStoredWorkspace, []);
  const [pgn, setPgn] = useState(stored?.pgn || '');
  const [player, setPlayer] = useState(stored?.player || 'kfctofu');
  const [platform, setPlatform] = useState<Platform>(stored?.platform || 'chess.com');
  const [analyses, setAnalyses] = useState<CoachAnalysis[]>(stored?.analyses || []);
  const [activeGameId, setActiveGameId] = useState(stored?.activeGameId || stored?.analyses[0]?.game.game_id || '');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(stored?.analyses.length ? `${stored.analyses.length} games ready` : 'Ready');
  const [error, setError] = useState('');
  const [feedbackStatus, setFeedbackStatus] = useState('');
  const [monitoringRefresh, setMonitoringRefresh] = useState(0);

  useEffect(() => {
    if (pgn) return;
    getSample().then((sample) => {
      setPgn(sample.pgn);
      setPlayer(sample.player);
    }).catch(() => undefined);
  }, [pgn]);

  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
        analyses: analyses.slice(0, 25), activeGameId, player, pgn, platform
      }));
    } catch {
      // Server persistence remains authoritative when browser storage is full or unavailable.
    }
  }, [activeGameId, analyses, pgn, platform, player]);

  function openGame(gameId: string) {
    setActiveGameId(gameId);
    setFeedbackStatus('');
  }

  async function runAnalysis() {
    setLoading(true);
    setError('');
    setStatus('Analyzing pasted PGN...');
    try {
      const result = await analyzeGames(pgn, player, 20, 'pgn');
      setAnalyses(result.analyses);
      const first = result.analyses[0] || null;
      if (first) openGame(first.game.game_id);
      const moments = result.analyses.reduce((sum, item) => sum + item.moments.length, 0);
      setStatus(`Analyzed ${result.analyses.length} games with ${moments} coachable moments`);
      setMonitoringRefresh((value) => value + 1);
      return first;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Analysis failed');
      setStatus('Could not analyze PGN');
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function syncAllGames() {
    if (!player.trim()) return null;
    setLoading(true);
    setError('');
    setStatus(`Starting ${platform} history sync for ${player}...`);
    try {
      let job = await startGameSync(player, platform);
      while (!['complete', 'failed'].includes(job.status)) {
        const completed = job.analyzed_games + job.skipped_games;
        setStatus(
          job.status === 'fetching'
            ? `Fetching complete ${platform} history...`
            : `Analyzing game ${Math.min(completed + 1, job.total_games)} of ${job.total_games}...`
        );
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        job = await getGameSync(job.id);
      }
      if (job.status === 'failed') throw new Error(job.error || 'Game sync failed');
      const result = await getAnalyzedGames(player, platform);
      setAnalyses(result.analyses);
      const first = result.analyses[0] || null;
      if (first) openGame(first.game.game_id);
      setStatus(
        `Synced ${job.total_games} games · analyzed ${job.analyzed_games} new · skipped ${job.skipped_games} existing`
      );
      setMonitoringRefresh((value) => value + 1);
      return first;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `Could not sync games from ${platform}`);
      setStatus('Game sync failed');
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function recordFeedback(moment: CriticalMoment, rating: 'helpful' | 'not_helpful') {
    setFeedbackStatus('Saving feedback...');
    try {
      await sendMomentFeedback(moment, rating);
      setFeedbackStatus(rating === 'helpful' ? 'Marked helpful' : 'Marked for review');
      setMonitoringRefresh((value) => value + 1);
    } catch {
      setFeedbackStatus('Feedback could not be saved');
    }
  }

  return (
    <WorkspaceContext.Provider value={{
      pgn, setPgn, player, setPlayer, platform, setPlatform,
      analyses, activeGameId, loading, status, error,
      feedbackStatus, monitoringRefresh, openGame, runAnalysis, syncAllGames,
      recordFeedback, clearFeedbackStatus: () => setFeedbackStatus('')
      , restoreAnalyses: (items) => {
        setAnalyses(items);
        setStatus(`${items.length} games ready`);
        if (items.length && !activeGameId) setActiveGameId(items[0].game.game_id);
      }
    }}>
      {children}
    </WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) throw new Error('useWorkspace must be used inside WorkspaceProvider');
  return context;
}
