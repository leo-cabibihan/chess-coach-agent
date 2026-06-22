import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { analyzeGames, askCoach, getSample, previewPlayerGames, sendMomentFeedback } from '../lib/api';
import type { ChatResponse, CoachAnalysis, CriticalMoment, GamePreview, Platform } from '../lib/types';

const STORAGE_KEY = 'chess-coach-workspace';

type StoredWorkspace = {
  analyses: CoachAnalysis[];
  activeGameId: string;
  player: string;
  pgn: string;
  platform?: Platform;
  availableGames?: GamePreview[];
  selectedGameIds?: string[];
};

type WorkspaceContextValue = {
  pgn: string;
  setPgn: (value: string) => void;
  player: string;
  setPlayer: (value: string) => void;
  platform: Platform;
  setPlatform: (value: Platform) => void;
  availableGames: GamePreview[];
  selectedGameIds: string[];
  analyses: CoachAnalysis[];
  activeGameId: string;
  activeAnalysis: CoachAnalysis | null;
  loading: boolean;
  status: string;
  error: string;
  coachAnswer: string;
  coachResponse: ChatResponse | null;
  feedbackStatus: string;
  monitoringRefresh: number;
  openGame: (gameId: string) => void;
  runAnalysis: () => Promise<CoachAnalysis | null>;
  findGames: () => Promise<void>;
  toggleGameSelection: (gameId: string) => void;
  selectAllGames: () => void;
  clearGameSelection: () => void;
  analyzeSelectedGames: () => Promise<CoachAnalysis | null>;
  ask: (question: string) => Promise<void>;
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
  const [availableGames, setAvailableGames] = useState<GamePreview[]>(stored?.availableGames || []);
  const [selectedGameIds, setSelectedGameIds] = useState<string[]>(stored?.selectedGameIds || []);
  const [analyses, setAnalyses] = useState<CoachAnalysis[]>(stored?.analyses || []);
  const [activeGameId, setActiveGameId] = useState(stored?.activeGameId || stored?.analyses[0]?.game.game_id || '');
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(stored?.analyses.length ? `${stored.analyses.length} games ready` : 'Ready');
  const [error, setError] = useState('');
  const [coachAnswer, setCoachAnswer] = useState('');
  const [coachResponse, setCoachResponse] = useState<ChatResponse | null>(null);
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
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      analyses, activeGameId, player, pgn, platform, availableGames, selectedGameIds
    }));
  }, [activeGameId, analyses, availableGames, pgn, platform, player, selectedGameIds]);

  const activeAnalysis = analyses.find((item) => item.game.game_id === activeGameId) || analyses[0] || null;

  function openGame(gameId: string) {
    setActiveGameId(gameId);
    setCoachAnswer('');
    setCoachResponse(null);
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

  async function findGames() {
    if (!player.trim()) return;
    setLoading(true);
    setError('');
    setStatus(`Finding ${platform} games for ${player}...`);
    try {
      const result = await previewPlayerGames(player, platform, 50);
      setAvailableGames(result.games);
      setSelectedGameIds(result.games.slice(0, 3).map((game) => game.game_id));
      setStatus(`Found ${result.games.length} games. Select up to 10 to analyze.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `Could not find games on ${platform}`);
      setStatus('Game search failed');
    } finally {
      setLoading(false);
    }
  }

  function toggleGameSelection(gameId: string) {
    setSelectedGameIds((current) => {
      if (current.includes(gameId)) return current.filter((id) => id !== gameId);
      if (current.length >= 10) {
        setError('Select up to 10 games per analysis batch.');
        return current;
      }
      setError('');
      return [...current, gameId];
    });
  }

  function selectAllGames() {
    setError('');
    setSelectedGameIds(availableGames.slice(0, 10).map((game) => game.game_id));
  }

  async function analyzeSelectedGames() {
    const selected = availableGames.filter((game) => selectedGameIds.includes(game.game_id));
    if (!selected.length) return null;
    setLoading(true);
    setError('');
    setStatus(`Analyzing ${selected.length} selected games...`);
    try {
      const result = await analyzeGames(selected.map((game) => game.pgn).join('\n\n'), player, selected.length, platform);
      setAnalyses(result.analyses);
      const first = result.analyses[0] || null;
      if (first) openGame(first.game.game_id);
      const moments = result.analyses.reduce((sum, item) => sum + item.moments.length, 0);
      setStatus(`Analyzed ${result.analyses.length} selected games with ${moments} moments`);
      setMonitoringRefresh((value) => value + 1);
      return first;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Selected game analysis failed');
      setStatus('Could not analyze selected games');
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
      const response = await askCoach(question, activeAnalysis);
      setCoachResponse(response);
      setCoachAnswer(response.answer);
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
      pgn, setPgn, player, setPlayer, platform, setPlatform, availableGames, selectedGameIds,
      analyses, activeGameId, activeAnalysis, loading, status, error, coachAnswer,
      coachResponse,
      feedbackStatus, monitoringRefresh, openGame, runAnalysis, findGames,
      toggleGameSelection, selectAllGames, clearGameSelection: () => setSelectedGameIds([]),
      analyzeSelectedGames, ask,
      recordFeedback, clearFeedbackStatus: () => setFeedbackStatus('')
      , restoreAnalyses: (items) => {
        setAnalyses(items);
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
