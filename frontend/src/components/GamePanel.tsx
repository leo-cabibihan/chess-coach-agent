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
  const fen =
    selectedMoment?.fen_before ||
    analysis?.moves[Math.max(0, Math.min(currentPly - 1, analysis.moves.length - 1))]?.fen_after ||
    'rn1qkbnr/ppp2ppp/4p3/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 3';
  const moves = analysis?.moves || [];

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
        <button onClick={() => setCurrentPly(0)}><ChevronsLeft size={16} /></button>
        <button onClick={() => setCurrentPly(Math.max(0, currentPly - 1))}><ChevronLeft size={16} /></button>
        <button onClick={() => setCurrentPly(Math.min(moves.length, currentPly + 1))}><ChevronRight size={16} /></button>
        <button onClick={() => setCurrentPly(moves.length)}><ChevronsRight size={16} /></button>
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
                <button className={white?.ply === selectedMoment?.ply ? 'highlight' : ''} onClick={() => white && setCurrentPly(white.ply)}>{white?.san || ''}</button>
                <button className={black?.ply === selectedMoment?.ply ? 'highlight' : ''} onClick={() => black && setCurrentPly(black.ply)}>{black?.san || ''}</button>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
