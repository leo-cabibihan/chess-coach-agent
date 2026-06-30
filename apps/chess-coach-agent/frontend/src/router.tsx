import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Link,
  Outlet,
  createRootRoute,
  createRoute,
  createRouter,
  redirect
} from '@tanstack/react-router';
import {
  Activity,
  AlertCircle,
  BookOpenCheck,
  Database,
  Library,
  Loader2,
  Home,
  Target,
  TrendingUp,
  Upload
} from 'lucide-react';
import { AnalysisPanel } from './components/AnalysisPanel';
import { GameList } from './components/GameList';
import { GamePanel } from './components/GamePanel';
import { MonitoringDashboard } from './components/MonitoringDashboard';
import type { CoachAnalysis, CriticalMoment, Platform } from './lib/types';
import { useWorkspace } from './workspace/WorkspaceContext';
import { HomePage } from './pages/HomePage';
import { ProgressPage } from './pages/ProgressPage';
import { PracticePage } from './pages/PracticePage';
import { createTrainingSession, getAnalyzedGames } from './lib/api';

function AppShell() {
  const { analyses } = useWorkspace();
  return (
    <div className="app-frame">
      <aside className="app-sidebar">
        <Link className="brand" to="/">
          <Activity size={19} />
          <span>Chess Coach</span>
        </Link>
        <nav aria-label="Primary navigation">
          <Link to="/" activeProps={{ className: 'active' }} activeOptions={{ exact: true }}>
            <Home size={18} /><span>Home</span>
          </Link>
          <Link to="/games" search={{ import: false }} activeProps={{ className: 'active' }}>
            <Library size={18} /><span>Games</span>
            {analyses.length > 0 && <small>{analyses.length}</small>}
          </Link>
          <Link to="/practice" activeProps={{ className: 'active' }}>
            <Target size={18} /><span>Practice</span>
          </Link>
          <Link to="/progress" activeProps={{ className: 'active' }}>
            <TrendingUp size={18} /><span>Progress</span>
          </Link>
        </nav>
      </aside>
      <div className="app-content"><Outlet /></div>
    </div>
  );
}

function PageHeader({ eyebrow, title, detail, actions }: {
  eyebrow: string;
  title: string;
  detail?: string;
  actions?: React.ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <span className="page-eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        {detail && <p>{detail}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </header>
  );
}

function GameIntake({ onAnalyzed }: { onAnalyzed: (analysis: CoachAnalysis) => void }) {
  const workspace = useWorkspace();

  async function syncAll() {
    const first = await workspace.syncAllGames();
    if (first) onAnalyzed(first);
  }

  return (
    <section className="game-intake">
      <section className="intake-workspace intake-workspace-single">
        <div className="intake-section online-import">
          <div className="section-heading">
            <Database size={18} />
            <div><strong>Player account</strong><span>Sync your Chess.com or Lichess game history</span></div>
          </div>
          <div className="intake-fields">
            <label>
              Player username
              <input
                aria-label="Player username"
                data-testid="player-username"
                value={workspace.player}
                onChange={(event) => workspace.setPlayer(event.target.value)}
              />
            </label>
            <label>
              Source
              <select
                aria-label="Source"
                data-testid="player-platform"
                value={workspace.platform}
                onChange={(event) => workspace.setPlatform(event.target.value as Platform)}
              >
                <option value="lichess">Lichess</option>
                <option value="chess.com">Chess.com</option>
              </select>
            </label>
          </div>
          <button
            className="primary"
            data-testid="sync-history-btn"
            onClick={syncAll}
            disabled={workspace.loading || !workspace.player.trim()}
          >
            {workspace.loading ? <Loader2 className="spin" size={17} /> : <Database size={17} />}
            Sync full history
          </button>
        </div>
      </section>
      <div className={workspace.error ? 'route-status error' : 'route-status'} data-testid="workspace-status">
        {workspace.error ? <AlertCircle size={16} /> : <Activity size={16} />}
        {workspace.error || workspace.status}
      </div>
    </section>
  );
}

function GamesPage() {
  const workspace = useWorkspace();
  const { analyses, activeGameId, openGame } = workspace;
  const navigate = gamesRoute.useNavigate();
  const search = gamesRoute.useSearch();
  const showImport = search.import || analyses.length === 0;
  const persisted = useQuery({
    queryKey: ['analyzed-games', workspace.platform, workspace.player],
    queryFn: () => getAnalyzedGames(workspace.player, workspace.platform),
    staleTime: 60_000
  });
  useEffect(() => {
    if (persisted.data?.analyses.length && persisted.data.analyses.length !== analyses.length) {
      workspace.restoreAnalyses(persisted.data.analyses);
    }
  }, [analyses.length, persisted.data]);
  const activeIndex = Math.max(0, analyses.findIndex((item) => item.game.game_id === activeGameId));

  function selectGame(index: number) {
    const game = analyses[index];
    if (!game) return;
    openGame(game.game.game_id);
    void navigate({ to: '/games/$gameId', params: { gameId: game.game.game_id }, search: { moment: undefined } });
  }

  function openAnalyzedGame(analysis: CoachAnalysis) {
    void navigate({
      to: '/games/$gameId',
      params: { gameId: analysis.game.game_id },
      search: { moment: undefined }
    });
  }

  return (
    <main className="route-page games-page">
      <PageHeader
        eyebrow="Game library"
        title="Your analyzed games"
        detail={analyses.length ? `${analyses.length} games ready for review.` : 'No games analyzed in this session.'}
        actions={<button
          className="secondary route-action"
          onClick={() => navigate({ search: { import: !showImport } })}
        ><Upload size={16} /> {showImport ? 'Close import' : 'Import games'}</button>}
      />
      {showImport && <GameIntake onAnalyzed={openAnalyzedGame} />}
      {analyses.length ? (
        <GameList analyses={analyses} activeIndex={activeIndex} onSelect={selectGame} />
      ) : !showImport ? (
        <section className="empty-route">
          <Library size={28} />
          <h2>No games yet</h2>
          <button className="primary" onClick={() => navigate({ search: { import: true } })}>
            Import games
          </button>
        </section>
      ) : null}
    </main>
  );
}

function gameStats(analysis: CoachAnalysis) {
  const side = analysis.game.player_color === 'unknown' ? 'player' : analysis.game.player_color;
  return [
    `${analysis.moves.length} plies`,
    `${analysis.moments.length} moments`,
    `${analysis.game.player_result} as ${side}`,
    analysis.game.player_elo ? `${analysis.game.player_elo} Elo` : analysis.game.time_control || 'PGN'
  ];
}

function GameReviewPage() {
  const { gameId } = gameRoute.useParams();
  const search = gameRoute.useSearch();
  const navigate = gameRoute.useNavigate();
  const workspace = useWorkspace();
  const analysis = workspace.analyses.find((item) => item.game.game_id === gameId) || null;
  const selectedMoment = analysis?.moments.find((moment) => moment.id === search.moment) || analysis?.moments[0] || null;
  const [currentPly, setCurrentPly] = useState(selectedMoment?.ply || 0);
  const [startingPractice, setStartingPractice] = useState(false);

  useEffect(() => {
    if (analysis) workspace.openGame(analysis.game.game_id);
  }, [analysis?.game.game_id]);

  useEffect(() => {
    setCurrentPly(selectedMoment?.ply || 0);
    workspace.clearFeedbackStatus();
  }, [selectedMoment?.id]);

  function selectMoment(moment: CriticalMoment) {
    setCurrentPly(moment.ply);
    workspace.clearFeedbackStatus();
    void navigate({ search: { moment: moment.id }, replace: true });
  }

  async function openPractice() {
    if (!analysis || !selectedMoment) return;
    setStartingPractice(true);
    try {
      const created = await createTrainingSession(
        workspace.player,
        workspace.platform,
        selectedMoment.theme,
        selectedMoment.id
      );
      await navigate({ to: '/practice/$sessionId', params: { sessionId: created.id } });
    } finally {
      setStartingPractice(false);
    }
  }

  if (!analysis) {
    return (
      <main className="route-page">
        <section className="empty-route">
          <BookOpenCheck size={28} />
          <h2>Review unavailable</h2>
          <p>This game is not in the current browser session.</p>
          <Link className="primary" to="/games" search={{ import: false }}>Back to games</Link>
        </section>
      </main>
    );
  }

  return (
    <main className="route-page review-page">
      <PageHeader
        eyebrow={`${analysis.game.date} · ${analysis.game.player_result}`}
        title={`${analysis.game.white} vs ${analysis.game.black}`}
        actions={<>
          <button className="secondary route-action" disabled={startingPractice} onClick={openPractice}>
            <Target size={16} /> Train this position
          </button>
          <Link className="secondary route-action" to="/games" search={{ import: false }}><Library size={16} /> All games</Link>
        </>}
      />
      <div className="stat-row">{gameStats(analysis).map((stat) => <span key={stat}>{stat}</span>)}</div>
      <div className="layout review-layout">
        <AnalysisPanel
          analysis={analysis}
          selectedMoment={selectedMoment}
          onSelectMoment={selectMoment}
          onFeedback={workspace.recordFeedback}
          feedbackStatus={workspace.feedbackStatus}
        />
        <GamePanel
          analysis={analysis}
          selectedMoment={selectedMoment}
          currentPly={currentPly}
          setCurrentPly={setCurrentPly}
        />
      </div>
    </main>
  );
}

function PracticeSessionRoutePage() {
  const { sessionId } = practiceSessionRoute.useParams();
  return <PracticePage sessionId={sessionId} />;
}

function QualityPage() {
  const { monitoringRefresh } = useWorkspace();
  return (
    <main className="route-page quality-page">
      <PageHeader
        eyebrow="Agent operations"
        title="Quality monitoring"
        detail="Analyses, model usage, and coaching feedback."
      />
      <MonitoringDashboard refreshKey={monitoringRefresh} />
    </main>
  );
}

const rootRoute = createRootRoute({ component: AppShell });

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: HomePage
});

const analyzeRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/analyze',
  beforeLoad: () => {
    throw redirect({ to: '/games', search: { import: true } });
  }
});
const gamesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/games',
  validateSearch: (search: Record<string, unknown>) => ({
    import: search.import === true || search.import === 'true'
  }),
  component: GamesPage
});
const gameRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/games/$gameId',
  validateSearch: (search: Record<string, unknown>) => ({
    moment: typeof search.moment === 'string' ? search.moment : undefined
  }),
  component: GameReviewPage
});
const practiceRoute = createRoute({ getParentRoute: () => rootRoute, path: '/practice', component: PracticePage });
const practiceSessionRoute = createRoute({ getParentRoute: () => rootRoute, path: '/practice/$sessionId', component: PracticeSessionRoutePage });
const retiredCoachRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/coach',
  beforeLoad: () => { throw redirect({ to: '/practice' }); }
});
const retiredCoachSessionRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/coach/$sessionId',
  beforeLoad: () => { throw redirect({ to: '/practice' }); }
});
const progressRoute = createRoute({ getParentRoute: () => rootRoute, path: '/progress', component: ProgressPage });
const qualityRoute = createRoute({ getParentRoute: () => rootRoute, path: '/quality', component: QualityPage });

const routeTree = rootRoute.addChildren([
  indexRoute, analyzeRoute, gamesRoute, gameRoute, practiceRoute, practiceSessionRoute,
  retiredCoachRoute, retiredCoachSessionRoute, progressRoute, qualityRoute
]);

export const router = createRouter({ routeTree, defaultPreload: 'intent', scrollRestoration: true });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
