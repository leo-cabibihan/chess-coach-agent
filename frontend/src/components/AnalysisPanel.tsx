import { BookOpen, Brain, CircleDot, Target, ThumbsDown, ThumbsUp } from 'lucide-react';
import type { CoachAnalysis, CriticalMoment } from '../lib/types';

export function AnalysisPanel({
  analysis,
  selectedMoment,
  onSelectMoment,
  onFeedback,
  feedbackStatus
}: {
  analysis: CoachAnalysis | null;
  selectedMoment: CriticalMoment | null;
  onSelectMoment: (moment: CriticalMoment) => void;
  onFeedback: (moment: CriticalMoment, rating: 'helpful' | 'not_helpful') => void;
  feedbackStatus: string;
}) {
  if (!analysis) {
    return (
      <section className="panel empty-state">
        <div className="panel-title"><Brain size={18} /> AI Analysis</div>
        <p>Load the sample or paste a PGN to generate critical moments, coach notes, and drills.</p>
      </section>
    );
  }

  return (
    <section className="panel analysis-panel">
      <div className="panel-title"><Brain size={18} /> AI Analysis</div>
      <div className="summary-box">
        <BookOpen size={18} />
        <div>
          <strong>Summary</strong>
          <p>{analysis.summary}</p>
        </div>
      </div>

      <div className="moment-tabs">
        {analysis.moments.map((moment, index) => (
          <button
            className={selectedMoment?.id === moment.id ? 'active' : ''}
            key={moment.id}
            onClick={() => onSelectMoment(moment)}
          >
            Moment {index + 1}
          </button>
        ))}
      </div>

      {selectedMoment && (
        <>
          <div className="card critical-card">
            <div className="card-heading">
              <span><CircleDot size={17} /> Critical Moment Analysis</span>
              <span className="badge">{selectedMoment.phase}</span>
              {selectedMoment.eval_swing !== null && (
                <span className="score-badge">{selectedMoment.eval_swing.toFixed(2)}</span>
              )}
            </div>
            <div className="move-comparison">
              <div className="move-box bad">
                <span>Move Actually Played</span>
                <strong>{selectedMoment.move_number}... {selectedMoment.played_san}</strong>
                <small>What happened in the game</small>
              </div>
              <div className="move-box good">
                <span>Recommended Best Move</span>
                <strong>{selectedMoment.move_number}... {selectedMoment.best_san || 'Candidate move'}</strong>
                <small>What the coach suggests checking</small>
              </div>
            </div>
            <div className="moment-feedback">
              <span>{feedbackStatus || 'Was this coaching useful?'}</span>
              <button
                aria-label="Mark coaching helpful"
                title="Helpful"
                onClick={() => onFeedback(selectedMoment, 'helpful')}
              >
                <ThumbsUp size={17} />
              </button>
              <button
                aria-label="Mark coaching not helpful"
                title="Not helpful"
                onClick={() => onFeedback(selectedMoment, 'not_helpful')}
              >
                <ThumbsDown size={17} />
              </button>
            </div>
          </div>

          <div className="card prose-card">
            <h3><Target size={17} /> Analysis</h3>
            <div className="analysis-block">
              <h4>What happened</h4>
              <p>{selectedMoment.what_happened}</p>
            </div>
            <div className="analysis-block">
              <h4>Better plan</h4>
              <p>{selectedMoment.better_plan}</p>
            </div>
            <div className="analysis-block">
              <h4>Principle</h4>
              <p>{selectedMoment.principle}</p>
            </div>
            <div className="analysis-block">
              <h4>Daily challenge</h4>
              <p>{selectedMoment.drill_prompt}</p>
            </div>
          </div>

          <div className="card">
            <h3>Training plan</h3>
            <ul className="training-list">
              {analysis.training_plan.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </div>
        </>
      )}
    </section>
  );
}
