export type MoveRecord = {
  ply: number;
  move_number: number;
  color: 'white' | 'black';
  san: string;
  uci: string;
  fen_before: string;
  fen_after: string;
  is_player_move: boolean;
};

export type CriticalMoment = {
  id: string;
  game_id: string;
  ply: number;
  move_number: number;
  phase: 'opening' | 'middlegame' | 'endgame';
  theme: string;
  played_san: string;
  best_san: string | null;
  fen_before: string;
  fen_after: string;
  fen_best: string | null;
  eval_before: number | null;
  eval_after: number | null;
  eval_swing: number | null;
  severity: number;
  summary: string;
  what_happened: string;
  better_plan: string;
  principle: string;
  drill_prompt: string;
};

export type CoachAnalysis = {
  game: {
    game_id: string;
    source: string;
    white: string;
    black: string;
    result: string;
    date: string;
    link: string;
    eco: string;
    time_control: string;
    player_color: string;
    player_result: string;
    player_elo: number | null;
  };
  moves: MoveRecord[];
  moments: CriticalMoment[];
  summary: string;
  training_plan: string[];
  retrieval_notes: string[];
};
