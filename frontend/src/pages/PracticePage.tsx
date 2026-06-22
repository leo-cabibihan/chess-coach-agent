import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { ArrowRight, CheckCircle2, Loader2, RotateCcw, Target } from 'lucide-react';
import { ChessBoard } from '../components/ChessBoard';
import {
  createTrainingSession,
  getTrainingSession,
  submitTrainingAttempt
} from '../lib/api';
import type { EvaluationPanel } from '../lib/types';
import { useWorkspace } from '../workspace/WorkspaceContext';

export function PracticePage({ sessionId }: { sessionId?: string }) {
  const workspace = useWorkspace();
  const navigate = useNavigate();
  const [index, setIndex] = useState(0);
  const [move, setMove] = useState('');
  const [evaluation, setEvaluation] = useState<EvaluationPanel | null>(null);
  const [busy, setBusy] = useState(false);
  const [hintOpen, setHintOpen] = useState(false);
  const started = useMemo(() => Date.now(), [index, sessionId]);
  const training = useQuery({
    queryKey: ['training-session', sessionId],
    queryFn: () => getTrainingSession(sessionId!),
    enabled: Boolean(sessionId)
  });
  const position = training.data?.positions[index];

  async function start() {
    setBusy(true);
    try {
      const created = await createTrainingSession(workspace.player, workspace.platform);
      await navigate({ to: '/practice/$sessionId', params: { sessionId: created.id } });
    } finally {
      setBusy(false);
    }
  }

  async function submit(selected: string) {
    if (!sessionId || !position) return;
    setBusy(true);
    try {
      const result = await submitTrainingAttempt(
        sessionId,
        position.id,
        selected,
        hintOpen ? 1 : 0,
        Date.now() - started
      );
      setEvaluation(result);
    } finally {
      setBusy(false);
    }
  }

  function next() {
    if (!training.data || index + 1 >= training.data.positions.length) {
      void navigate({ to: '/progress' });
      return;
    }
    setIndex((value) => value + 1);
    setMove('');
    setEvaluation(null);
    setHintOpen(false);
  }

  if (!sessionId) return <main className="route-page practice-home">
    <header className="page-header"><div><span className="page-eyebrow">Practice</span><h1>Train mistakes from your games</h1><p>Real positions, Stockfish grading, and adaptive review scheduling.</p></div></header>
    <section className="practice-start">
      <Target size={30} />
      <h2>Your next five positions</h2>
      <p>The queue prioritizes mistakes and blunders from your analyzed history.</p>
      <button className="primary" data-testid="start-practice-btn" disabled={busy} onClick={start}>{busy ? <><Loader2 className="spin" size={17} /> Preparing your session…</> : <><ArrowRight size={17} /> Start practice</>}</button>
    </section>
  </main>;

  if (training.isLoading) return <main className="route-page"><section className="empty-route"><Loader2 className="spin" size={28} /><h2>Loading positions</h2></section></main>;
  if (!position) return <main className="route-page"><section className="empty-route"><CheckCircle2 size={28} /><h2>No positions due</h2><button className="primary" onClick={() => navigate({ to: '/games', search: { import: false } })}>Review games</button></section></main>;

  return <main className="route-page practice-page">
    <header className="page-header"><div><span className="page-eyebrow">Practice · {index + 1} of {training.data?.positions.length}</span><h1>{position.theme.replace(/_/g, ' ')}</h1><p>{position.difficulty} · position from your games</p></div></header>
    <section className="practice-workspace">
      <div className="practice-board"><ChessBoard fen={position.fen} /></div>
      <div className="practice-controls">
        {evaluation ? <>
          <div className={`evaluation-status ${evaluation.correct ? 'correct' : 'incorrect'}`}><strong>{evaluation.correct ? 'Strong move' : evaluation.legal ? 'Try this again' : 'Illegal move'}</strong><span>Best move: {evaluation.best_move}{evaluation.cp_loss == null ? '' : ` · ${evaluation.cp_loss.toFixed(2)} pawn loss`}</span></div>
          <p>{evaluation.explanation}</p>
          <small>Scheduled for {new Date(evaluation.next_review_at).toLocaleDateString()}</small>
          <button className="primary" onClick={next}>{index + 1 < (training.data?.positions.length || 0) ? 'Next position' : 'View progress'} <ArrowRight size={17} /></button>
          <button className="secondary" onClick={() => setEvaluation(null)}><RotateCcw size={16} /> Try again</button>
        </> : <>
          <span className="page-eyebrow">Your move</span>
          <h2 data-testid="practice-prompt">{position.prompt || 'What would you play?'}</h2>
          {position.choices.length ? <div className="move-choices">{position.choices.map((choice) => <button disabled={busy} key={choice} onClick={() => submit(choice)}>{choice}</button>)}</div> : <div className="move-entry"><input value={move} onChange={(event) => setMove(event.target.value)} placeholder="Enter SAN or UCI" /><button className="primary" disabled={!move || busy} onClick={() => submit(move)}>Submit</button></div>}
          {position.hint && position.difficulty === 'beginner' && !hintOpen && <button className="text-action" onClick={() => setHintOpen(true)}>Show hint</button>}
          {hintOpen && position.hint && <p className="quiz-hint">{position.hint}</p>}
        </>}
      </div>
    </section>
  </main>;
}
