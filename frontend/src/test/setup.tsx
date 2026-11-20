import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock Leaflet
vi.mock('leaflet', () => ({
  Map: vi.fn(),
  TileLayer: vi.fn(),
  GeoJSON: vi.fn(),
  latLng: vi.fn(),
  latLngBounds: vi.fn(),
  point: vi.fn(),
  DomUtil: {
    create: vi.fn(),
    get: vi.fn(),
  },
  DomEvent: {
    on: vi.fn(),
    off: vi.fn(),
  },
  Browser: {
    any3d: false,
  },
}))

// Mock react-leaflet
vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: any) => <div data-testid="map-container">{children}</div>,
  TileLayer: () => <div data-testid="tile-layer" />,
  GeoJSON: () => <div data-testid="geojson" />,
  useMap: () => ({
    setView: vi.fn(),
    addLayer: vi.fn(),
    removeLayer: vi.fn(),
    getZoom: vi.fn(),
    getCenter: vi.fn(),
  }),
  useMapEvents: vi.fn(),
}))

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
Object.defineProperty(window, 'localStorage', { value: localStorageMock })

// Mock fetch
global.fetch = vi.fn()

// Mock ResizeObserver
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))