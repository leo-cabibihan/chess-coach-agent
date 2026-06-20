import { useMemo, useState } from 'react';
import { CheckSquare2, Loader2, Swords } from 'lucide-react';
import type { GamePreview } from '../lib/types';

type ResultFilter = 'all' | 'win' | 'loss' | 'draw';

const FILTER_LABELS: Record<ResultFilter, string> = {
  all: 'All',
  win: 'Wins',
  loss: 'Losses',
  draw: 'Draws'
};

function resultLabel(result: GamePreview['player_result']) {
  if (result === 'win') return 'Win';
  if (result === 'loss') return 'Loss';
  if (result === 'draw') return 'Draw';
  return 'Unknown';
}

export function GamePicker({
  games,
  selectedIds,
  loading,
  onToggle,
  onSelectAll,
  onClear,
  onAnalyze
}: {
  games: GamePreview[];
  selectedIds: string[];
  loading: boolean;
  onToggle: (gameId: string) => void;
  onSelectAll: () => void;
  onClear: () => void;
  onAnalyze: () => void;
}) {
  const [filter, setFilter] = useState<ResultFilter>('all');
  const visibleGames = useMemo(
    () => filter === 'all' ? games : games.filter((game) => game.player_result === filter),
    [filter, games]
  );

  return (
    <section className="game-picker">
      <div className="game-picker-head">
        <div className="section-heading">
          <CheckSquare2 size={18} />
          <div><strong>Select games</strong><span>{selectedIds.length} selected · maximum 10</span></div>
        </div>
        <div className="picker-actions">
          <button type="button" onClick={onSelectAll}>Select 10</button>
          <button type="button" onClick={onClear}>Clear</button>
        </div>
      </div>

      <div className="result-filters" aria-label="Filter games by result">
        {(['all', 'win', 'loss', 'draw'] as ResultFilter[]).map((value) => (
          <button
            type="button"
            className={filter === value ? 'active' : ''}
            key={value}
            onClick={() => setFilter(value)}
          >
            {FILTER_LABELS[value]}
          </button>
        ))}
      </div>

      <div className="preview-game-list">
        {visibleGames.map((game) => {
          const selected = selectedIds.includes(game.game_id);
          return (
            <label className={selected ? 'preview-game selected' : 'preview-game'} key={game.game_id}>
              <input
                type="checkbox"
                checked={selected}
                onChange={() => onToggle(game.game_id)}
              />
              <span className={`result-dot ${game.player_result}`} />
              <span className="preview-opponent">
                <strong>vs {game.opponent}</strong>
                <small>{game.date.replace(/\./g, '-')} · {game.time_control || 'Unknown control'}</small>
              </span>
              <span className="preview-rating">
                <strong>{game.player_elo || '—'}</strong>
                <small>{game.opponent_elo ? `opp. ${game.opponent_elo}` : 'Elo'}</small>
              </span>
              <span className={`result-label ${game.player_result}`}>{resultLabel(game.player_result)}</span>
            </label>
          );
        })}
        {!visibleGames.length && <div className="picker-empty">No {filter} games in this set.</div>}
      </div>

      <div className="picker-footer">
        <span>{games.length} games found</span>
        <button className="primary" onClick={onAnalyze} disabled={loading || !selectedIds.length}>
          {loading ? <Loader2 className="spin" size={17} /> : <Swords size={17} />}
          Analyze {selectedIds.length || ''} selected
        </button>
      </div>
    </section>
  );
}
