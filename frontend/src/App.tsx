import { useEffect, useMemo, useState } from 'react';
import { Activity, AlertCircle, Database, Loader2, MessageCircle, Upload } from 'lucide-react';
import { AnalysisPanel } from './components/AnalysisPanel';
import { GamePanel } from './components/GamePanel';
import { analyzeGame, askCoach, getSample, importGames } from './lib/api';
import type { CoachAnalysis, CriticalMoment, Platform } from './lib/types';
import './styles.css';

function App() {
  const [pgn, setPgn] = useState('');
  const [player, setPlayer] = useState('kfctofu');
  const [analysis, setAnalysis] = useState<CoachAnalysis | null>(null);
  const [selectedMoment, setSelectedMoment] = useState<CriticalMoment | null>(null);
  const [currentPly, setCurrentPly] = useState(0);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('Ready');
  const [error, setError] = useState('');
  const [platform, setPlatform] = useState<Platform>('chess.com');
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

  const gameStats = useMemo(() => {
    if (!analysis) return null;
    const playerSide = analysis.game.player_color === 'unknown' ? 'player' : analysis.game.player_color;
    return [
      `${analysis.moves.length} plies`,
      `${analysis.moments.length} moments`,
      `${analysis.game.player_result} as ${playerSide}`,
      analysis.game.player_elo ? `${analysis.game.player_elo} Elo` : analysis.game.time_control || 'PGN'
    ];
  }, [analysis]);

  async function runAnalysis() {
    setLoading(true);
    setError('');
    setStatus('Analyzing PGN...');
    setCoachAnswer('');
    try {
      const result = await analyzeGame(pgn, player);
      setAnalysis(result);
      setSelectedMoment(result.moments[0] || null);
      setCurrentPly(result.moments[0]?.ply || 0);
      setStatus(`Found ${result.moments.length} coachable moments`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
      setStatus('Could not analyze PGN');
    } finally {
      setLoading(false);
    }
  }

  async function runImport() {
    if (!player.trim()) return;
    setLoading(true);
    setError('');
    setStatus(`Importing latest ${platform} game...`);
    setCoachAnswer('');
    try {
      const result = await importGames(player, platform);
      setAnalysis(result);
      setSelectedMoment(result.moments[0] || null);
      setCurrentPly(result.moments[0]?.ply || 0);
      setStatus(`Imported ${platform} game and found ${result.moments.length} moments`);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Could not import from ${platform}`);
      setStatus('Import failed');
    } finally {
      setLoading(false);
    }
  }

  async function ask() {
    if (!question.trim()) return;
    setLoading(true);
    setError('');
    setStatus('Asking MiniMax coach...');
    try {
      const answer = await askCoach(question, analysis);
      setCoachAnswer(answer);
      setStatus('Coach answer ready');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Coach chat failed');
      setStatus('Coach chat failed');
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
          {gameStats && (
            <div className="stat-row">
              {gameStats.map((stat) => <span key={stat}>{stat}</span>)}
            </div>
          )}
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
        <label>
          Import source
          <select value={platform} onChange={(event) => setPlatform(event.target.value as Platform)}>
            <option value="chess.com">Chess.com</option>
            <option value="lichess">Lichess</option>
          </select>
        </label>
        <label className="pgn-input">
          PGN input
          <textarea value={pgn} onChange={(event) => setPgn(event.target.value)} rows={4} />
        </label>
        <div className="input-actions">
          <button className="secondary" onClick={runImport} disabled={loading || !player.trim()}>
            <Database size={16} />
            Import latest
          </button>
          <span className={error ? 'status error' : 'status'}>{error ? <AlertCircle size={15} /> : null}{error || status}</span>
        </div>
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
          <button onClick={ask} disabled={loading || !question.trim()}>
            {loading ? <Loader2 className="spin" size={16} /> : null}
            Ask
          </button>
        </div>
        {coachAnswer && <p className="coach-answer">{coachAnswer}</p>}
      </section>
    </main>
  );
}

export default App;
