import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { Loader2, MessageCircle, Sparkles, Target } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { ChessBoard } from '../components/ChessBoard';
import {
  createCoachSession,
  getCoachSession,
  readCoachEvents,
  sendCoachMessage,
  submitTrainingAttempt
} from '../lib/api';
import type { CoachPanel } from '../lib/types';
import { useWorkspace } from '../workspace/WorkspaceContext';

function PanelView({ panel, onPanel }: { panel: CoachPanel | null; onPanel: (panel: CoachPanel) => void }) {
  const [move, setMove] = useState('');
  const [busy, setBusy] = useState(false);
  const [hintOpen, setHintOpen] = useState(false);
  const started = useMemo(() => Date.now(), [panel?.type === 'quiz' ? panel.position_id : 'none']);
  if (!panel) return <div className="coach-panel-empty"><Target size={28} /><h2>Learning panel</h2><p>Ask for a quiz, training plan, or explanation from your games.</p></div>;
  if (panel.type === 'board') return <div className="learning-panel"><div className="learning-panel-head"><span>Position</span><h2>{panel.title}</h2></div><ChessBoard fen={panel.fen} /><p>{panel.description}</p></div>;
  if (panel.type === 'quiz') {
    const quiz = panel;
    async function submit(selected: string) {
      setBusy(true);
      try {
        const result = await submitTrainingAttempt(quiz.training_session_id, quiz.position_id, selected, hintOpen ? 1 : 0, Date.now() - started);
        onPanel(result);
      } finally { setBusy(false); }
    }
    return <div className="learning-panel quiz-panel">
      <div className="learning-panel-head"><span>{panel.theme.replace(/_/g, ' ')} · {panel.difficulty}</span><h2>{panel.question}</h2></div>
      <ChessBoard fen={panel.fen} />
      {panel.choices.length ? <div className="move-choices">{panel.choices.map((choice) => <button disabled={busy} key={choice} onClick={() => submit(choice)}>{choice}</button>)}</div> : <div className="move-entry"><input value={move} onChange={(event) => setMove(event.target.value)} placeholder="Enter SAN or UCI" /><button className="primary" disabled={!move || busy} onClick={() => submit(move)}>Submit</button></div>}
      {panel.hint && <button className="text-action" onClick={() => setHintOpen(true)}>Show hint</button>}
      {hintOpen && panel.hint && <p className="quiz-hint">{panel.hint}</p>}
    </div>;
  }
  if (panel.type === 'evaluation') return <div className="learning-panel"><div className={`evaluation-status ${panel.correct ? 'correct' : 'incorrect'}`}><strong>{panel.correct ? 'Strong move' : panel.legal ? 'Try this again' : 'Illegal move'}</strong><span>Best move: {panel.best_move}{panel.cp_loss == null ? '' : ` · ${panel.cp_loss.toFixed(2)} pawn loss`}</span></div><ChessBoard fen={panel.fen} /><p>{panel.explanation}</p><small>Scheduled for {new Date(panel.next_review_at).toLocaleDateString()}</small></div>;
  if (panel.type === 'flashcards') return <div className="learning-panel"><div className="learning-panel-head"><span>Flashcards</span><h2>{panel.title}</h2></div>{panel.cards.map((card) => <div className="flashcard-row" key={card.id}><ChessBoard fen={card.fen} /><div><strong>{card.prompt}</strong><p>{card.answer}</p></div></div>)}</div>;
  return <div className="learning-panel"><div className="learning-panel-head"><span>Training plan</span><h2>{panel.focus_themes.map((item) => item.replace(/_/g, ' ')).join(', ')}</h2></div><div className="plan-summary"><strong>{panel.position_count}</strong><span>positions</span><strong>{panel.estimated_minutes}</strong><span>minutes</span><strong>{panel.difficulty}</strong><span>difficulty</span></div></div>;
}

export function CoachWorkspacePage({ sessionId }: { sessionId?: string }) {
  const workspace = useWorkspace();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [question, setQuestion] = useState('');
  const [streamed, setStreamed] = useState('');
  const [activity, setActivity] = useState<string[]>([]);
  const [panel, setPanel] = useState<CoachPanel | null>(null);
  const [sending, setSending] = useState(false);
  const session = useQuery({ queryKey: ['coach-session', sessionId], queryFn: () => getCoachSession(sessionId!), enabled: Boolean(sessionId) });
  useEffect(() => { if (session.data?.active_panel) setPanel(session.data.active_panel); }, [session.data?.active_panel]);

  if (!sessionId) return <main className="route-page coach-start"><div className="coach-start-copy"><span className="page-eyebrow">Persistent coach</span><h1>Continue learning with context</h1><p>The coach remembers your recurring themes, practice results, and positions due for review.</p><button className="primary" onClick={async () => { const created = await createCoachSession(workspace.player, workspace.platform); await navigate({ to: '/coach/$sessionId', params: { sessionId: created.id } }); }}><Sparkles size={17} /> Start coaching session</button></div></main>;
  const activeSessionId = sessionId;

  async function ask() {
    if (!question.trim()) return;
    setSending(true); setStreamed(''); setActivity([]);
    try {
      const messageId = await sendCoachMessage(activeSessionId, question);
      setQuestion('');
      await readCoachEvents(activeSessionId, messageId, (type, payload) => {
        if (type === 'text_delta') setStreamed((value) => value + String(payload.text || ''));
        if (type === 'tool_started') setActivity((value) => [...value, `Using ${String(payload.tool).replace(/_/g, ' ')}...`]);
        if (type === 'panel_ready') setPanel(payload as unknown as CoachPanel);
      });
      await queryClient.invalidateQueries({ queryKey: ['coach-session', sessionId] });
      await session.refetch();
      setStreamed('');
      setActivity([]);
    } finally { setSending(false); }
  }

  return <main className="route-page coach-session-page">
    <header className="page-header"><div><span className="page-eyebrow">Adaptive coach</span><h1>{session.data?.focus_theme.replace(/_/g, ' ') || 'Learning session'}</h1><p>{workspace.player} · persistent conversation and practice context</p></div></header>
    <div className="coach-session-layout">
      <section className="conversation-pane">
        <div className="message-list">
          {session.data?.messages.map((message) => <article className={`message ${message.role}`} key={message.id}><span>{message.role === 'user' ? 'You' : 'Coach'}</span><ReactMarkdown>{message.content}</ReactMarkdown></article>)}
          {activity.length > 0 && <div className="tool-activity">{activity.map((item, index) => <span key={`${item}-${index}`}>{item}</span>)}</div>}
          {streamed && <article className="message assistant"><span>Coach</span><ReactMarkdown>{streamed}</ReactMarkdown></article>}
        </div>
        <div className="coach-composer"><textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={3} placeholder="Ask about a game, request a quiz, or build a training plan" /><button className="primary" onClick={ask} disabled={sending || !question.trim()}>{sending ? <Loader2 className="spin" size={17} /> : <MessageCircle size={17} />} Send</button></div>
      </section>
      <aside className="context-pane"><PanelView panel={panel} onPanel={setPanel} /></aside>
    </div>
  </main>;
}
