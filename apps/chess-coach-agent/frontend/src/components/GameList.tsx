import { ListChecks } from 'lucide-react';
import type { CoachAnalysis } from '../lib/types';

function resultLabel(result: string) {
  if (result === 'win') return 'Win';
  if (result === 'loss') return 'Loss';
  if (result === 'draw') return 'Draw';
  return 'Unknown';
}

export function GameList({
  analyses,
  activeIndex,
  onSelect
}: {
  analyses: CoachAnalysis[];
  activeIndex: number;
  onSelect: (index: number) => void;
}) {
  if (!analyses.length) return null;

  return (
    <section className="game-list-panel">
      <div className="game-list-head">
        <div className="panel-title"><ListChecks size={18} /> Games</div>
        <span>{analyses.length} analyzed</span>
      </div>
      <div className="game-list">
        {analyses.map((item, index) => {
          const opponent = item.game.player_color === 'white' ? item.game.black : item.game.white;
          const title = `${item.game.white} vs ${item.game.black}`;
          const themes = Array.from(new Set(item.moments.map((moment) => moment.theme.replace('_', ' ')))).slice(0, 2);
          return (
            <button
              className={index === activeIndex ? 'active' : ''}
              key={item.game.game_id}
              onClick={() => onSelect(index)}
            >
              <strong>{title}</strong>
              <span>{item.game.date} • {resultLabel(item.game.player_result)}{opponent ? ` • vs ${opponent}` : ''}</span>
              <small>
                {item.game.player_elo ? `${item.game.player_elo} Elo` : item.game.time_control || 'PGN'}
                {' · '}
                {item.moments.length} moments
                {themes.length ? ` · ${themes.join(', ')}` : ''}
              </small>
            </button>
          );
        })}
      </div>
    </section>
  );
}
