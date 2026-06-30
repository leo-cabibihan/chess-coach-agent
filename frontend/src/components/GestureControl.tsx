import { useEffect, useRef } from 'react';
import { Camera, CameraOff, Hand, Loader2 } from 'lucide-react';
import {
  type DetectedGesture,
  type GestureAction,
  type PracticePhase,
  GESTURE_COOLDOWN_MS,
  GESTURE_HINTS,
  formatGestureLabel,
  gestureToAction,
  shouldAcceptGesture
} from '../gestures/gestureActions';
import { useGestureRecognizer } from '../hooks/useGestureRecognizer';

export function GestureControl({
  enabled,
  onToggle,
  phase,
  choiceCount,
  hasHint,
  hasMoveText,
  onAction
}: {
  enabled: boolean;
  onToggle: (next: boolean) => void;
  phase: PracticePhase;
  choiceCount: number;
  hasHint: boolean;
  hasMoveText: boolean;
  onAction: (action: GestureAction) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const lastGestureRef = useRef<DetectedGesture | null>(null);
  const lastAcceptedAtRef = useRef(0);
  const { gesture, confidence, status, error } = useGestureRecognizer(enabled, videoRef);

  useEffect(() => {
    if (!enabled || status !== 'ready' || gesture === 'None') return;

    const now = Date.now();
    if (!shouldAcceptGesture(gesture, lastGestureRef.current, lastAcceptedAtRef.current, now)) {
      return;
    }

    const action = gestureToAction(gesture, phase, choiceCount, hasHint, hasMoveText);
    if (!action) return;

    lastGestureRef.current = gesture;
    lastAcceptedAtRef.current = now;
    onAction(action);
  }, [choiceCount, enabled, gesture, hasHint, hasMoveText, onAction, phase, status]);

  useEffect(() => {
    if (!enabled) {
      lastGestureRef.current = null;
      lastAcceptedAtRef.current = 0;
    }
  }, [enabled]);

  return (
    <section className="gesture-control" aria-label="Gesture recognition controls">
      <div className="gesture-control-head">
        <div>
          <span className="page-eyebrow">Computer vision</span>
          <h3><Hand size={18} /> Gesture control</h3>
        </div>
        <button
          type="button"
          className={enabled ? 'secondary gesture-toggle active' : 'secondary gesture-toggle'}
          data-testid="gesture-toggle"
          onClick={() => onToggle(!enabled)}
        >
          {enabled ? <CameraOff size={16} /> : <Camera size={16} />}
          {enabled ? 'Disable camera' : 'Enable camera'}
        </button>
      </div>

      {enabled && (
        <div className="gesture-control-body">
          <div className="gesture-preview-wrap">
            <video ref={videoRef} className="gesture-preview" playsInline muted aria-hidden="true" />
            <div className="gesture-overlay">
              {status === 'loading' && (
                <span className="gesture-status"><Loader2 className="spin" size={16} /> Loading model…</span>
              )}
              {status === 'ready' && (
                <span className="gesture-status live">
                  {formatGestureLabel(gesture)}
                  {confidence > 0 ? ` · ${Math.round(confidence * 100)}%` : ''}
                </span>
              )}
              {status === 'error' && <span className="gesture-status error">{error}</span>}
            </div>
          </div>

          <ul className="gesture-hints">
            {GESTURE_HINTS[phase].map((hint) => (
              <li key={hint.gesture} className={gesture === hint.gesture ? 'active' : ''}>
                <strong>{formatGestureLabel(hint.gesture)}</strong>
                <span>{hint.label}</span>
              </li>
            ))}
          </ul>
          <p className="gesture-note">
            Gestures are debounced every {GESTURE_COOLDOWN_MS / 1000}s. Hold each pose clearly in frame.
          </p>
        </div>
      )}
    </section>
  );
}
