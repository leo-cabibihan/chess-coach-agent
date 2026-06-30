import { useCallback, useEffect, useRef, useState, type RefObject } from 'react';
import { FilesetResolver, GestureRecognizer } from '@mediapipe/tasks-vision';
import {
  type DetectedGesture,
  GESTURE_SCORE_THRESHOLD
} from '../gestures/gestureActions';

const MEDIAPIPE_WASM =
  'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/wasm';
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task';

export function useGestureRecognizer(enabled: boolean, videoRef: RefObject<HTMLVideoElement | null>) {
  const recognizerRef = useRef<GestureRecognizer | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);
  const [gesture, setGesture] = useState<DetectedGesture>('None');
  const [confidence, setConfidence] = useState(0);
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);

  const stop = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    recognizerRef.current?.close();
    recognizerRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    const video = videoRef.current;
    if (video) {
      video.srcObject = null;
    }
    setGesture('None');
    setConfidence(0);
    setStatus('idle');
  }, [videoRef]);

  const detect = useCallback(() => {
    const video = videoRef.current;
    const recognizer = recognizerRef.current;
    if (!video || !recognizer || video.readyState < 2) {
      rafRef.current = requestAnimationFrame(detect);
      return;
    }

    const result = recognizer.recognizeForVideo(video, performance.now());
    const top = result.gestures[0]?.[0];
    const name = (top?.categoryName as DetectedGesture) || 'None';
    const score = top?.score ?? 0;

    if (score >= GESTURE_SCORE_THRESHOLD) {
      setGesture(name);
      setConfidence(score);
    } else {
      setGesture('None');
      setConfidence(0);
    }

    rafRef.current = requestAnimationFrame(detect);
  }, [videoRef]);

  const start = useCallback(async () => {
    setStatus('loading');
    setError(null);

    try {
      const vision = await FilesetResolver.forVisionTasks(MEDIAPIPE_WASM);
      const recognizer = await GestureRecognizer.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: MODEL_URL,
          delegate: 'GPU'
        },
        runningMode: 'VIDEO',
        numHands: 1
      });
      recognizerRef.current = recognizer;

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 640 },
          height: { ideal: 480 }
        },
        audio: false
      });
      streamRef.current = stream;

      const video = videoRef.current;
      if (!video) {
        throw new Error('Camera preview is not ready');
      }

      video.srcObject = stream;
      video.playsInline = true;
      video.muted = true;
      await video.play();

      setStatus('ready');
      rafRef.current = requestAnimationFrame(detect);
    } catch (err) {
      stop();
      setStatus('error');
      setError(err instanceof Error ? err.message : 'Camera or gesture model failed to start');
    }
  }, [detect, stop, videoRef]);

  useEffect(() => {
    if (!enabled) {
      stop();
      return;
    }

    void start();
    return stop;
  }, [enabled, start, stop]);

  return { gesture, confidence, status, error };
}
