// Session types
export type SessionState =
  | 'waiting_for_prompt_playback'
  | 'recording'
  | 'aligning'
  | 'user_paused'
  | 'complete';

export interface AyahText {
  surah: number;
  ayah: number;
  juz: number;
  audio_url: string;
  text_uthmani: string;
  text_normalized: string;
  text_tokens: string[];
}

export interface ReviewSession {
  id: string;
  state: SessionState;
  juz_range: [number, number];
  num_ayahs_to_recite: number;
  prompt_ayah: AyahText;
  expected_ayahs: AyahText[];
}

// Mistake types
export type MistakeType =
  | 'wrong_word'
  | 'skipped'
  | 'added'
  | 'repetition'
  | 'out_of_order'
  | 'jumped_ahead'
  | 'early_stop'
  | 'self_corrected'
  | 'low_confidence';

export interface Mistake {
  mistake_type: MistakeType;
  ayah: [number, number]; // [surah, ayah]
  word_index: number;
  expected: string;
  received: string | null;
  confidence: number;
  is_penalty: boolean;
  timestamp_ms: number;
}

// WebSocket message types - Client to Server
export interface AudioChunkMessage {
  type: 'audio_chunk';
  data: string; // base64 encoded audio
  timestamp_ms: number;
  is_final: boolean;
}

export interface RecordingControlMessage {
  type: 'start_recording' | 'pause_recording' | 'stop_recording';
}

export type ClientMessage = AudioChunkMessage | RecordingControlMessage;

// WebSocket message types - Server to Client
export interface WordStatus {
  word: string;
  status: 'correct' | 'incorrect' | 'tentative';
  index: number;
}

export interface TranscriptionMessage {
  type: 'transcription';
  confirmed_words: WordStatus[];
  tentative_words: WordStatus[];
}

export interface MistakeMessage {
  type: 'mistake';
  mistake_type: MistakeType;
  word_index: number;
  expected: string;
  received: string;
  confidence: number;
  is_penalty: boolean;
}

export interface SelfCorrectionMessage {
  type: 'self_correction';
  word_index: number;
  message: string;
}

export interface AyahCompleteMessage {
  type: 'ayah_complete';
  ayah: { surah: number; ayah: number };
  status: 'correct' | 'incorrect';
  words_correct: number;
  words_total: number;
}

export interface SessionCompleteMessage {
  type: 'session_complete';
  summary: SessionSummary;
}

export interface SessionSummary {
  ayahs_tested: number;
  ayahs_correct: number;
  total_words: number;
  words_correct: number;
  mistakes: Mistake[];
}

export type ServerMessage =
  | TranscriptionMessage
  | MistakeMessage
  | SelfCorrectionMessage
  | AyahCompleteMessage
  | SessionCompleteMessage;

// Juz info type
export interface JuzInfo {
  juz_number: number;
  start_surah: number;
  start_ayah: number;
  end_surah: number;
  end_ayah: number;
  total_ayahs: number;
}

// API response types
export interface StartSessionRequest {
  juz_start: number;
  juz_end: number;
  num_ayahs?: number;
  feedback_mode?: 'immediate' | 'gentle' | 'post_ayah' | 'post_session';
}

export interface StartSessionResponse {
  session_id: string;
  prompt_ayah: AyahText;
  expected_ayahs: AyahText[];
}

// Connection state for WebSocket
export type ConnectionState = 'connecting' | 'connected' | 'disconnected' | 'error';

// Recording state
export type RecordingState = 'idle' | 'recording' | 'paused';
