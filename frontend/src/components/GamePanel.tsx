import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Trophy } from 'lucide-react';
import { ChessBoard } from './ChessBoard';
import type { CoachAnalysis, CriticalMoment } from '../lib/types';

export function GamePanel({
  analysis,
  selectedMoment,
  currentPly,
  setCurrentPly
}: {
  analysis: CoachAnalysis | null;
  selectedMoment: CriticalMoment | null;
  currentPly: number;
  setCurrentPly: (ply: number) => void;
}) {
  const moves = analysis?.moves || [];
  const clampedPly = Math.max(0, Math.min(currentPly, moves.length));
  const fallbackFen = 'rn1qkbnr/ppp2ppp/4p3/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 3';
  const fen =
    (clampedPly === 0
      ? moves[0]?.fen_before
      : moves[clampedPly - 1]?.fen_after) || fallbackFen;
  const selectedMomentIds = new Set(analysis?.moments.map((moment) => moment.ply) || []);

  return (
    <section className="panel game-panel">
      <div className="panel-title"><Trophy size={18} /> Chess Board</div>
      <div className="player-pill black">
        <span>♛</span>
        <strong>{analysis?.game.black || 'Black'}</strong>
        <small>Black</small>
      </div>
      <ChessBoard fen={fen} />
      <div className="player-pill white">
        <span>♕</span>
        <strong>{analysis?.game.white || 'White'}</strong>
        <small>White</small>
      </div>
      <div className="board-controls">
        <button title="Start" onClick={() => setCurrentPly(0)} disabled={!moves.length || clampedPly === 0}><ChevronsLeft size={16} /></button>
        <button title="Previous move" onClick={() => setCurrentPly(Math.max(0, clampedPly - 1))} disabled={!moves.length || clampedPly === 0}><ChevronLeft size={16} /></button>
        <span className="ply-counter">{moves.length ? `${clampedPly}/${moves.length}` : '0/0'}</span>
        <button title="Next move" onClick={() => setCurrentPly(Math.min(moves.length, clampedPly + 1))} disabled={!moves.length || clampedPly === moves.length}><ChevronRight size={16} /></button>
        <button title="End" onClick={() => setCurrentPly(moves.length)} disabled={!moves.length || clampedPly === moves.length}><ChevronsRight size={16} /></button>
      </div>
      <div className="move-history">
        <div className="history-head">
          <strong>Move History</strong>
          <span>{analysis ? `${analysis.game.result} • ${analysis.game.player_result}` : 'Load a game'}</span>
        </div>
        <div className="history-grid">
          <div className="grid-label">#</div>
          <div className="grid-label">White</div>
          <div className="grid-label">Black</div>
          {Array.from({ length: Math.ceil(moves.length / 2) }, (_, i) => {
            const white = moves[i * 2];
            const black = moves[i * 2 + 1];
            return (
              <div className="move-row" key={i}>
                <span>{i + 1}.</span>
                <button
                  className={[
                    white?.ply === clampedPly ? 'current' : '',
                    white && selectedMomentIds.has(white.ply) ? 'moment-mark' : ''
                  ].filter(Boolean).join(' ')}
                  onClick={() => white && setCurrentPly(white.ply)}
                >
                  {white?.san || ''}
                </button>
                <button
                  className={[
                    black?.ply === clampedPly ? 'current' : '',
                    black && selectedMomentIds.has(black.ply) ? 'moment-mark' : ''
                  ].filter(Boolean).join(' ')}
                  onClick={() => black && setCurrentPly(black.ply)}
                >
                  {black?.san || ''}
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
