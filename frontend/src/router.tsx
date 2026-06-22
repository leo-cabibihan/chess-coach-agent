import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Link,
  Outlet,
  createRootRoute,
  createRoute,
  createRouter
} from '@tanstack/react-router';
import {
  Activity,
  AlertCircle,
  BarChart3,
  BookOpenCheck,
  ChevronRight,
  Database,
  Library,
  Loader2,
  MessageCircle,
  Dumbbell,
  Home,
  TrendingUp,
  Search,
  Upload
} from 'lucide-react';
import { AnalysisPanel } from './components/AnalysisPanel';
import { GameList } from './components/GameList';
import { GamePicker } from './components/GamePicker';
import { GamePanel } from './components/GamePanel';
import { MonitoringDashboard } from './components/MonitoringDashboard';
import type { CoachAnalysis, CriticalMoment, Platform } from './lib/types';
import { useWorkspace } from './workspace/WorkspaceContext';
import { HomePage } from './pages/HomePage';
import { CoachWorkspacePage } from './pages/CoachWorkspacePage';
import { ProgressPage } from './pages/ProgressPage';
import { createCoachSession, getAnalyzedGames, sendCoachMessage } from './lib/api';

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
          <Link to="/games" activeProps={{ className: 'active' }}>
            <Library size={18} /><span>Games</span>
            {analyses.length > 0 && <small>{analyses.length}</small>}
          </Link>
          <Link to="/coach" activeProps={{ className: 'active' }}>
            <MessageCircle size={18} /><span>Coach</span>
          </Link>
          <Link to="/progress" activeProps={{ className: 'active' }}>
            <TrendingUp size={18} /><span>Progress</span>
          </Link>
          <Link to="/quality" activeProps={{ className: 'active' }}>
            <BarChart3 size={18} /><span>Quality</span>
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

function AnalyzePage() {
  const workspace = useWorkspace();
  const navigate = analyzeRoute.useNavigate();

  async function analyze() {
    const first = await workspace.runAnalysis();
    if (first) await navigate({ to: '/games/$gameId', params: { gameId: first.game.game_id }, search: { moment: undefined } });
  }

  async function analyzeSelected() {
    const first = await workspace.analyzeSelectedGames();
    if (first) await navigate({ to: '/games/$gameId', params: { gameId: first.game.game_id }, search: { moment: undefined } });
  }

  return (
    <main className="route-page analyze-page">
      <PageHeader
        eyebrow="Game intake"
        title="Analyze your games"
        detail="Choose games from a player profile or review pasted PGN."
      />
      <section className="intake-workspace">
        <div className="intake-section online-import">
          <div className="section-heading">
            <Database size={18} />
            <div><strong>Online games</strong><span>Chess.com or Lichess</span></div>
          </div>
          <div className="intake-fields">
            <label>
              Player username
              <input value={workspace.player} onChange={(event) => workspace.setPlayer(event.target.value)} />
            </label>
            <label>
              Source
              <select value={workspace.platform} onChange={(event) => workspace.setPlatform(event.target.value as Platform)}>
                <option value="chess.com">Chess.com</option>
                <option value="lichess">Lichess</option>
              </select>
            </label>
          </div>
          <button className="primary" onClick={workspace.findGames} disabled={workspace.loading || !workspace.player.trim()}>
            {workspace.loading ? <Loader2 className="spin" size={17} /> : <Database size={17} />}
            Find games
          </button>
        </div>

        {workspace.availableGames.length > 0 && (
          <GamePicker
            games={workspace.availableGames}
            selectedIds={workspace.selectedGameIds}
            loading={workspace.loading}
            onToggle={workspace.toggleGameSelection}
            onSelectAll={workspace.selectAllGames}
            onClear={workspace.clearGameSelection}
            onAnalyze={analyzeSelected}
          />
        )}

        <div className="intake-divider"><span>or</span></div>

        <div className="intake-section pgn-import">
          <div className="section-heading">
            <Upload size={18} />
            <div><strong>PGN review</strong><span>Paste one or more games</span></div>
          </div>
          <label>
            PGN
            <textarea value={workspace.pgn} onChange={(event) => workspace.setPgn(event.target.value)} rows={9} />
          </label>
          <button className="secondary" onClick={analyze} disabled={workspace.loading || !workspace.pgn.trim()}>
            {workspace.loading ? <Loader2 className="spin" size={17} /> : <Upload size={17} />}
            Analyze pasted PGN
          </button>
        </div>
      </section>
      <div className={workspace.error ? 'route-status error' : 'route-status'}>
        {workspace.error ? <AlertCircle size={16} /> : <Activity size={16} />}
        {workspace.error || workspace.status}
      </div>
      {workspace.analyses.length > 0 && (
        <section className="continue-review">
          <div>
            <strong>{workspace.analyses.length} games in this session</strong>
            <span>Continue from the game library.</span>
          </div>
          <Link to="/games">Open games <ChevronRight size={17} /></Link>
        </section>
      )}
    </main>
  );
}

function GamesPage() {
  const workspace = useWorkspace();
  const { analyses, activeGameId, openGame } = workspace;
  const navigate = gamesRoute.useNavigate();
  const persisted = useQuery({
    queryKey: ['analyzed-games', workspace.platform, workspace.player],
    queryFn: () => getAnalyzedGames(workspace.player, workspace.platform),
    enabled: analyses.length === 0
  });
  useEffect(() => {
    if (!analyses.length && persisted.data?.analyses.length) {
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

  return (
    <main className="route-page games-page">
      <PageHeader
        eyebrow="Game library"
        title="Your analyzed games"
        detail={analyses.length ? `${analyses.length} games ready for review.` : 'No games analyzed in this session.'}
        actions={<Link className="secondary route-action" to="/analyze"><Search size={16} /> Add games</Link>}
      />
      {analyses.length ? (
        <GameList analyses={analyses} activeIndex={activeIndex} onSelect={selectGame} />
      ) : (
        <section className="empty-route">
          <Library size={28} />
          <h2>No games yet</h2>
          <Link className="primary" to="/analyze">Analyze games</Link>
        </section>
      )}
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
  const [startingCoach, setStartingCoach] = useState(false);

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

  async function openCoach(practice: boolean) {
    if (!analysis || !selectedMoment) return;
    setStartingCoach(true);
    try {
      const created = await createCoachSession(
        workspace.player,
        workspace.platform,
        selectedMoment.theme
      );
      const request = practice
        ? `Create a practice quiz from game ${analysis.game.game_id}, especially move ${selectedMoment.move_number}.`
        : `Help me understand game ${analysis.game.game_id}, especially move ${selectedMoment.move_number} where I played ${selectedMoment.played_san}.`;
      await sendCoachMessage(created.id, request);
      await navigate({ to: '/coach/$sessionId', params: { sessionId: created.id } });
    } finally {
      setStartingCoach(false);
    }
  }

  if (!analysis) {
    return (
      <main className="route-page">
        <section className="empty-route">
          <BookOpenCheck size={28} />
          <h2>Review unavailable</h2>
          <p>This game is not in the current browser session.</p>
          <Link className="primary" to="/games">Back to games</Link>
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
          <button className="secondary route-action" disabled={startingCoach} onClick={() => openCoach(false)}>
            <MessageCircle size={16} /> Ask coach
          </button>
          <button className="secondary route-action" disabled={startingCoach} onClick={() => openCoach(true)}>
            <Dumbbell size={16} /> Add to practice
          </button>
          <Link className="secondary route-action" to="/games"><Library size={16} /> All games</Link>
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

function CoachSessionRoutePage() {
  const { sessionId } = coachSessionRoute.useParams();
  return <CoachWorkspacePage sessionId={sessionId} />;
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

const analyzeRoute = createRoute({ getParentRoute: () => rootRoute, path: '/analyze', component: AnalyzePage });
const gamesRoute = createRoute({ getParentRoute: () => rootRoute, path: '/games', component: GamesPage });
const gameRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/games/$gameId',
  validateSearch: (search: Record<string, unknown>) => ({
    moment: typeof search.moment === 'string' ? search.moment : undefined
  }),
  component: GameReviewPage
});
const coachRoute = createRoute({ getParentRoute: () => rootRoute, path: '/coach', component: CoachWorkspacePage });
const coachSessionRoute = createRoute({ getParentRoute: () => rootRoute, path: '/coach/$sessionId', component: CoachSessionRoutePage });
const progressRoute = createRoute({ getParentRoute: () => rootRoute, path: '/progress', component: ProgressPage });
const qualityRoute = createRoute({ getParentRoute: () => rootRoute, path: '/quality', component: QualityPage });

const routeTree = rootRoute.addChildren([
  indexRoute, analyzeRoute, gamesRoute, gameRoute, coachRoute, coachSessionRoute, progressRoute, qualityRoute
]);

export const router = createRouter({ routeTree, defaultPreload: 'intent', scrollRestoration: true });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
