export type DetectedGesture =
  | 'Open_Palm'
  | 'Closed_Fist'
  | 'Pointing_Up'
  | 'Thumb_Up'
  | 'Thumb_Down'
  | 'Victory'
  | 'ILoveYou'
  | 'None';

export type PracticePhase = 'answering' | 'evaluated';

export type GestureAction =
  | { type: 'show_hint' }
  | { type: 'submit_choice'; index: number }
  | { type: 'submit_move' }
  | { type: 'next' }
  | { type: 'retry' };

export const GESTURE_COOLDOWN_MS = 1200;
export const GESTURE_SCORE_THRESHOLD = 0.65;

export function shouldAcceptGesture(
  gesture: DetectedGesture,
  lastGesture: DetectedGesture | null,
  lastAt: number,
  now: number
): boolean {
  if (gesture === 'None') return false;
  if (now - lastAt < GESTURE_COOLDOWN_MS) return false;
  if (gesture === lastGesture && now - lastAt < GESTURE_COOLDOWN_MS * 2) return false;
  return true;
}

export function gestureToAction(
  gesture: DetectedGesture,
  phase: PracticePhase,
  choiceCount: number,
  hasHint: boolean,
  hasMoveText: boolean
): GestureAction | null {
  if (gesture === 'None') return null;

  if (phase === 'evaluated') {
    if (gesture === 'Thumb_Up') return { type: 'next' };
    if (gesture === 'Open_Palm') return { type: 'retry' };
    return null;
  }

  if (gesture === 'Open_Palm' && hasHint) return { type: 'show_hint' };
  if (gesture === 'Pointing_Up' && choiceCount >= 1) return { type: 'submit_choice', index: 0 };
  if (gesture === 'Victory' && choiceCount >= 2) return { type: 'submit_choice', index: 1 };
  if (gesture === 'Thumb_Up') {
    if (choiceCount >= 1) return { type: 'submit_choice', index: 0 };
    if (hasMoveText) return { type: 'submit_move' };
  }
  if (gesture === 'Closed_Fist' && hasMoveText) return { type: 'submit_move' };

  return null;
}

export const GESTURE_HINTS: Record<PracticePhase, { gesture: DetectedGesture; label: string }[]> = {
  answering: [
    { gesture: 'Open_Palm', label: 'Show hint' },
    { gesture: 'Pointing_Up', label: 'Pick 1st choice' },
    { gesture: 'Victory', label: 'Pick 2nd choice' },
    { gesture: 'Thumb_Up', label: 'Submit move or 1st choice' },
    { gesture: 'Closed_Fist', label: 'Submit typed move' }
  ],
  evaluated: [
    { gesture: 'Thumb_Up', label: 'Next position' },
    { gesture: 'Open_Palm', label: 'Try again' }
  ]
};

export function formatGestureLabel(gesture: DetectedGesture): string {
  switch (gesture) {
    case 'Open_Palm':
      return 'Open palm';
    case 'Closed_Fist':
      return 'Closed fist';
    case 'Pointing_Up':
      return 'Pointing up';
    case 'Thumb_Up':
      return 'Thumbs up';
    case 'Thumb_Down':
      return 'Thumbs down';
    case 'Victory':
      return 'Peace sign';
    case 'ILoveYou':
      return 'Rock on';
    default:
      return 'No gesture';
  }
}
