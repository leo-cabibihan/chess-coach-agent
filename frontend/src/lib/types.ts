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

export type AnalyzeResponse = {
  analyses: CoachAnalysis[];
  generated_at: string;
};

export type Platform = 'chess.com' | 'lichess';

export type GamePreview = {
  game_id: string;
  pgn: string;
  source: Platform;
  white: string;
  black: string;
  result: string;
  date: string;
  time_control: string;
  link: string;
  player_color: 'white' | 'black' | 'unknown';
  player_result: 'win' | 'loss' | 'draw' | 'unknown';
  player_elo: number | null;
  opponent: string;
  opponent_elo: number | null;
};

export type GamePreviewResponse = {
  username: string;
  platform: Platform;
  games: GamePreview[];
};

export type CoachingOutput = {
  answer: string;
  evidence: string[];
  recommended_move: string | null;
  principle: string;
  drill: string;
  confidence: number;
};

export type ChatResponse = {
  answer: string;
  used_llm: boolean;
  retrieved_notes: string[];
  coaching: CoachingOutput | null;
  tools_used: string[];
  usage: {
    model: string;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    requests: number;
    tool_calls: number;
    estimated_cost_usd: number;
  } | null;
  trace_id: string | null;
  panel?: CoachPanel | null;
};

export type Difficulty = 'beginner' | 'intermediate' | 'advanced';

export type PlayerProfile = {
  id: string;
  platform: Platform | 'pgn';
  username: string;
  current_rating: number | null;
  recurring_themes: Record<string, number>;
  quiz_accuracy: Record<string, number>;
  mastered_positions: number;
  due_positions: number;
};

export type CoachPanel =
  | { type: 'board'; fen: string; title: string; description: string }
  | {
      type: 'quiz'; training_session_id: string; position_id: string; fen: string;
      question: string; choices: string[]; theme: string; difficulty: Difficulty; hint: string | null;
    }
  | { type: 'flashcards'; title: string; cards: Array<{ id: string; fen: string; prompt: string; answer: string; theme: string }> }
  | {
      type: 'evaluation'; position_id: string; fen: string; submitted_move: string;
      best_move: string; legal: boolean; correct: boolean; cp_loss: number | null;
      explanation: string; next_review_at: string;
    }
  | {
      type: 'plan'; training_session_id: string; focus_themes: string[];
      difficulty: Difficulty; position_count: number; estimated_minutes: number;
    };

export type CoachMessage = {
  id: string;
  sequence: number;
  role: 'user' | 'assistant';
  content: string;
  trace_id: string | null;
  created_at: string;
};

export type CoachSession = {
  id: string;
  player: PlayerProfile;
  status: string;
  focus_theme: string;
  summary: string;
  messages: CoachMessage[];
  active_panel: CoachPanel | null;
  created_at: string;
};

export type TrainingPosition = {
  id: string;
  order: number;
  fen: string;
  choices: string[];
  theme: string;
  difficulty: Difficulty;
  prompt: string;
};

export type TrainingSession = {
  id: string;
  player_id: string;
  focus_themes: string[];
  difficulty: Difficulty;
  status: string;
  positions: TrainingPosition[];
};

export type ProgressSummary = {
  player: PlayerProfile;
  total_games: number;
  record: Record<string, number>;
  rating_history: Array<{ date: string; rating: number; result: string }>;
  theme_frequency: Record<string, number>;
  quiz_accuracy: Record<string, number>;
  recent_attempts: number;
  transfer_score: number | null;
};

export type MonitoringSummary = {
  total_events: number;
  event_counts: Record<string, number>;
  feedback_count: number;
  helpful_rate: number | null;
  feedback_themes: Record<string, number>;
  llm_calls: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  average_chat_latency_ms: number | null;
  tool_usage: Record<string, number>;
  stream_failures: number;
  training_sessions: number;
  quiz_attempts: number;
  quiz_accuracy: number | null;
  hint_use_rate: number | null;
  retrieval_methods: Record<string, number>;
  memory_retrievals: number;
  recent_events: Array<Record<string, unknown>>;
};
