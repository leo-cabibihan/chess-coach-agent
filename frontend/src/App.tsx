import { useEffect, useMemo, useState } from 'react';
import { Activity, Loader2, MessageCircle, Upload } from 'lucide-react';
import { AnalysisPanel } from './components/AnalysisPanel';
import { GamePanel } from './components/GamePanel';
import { analyzeGame, askCoach, getSample } from './lib/api';
import type { CoachAnalysis, CriticalMoment } from './lib/types';
import './styles.css';

function App() {
  const [pgn, setPgn] = useState('');
  const [player, setPlayer] = useState('kfctofu');
  const [analysis, setAnalysis] = useState<CoachAnalysis | null>(null);
  const [selectedMoment, setSelectedMoment] = useState<CriticalMoment | null>(null);
  const [currentPly, setCurrentPly] = useState(0);
  const [loading, setLoading] = useState(false);
  const [question, setQuestion] = useState('');
  const [coachAnswer, setCoachAnswer] = useState('');

  useEffect(() => {
    getSample().then((sample) => {
      setPgn(sample.pgn);
      setPlayer(sample.player);
    }).catch(() => undefined);
  }, []);

  const headline = useMemo(() => {
    if (!analysis) return 'Personal chess improvement from your own games';
    return `${analysis.game.white} vs ${analysis.game.black} • ${analysis.game.date}`;
  }, [analysis]);

  async function runAnalysis() {
    setLoading(true);
    setCoachAnswer('');
    try {
      const result = await analyzeGame(pgn, player);
      setAnalysis(result);
      setSelectedMoment(result.moments[0] || null);
      setCurrentPly(result.moments[0]?.ply || 0);
    } finally {
      setLoading(false);
    }
  }

  async function ask() {
    if (!question.trim()) return;
    setLoading(true);
    try {
      const answer = await askCoach(question, analysis);
      setCoachAnswer(answer);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header className="app-header">
        <div>
          <span className="eyebrow"><Activity size={15} /> Chess Coach Agent</span>
          <h1>{headline}</h1>
        </div>
        <button className="primary" onClick={runAnalysis} disabled={loading || !pgn.trim()}>
          {loading ? <Loader2 className="spin" size={17} /> : <Upload size={17} />}
          Analyze PGN
        </button>
      </header>

      <section className="input-strip">
        <label>
          Player username
          <input value={player} onChange={(event) => setPlayer(event.target.value)} />
        </label>
        <label className="pgn-input">
          PGN input
          <textarea value={pgn} onChange={(event) => setPgn(event.target.value)} rows={4} />
        </label>
      </section>

      <div className="layout">
        <AnalysisPanel analysis={analysis} selectedMoment={selectedMoment} onSelectMoment={(moment) => {
          setSelectedMoment(moment);
          setCurrentPly(moment.ply);
        }} />
        <GamePanel analysis={analysis} selectedMoment={selectedMoment} currentPly={currentPly} setCurrentPly={setCurrentPly} />
      </div>

      <section className="coach-chat">
        <div className="panel-title"><MessageCircle size={18} /> Ask the coach</div>
        <div className="chat-row">
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask why the tactic works, what to drill, or how to avoid this pattern"
          />
          <button onClick={ask} disabled={loading}>Ask</button>
        </div>
        {coachAnswer && <p className="coach-answer">{coachAnswer}</p>}
      </section>
    </main>
  );
}

export default App;
