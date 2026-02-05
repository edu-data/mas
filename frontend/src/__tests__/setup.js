import '@testing-library/jest-dom'

// Mock WebSocket
global.WebSocket = class MockWebSocket {
    constructor(url) {
        this.url = url
        this.readyState = WebSocket.OPEN
        setTimeout(() => this.onopen?.(), 0)
    }
    send(data) { }
    close() {
        this.onclose?.()
    }
    static OPEN = 1
    static CLOSED = 3
}

// Mock fetch
global.fetch = vi.fn()

// Mock ResizeObserver for Recharts
global.ResizeObserver = class ResizeObserver {
    observe() { }
    unobserve() { }
    disconnect() { }
}
