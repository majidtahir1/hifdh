import { useState, useRef, useCallback, useEffect } from 'react';
import type { ConnectionState, ServerMessage, ClientMessage } from '../types';

interface UseWebSocketOptions {
  onMessage?: (message: ServerMessage) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

interface UseWebSocketReturn {
  connectionState: ConnectionState;
  connect: (sessionId: string) => void;
  disconnect: () => void;
  sendMessage: (message: ClientMessage) => void;
  sendBinary: (data: ArrayBuffer) => void;
}

/**
 * Custom hook for WebSocket connection management
 * Handles connection, reconnection, and message sending/receiving
 */
export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectAttempts = 3,
    reconnectInterval = 2000,
  } = options;

  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const sessionIdRef = useRef<string | null>(null);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const connect = useCallback((sessionId: string) => {
    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    sessionIdRef.current = sessionId;
    setConnectionState('connecting');
    reconnectCountRef.current = 0;

    // Determine WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/session/${sessionId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionState('connected');
      reconnectCountRef.current = 0;
      onOpen?.();
    };

    ws.onclose = (event) => {
      setConnectionState('disconnected');
      onClose?.();

      // Attempt reconnection if not intentionally closed
      if (!event.wasClean && reconnectCountRef.current < reconnectAttempts && sessionIdRef.current) {
        reconnectCountRef.current += 1;
        reconnectTimeoutRef.current = window.setTimeout(() => {
          if (sessionIdRef.current) {
            connect(sessionIdRef.current);
          }
        }, reconnectInterval);
      }
    };

    ws.onerror = (error) => {
      setConnectionState('error');
      onError?.(error);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as ServerMessage;
        onMessage?.(message);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };
  }, [onMessage, onOpen, onClose, onError, reconnectAttempts, reconnectInterval]);

  const disconnect = useCallback(() => {
    sessionIdRef.current = null;
    reconnectCountRef.current = reconnectAttempts; // Prevent reconnection

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnectionState('disconnected');
  }, [reconnectAttempts]);

  const sendMessage = useCallback((message: ClientMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Cannot send message.');
    }
  }, []);

  const sendBinary = useCallback((data: ArrayBuffer) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    } else {
      console.warn('WebSocket is not connected. Cannot send binary data.');
    }
  }, []);

  return {
    connectionState,
    connect,
    disconnect,
    sendMessage,
    sendBinary,
  };
}

export default useWebSocket;
