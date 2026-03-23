import type { StartSessionRequest, StartSessionResponse, JuzInfo } from '../types';

const API_BASE = '/api';

/**
 * Start a new review session
 */
export async function startSession(request: StartSessionRequest): Promise<StartSessionResponse> {
  const response = await fetch(`${API_BASE}/session/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`Failed to start session: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get information about a specific juz
 */
export async function getJuzInfo(juzNumber: number): Promise<JuzInfo> {
  const response = await fetch(`${API_BASE}/juz/${juzNumber}`);

  if (!response.ok) {
    throw new Error(`Failed to get juz info: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get all juz information (1-30)
 */
export async function getAllJuzInfo(): Promise<JuzInfo[]> {
  const response = await fetch(`${API_BASE}/juz`);

  if (!response.ok) {
    throw new Error(`Failed to get all juz info: ${response.statusText}`);
  }

  return response.json();
}
