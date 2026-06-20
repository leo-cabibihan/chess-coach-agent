import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { analyzeGames, askCoach, getSample, importGames, sendMomentFeedback } from '../lib/api';
import type { CoachAnalysis, CriticalMoment, Platform } from '../lib/types';

const STORAGE_KEY = 'chess-coach-workspace';

type StoredWorkspace = {
  analyses: CoachAnalysis[];
  activeGameId: string;
  player: string;
  pgn: string;
};

type WorkspaceContextValue = {
  pgn: string;
  setPgn: (value: string) => void;
  player: string;
  setPlayer: (value: string) => void;
  platform: Platform;
  setPlatform: (value: Platform) => void;
  maxGames: number;
  setMaxGames: (value: number) => void;
  analyses: CoachAnalysis[];
  activeGameId: string;
  activeAnalysis: CoachAnalysis | null;
  loading: boolean;
  status: string;
  error: string;
  coachAnswer: string;
  feedbackStatus: string;
  monitoringRefresh: number;
  openGame: (gameId: string) => void;
  runAnalysis: () => Promise<CoachAnalysis | null>;
  runImport: () => Promise<CoachAnalysis | null>;
  ask: (question: string) => Promise<void>;
  recordFeedback: (moment: CriticalMoment, rating: 'helpful' | 'not_helpful') => Promise<void>;
  clearFeedbackStatus: () => void;
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
  const [platform, setPlatform] = useState<Platform>('chess.com');
  const [maxGames, setMaxGames] = useState(10);
  const [analyses, setAnalyses] = useState<CoachAnalysis[]>(stored?.analyses || []);
  const [activeGameId, setActiveGameId] = useState(stored?.activeGameId || stored?.analyses[0]?.game.game_id || '');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(stored?.analyses.length ? `${stored.analyses.length} games ready` : 'Ready');
  const [error, setError] = useState('');
  const [coachAnswer, setCoachAnswer] = useState('');
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
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ analyses, activeGameId, player, pgn }));
  }, [activeGameId, analyses, pgn, player]);

  const activeAnalysis = analyses.find((item) => item.game.game_id === activeGameId) || analyses[0] || null;

  function openGame(gameId: string) {
    setActiveGameId(gameId);
    setCoachAnswer('');
    setFeedbackStatus('');
  }

  async function runAnalysis() {
    setLoading(true);
    setError('');
    setStatus(`Analyzing up to ${maxGames} PGN games...`);
    try {
      const result = await analyzeGames(pgn, player, maxGames);
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

  async function runImport() {
    if (!player.trim()) return null;
    setLoading(true);
    setError('');
    setStatus(`Importing ${maxGames} recent ${platform} games...`);
    try {
      const result = await importGames(player, platform, maxGames);
      setAnalyses(result.analyses);
      const first = result.analyses[0] || null;
      if (first) openGame(first.game.game_id);
      const moments = result.analyses.reduce((sum, item) => sum + item.moments.length, 0);
      setStatus(`Imported ${result.analyses.length} ${platform} games with ${moments} moments`);
      setMonitoringRefresh((value) => value + 1);
      return first;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `Could not import from ${platform}`);
      setStatus('Import failed');
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function ask(question: string) {
    if (!question.trim()) return;
    setLoading(true);
    setError('');
    setStatus('Asking MiniMax coach...');
    try {
      setCoachAnswer(await askCoach(question, activeAnalysis));
      setStatus('Coach answer ready');
      setMonitoringRefresh((value) => value + 1);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Coach chat failed');
      setStatus('Coach chat failed');
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
      pgn, setPgn, player, setPlayer, platform, setPlatform, maxGames, setMaxGames,
      analyses, activeGameId, activeAnalysis, loading, status, error, coachAnswer,
      feedbackStatus, monitoringRefresh, openGame, runAnalysis, runImport, ask,
      recordFeedback, clearFeedbackStatus: () => setFeedbackStatus('')
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
