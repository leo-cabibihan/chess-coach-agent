import { useQuery } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Activity, ArrowRight, BookOpenCheck, Clock3, Database, Target } from 'lucide-react';
import { createCoachSession, getProgress } from '../lib/api';
import { useWorkspace } from '../workspace/WorkspaceContext';

export function HomePage() {
  const workspace = useWorkspace();
  const navigate = useNavigate();
  const progress = useQuery({
    queryKey: ['progress', workspace.platform, workspace.player],
    queryFn: () => getProgress(workspace.player, workspace.platform)
  });
  const profile = progress.data?.player;
  const themes = Object.entries(profile?.recurring_themes || {}).sort((a, b) => b[1] - a[1]);
  const focus = themes[0]?.[0]?.replace(/_/g, ' ') || 'candidate move discipline';

  async function continueTraining() {
    const session = await createCoachSession(workspace.player, workspace.platform);
    await navigate({ to: '/coach/$sessionId', params: { sessionId: session.id } });
  }

  return (
    <main className="route-page home-page">
      <header className="home-header">
        <div>
          <span className="page-eyebrow">Adaptive training</span>
          <h1>{workspace.player}</h1>
          <p>{workspace.platform} · {profile?.current_rating ? `${profile.current_rating} rating` : 'Profile ready'}</p>
        </div>
        <button className="primary" onClick={continueTraining}>
          <Target size={17} /> Continue training
        </button>
      </header>

      <section className="home-focus">
        <div className="focus-copy">
          <span>Today’s focus</span>
          <h2>{focus}</h2>
          <p>
            {themes.length
              ? `This pattern represents ${Math.round(themes[0][1] * 100)}% of your stored critical moments.`
              : 'Analyze games to build a personal weakness profile and practice queue.'}
          </p>
          <button className="primary" onClick={continueTraining}>Open coach <ArrowRight size={17} /></button>
        </div>
        <div className="focus-metrics">
          <div><Database size={18} /><strong>{progress.data?.total_games || workspace.analyses.length}</strong><span>Games</span></div>
          <div><Clock3 size={18} /><strong>{profile?.due_positions || 0}</strong><span>Due today</span></div>
          <div><BookOpenCheck size={18} /><strong>{profile?.mastered_positions || 0}</strong><span>Mastered</span></div>
          <div><Activity size={18} /><strong>{progress.data?.recent_attempts || 0}</strong><span>Attempts</span></div>
        </div>
      </section>

      <section className="home-next">
        <div>
          <strong>{workspace.analyses.length ? `${workspace.analyses.length} games ready in this browser` : 'Bring in recent games'}</strong>
          <span>{workspace.status}</span>
        </div>
        <button className="secondary" onClick={() => navigate({ to: '/analyze' })}>
          <Database size={16} /> Analyze games
        </button>
      </section>
    </main>
  );
}
