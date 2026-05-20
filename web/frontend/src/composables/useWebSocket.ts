import { ref, onScopeDispose } from 'vue'
import { getWebSocketUrl } from '@/api'
import { getToken, promptForToken } from '@/lib/auth'

export interface UseWebSocketOptions<T> {
  /** Auto-reconnect with exponential backoff on unexpected close. */
  autoReconnect?: boolean
  /** Called for each parsed JSON payload from the server. */
  onMessage?: (data: T) => void
  /** Called when the socket transitions to an open state. */
  onOpen?: () => void
  /** Called once the socket closes for any reason (including by design). */
  onClose?: () => void
  /** Called when the socket errors. */
  onError?: (err: Event) => void
}

export function useWebSocket<T = unknown>(path: string, options: UseWebSocketOptions<T> = {}) {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const lastMessage = ref<T | null>(null)

  let reconnectAttempts = 0
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let intentionallyClosed = false

  function clearReconnectTimer() {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  function scheduleReconnect() {
    if (intentionallyClosed || !options.autoReconnect) return
    const delay = Math.min(15000, 500 * 2 ** reconnectAttempts)
    reconnectAttempts += 1
    reconnectTimer = setTimeout(connect, delay)
  }

  function connect() {
    clearReconnectTimer()
    intentionallyClosed = false

    const url = getWebSocketUrl(path)
    const token = getToken()
    const protocols = token ? ['mettle.bearer', token] : []
    const socket = new WebSocket(url, protocols)
    ws.value = socket

    socket.onopen = () => {
      isConnected.value = true
      reconnectAttempts = 0
      options.onOpen?.()
    }

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as T
        lastMessage.value = data
        options.onMessage?.(data)
      } catch {
        // Non-JSON message (ping/pong) — ignored.
      }
    }

    socket.onerror = (err) => {
      options.onError?.(err)
    }

    socket.onclose = (event) => {
      if (event.code === 1008) {
        promptForToken()
      }
      isConnected.value = false
      options.onClose?.()
      scheduleReconnect()
    }
  }

  function disconnect() {
    intentionallyClosed = true
    clearReconnectTimer()
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    isConnected.value = false
  }

  function send(data: unknown) {
    if (ws.value && isConnected.value) {
      ws.value.send(typeof data === 'string' ? data : JSON.stringify(data))
    }
  }

  // Clean up automatically when the calling composable's scope is disposed,
  // e.g. when the component using it is unmounted or the user navigates away.
  onScopeDispose(() => disconnect())

  return {
    connect,
    disconnect,
    send,
    isConnected,
    lastMessage,
  }
}
