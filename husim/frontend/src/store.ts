import { create } from 'zustand'

export interface OptimizedParams {
  max_speed_factor: number
  friction_coefficient: number
  braking_distance_factor: number
  visibility_range: number
  agent_speed_factor: number
  safety_margin_factor: number
  recommended_algorithm: string
  risk_level: string
  warnings: string[]
  optimization_notes: string
}

export interface WeatherInput {
  weather_type: string
  temperature: number
  wind_speed: number
  visibility: number
  ground_type: string
}

export interface SimMetrics {
  collision_count: number
  near_miss_count: number
  min_safety_distance: number
  risk_score: number
  completion_time: number
  path_efficiency: number
  average_speed: number
  max_acceleration: number
  max_deceleration: number
  steering_smoothness: number
  task_completed: boolean
  completion_rate: number
  algorithm_name: string
}

export interface VehicleFrame {
  id: string
  x: number
  y: number
  heading: number
  speed: number
  length?: number
  width?: number
  engine_temp?: number
  engine_status?: string
  speed_limit_factor?: number
}

export interface EventZone {
  id: string
  type: string
  name: string
  x: number
  y: number
  radius_m: number
  speed_factor: number
  duration_s: number
  color: string
  icon: string
  start_time: number
  end_time: number
  remaining_time?: number
}

export interface SimFrame {
  frame: number
  time: number
  vehicles: VehicleFrame[]
  completed: boolean
}

export interface Alert {
  id: string
  message: string
  level: 'bilgi' | 'uyarı' | 'kritik'
  timestamp: number
}

interface HusimStore {
  // Weather
  weather: WeatherInput
  setWeather: (w: Partial<WeatherInput>) => void

  // Optimization result
  optimizedParams: OptimizedParams | null
  setOptimizedParams: (p: OptimizedParams | null) => void

  // Active simulation
  activeSimId: string | null
  setActiveSimId: (id: string | null) => void
  simStatus: string
  setSimStatus: (s: string) => void
  simProgress: number
  setSimProgress: (p: number) => void
  simMetrics: SimMetrics | null
  setSimMetrics: (m: SimMetrics | null) => void

  // Live frames
  frames: SimFrame[]
  addFrame: (f: SimFrame) => void
  clearFrames: () => void
  currentFrameIdx: number
  setCurrentFrameIdx: (i: number) => void

  // Alerts
  alerts: Alert[]
  addAlert: (a: Omit<Alert, 'id' | 'timestamp'>) => void
  removeAlert: (id: string) => void
  clearAlerts: () => void
  alertThreshold: number
  setAlertThreshold: (t: number) => void

  // Backend connection
  backendConnected: boolean
  setBackendConnected: (v: boolean) => void

  // Selected scenario
  selectedScenario: string | null
  setSelectedScenario: (id: string | null) => void

  // Active page
  activePage: 'dashboard' | 'scenarios' | 'history'
  setActivePage: (p: 'dashboard' | 'scenarios' | 'history') => void

  // Road geometry (for the selected scenario)
  roadGeometry: any | null
  setRoadGeometry: (g: any | null) => void

  // Bulk-set all frames (for preloading)
  setFrames: (f: SimFrame[]) => void

  // Load and grade parameters
  loadParams: { vehicleType: string; loadPercent: number; gradePercent: number }
  setLoadParams: (p: Partial<{ vehicleType: string; loadPercent: number; gradePercent: number }>) => void
  calculatedLoad: any | null
  setCalculatedLoad: (v: any | null) => void

  // Event zones
  activeEvents: EventZone[]
  setActiveEvents: (events: EventZone[]) => void
  addEventZone: (ev: EventZone) => void
  removeEventZone: (id: string) => void

  // Event placing mode
  eventPlacingType: string | null
  setEventPlacingType: (t: string | null) => void

  // Presentation mode
  presentationMode: boolean
  setPresentationMode: (v: boolean) => void
}

export const useStore = create<HusimStore>((set) => ({
  weather: {
    weather_type: 'clear',
    temperature: 20,
    wind_speed: 10,
    visibility: 500,
    ground_type: 'dry',
  },
  setWeather: (w) => set((s) => ({ weather: { ...s.weather, ...w } })),

  optimizedParams: null,
  setOptimizedParams: (p) => set({ optimizedParams: p }),

  activeSimId: null,
  setActiveSimId: (id) => set({ activeSimId: id }),
  simStatus: 'idle',
  setSimStatus: (s) => set({ simStatus: s }),
  simProgress: 0,
  setSimProgress: (p) => set({ simProgress: p }),
  simMetrics: null,
  setSimMetrics: (m) => set({ simMetrics: m }),

  frames: [],
  addFrame: (f) => set((s) => ({ frames: [...s.frames.slice(-300), f] })),
  clearFrames: () => set({ frames: [], currentFrameIdx: 0 }),
  currentFrameIdx: 0,
  setCurrentFrameIdx: (i) => set({ currentFrameIdx: i }),

  alerts: [],
  addAlert: (a) =>
    set((s) => ({
      alerts: [
        { ...a, id: Math.random().toString(36).slice(2), timestamp: Date.now() },
        ...s.alerts.slice(0, 49),
      ],
    })),
  removeAlert: (id) => set((s) => ({ alerts: s.alerts.filter((a) => a.id !== id) })),
  clearAlerts: () => set({ alerts: [] }),
  alertThreshold: 70,
  setAlertThreshold: (t) => set({ alertThreshold: t }),

  backendConnected: false,
  setBackendConnected: (v) => set({ backendConnected: v }),

  selectedScenario: null,
  setSelectedScenario: (id) => set({ selectedScenario: id }),

  activePage: 'dashboard',
  setActivePage: (p) => set({ activePage: p }),

  roadGeometry: null,
  setRoadGeometry: (g) => set({ roadGeometry: g }),

  setFrames: (f) => set({ frames: f.slice(0, 3000), currentFrameIdx: 0 }),

  loadParams: { vehicleType: 'MineTruck_XG90G', loadPercent: 0, gradePercent: 0 },
  setLoadParams: (p) => set((s) => ({ loadParams: { ...s.loadParams, ...p } })),
  calculatedLoad: null,
  setCalculatedLoad: (v) => set({ calculatedLoad: v }),

  activeEvents: [],
  setActiveEvents: (events) => set({ activeEvents: events }),
  addEventZone: (ev) => set((s) => ({ activeEvents: [...s.activeEvents, ev] })),
  removeEventZone: (id) => set((s) => ({ activeEvents: s.activeEvents.filter((e) => e.id !== id) })),

  eventPlacingType: null,
  setEventPlacingType: (t) => set({ eventPlacingType: t }),

  presentationMode: false,
  setPresentationMode: (v) => set({ presentationMode: v }),
}))
