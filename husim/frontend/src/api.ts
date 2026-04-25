const BASE = '/api'

export async function fetchHealth() {
  const r = await fetch(`${BASE}/health`)
  return r.json()
}

export async function fetchScenarios() {
  const r = await fetch(`${BASE}/scenarios`)
  return r.json()
}

export async function optimizeWeather(weather: object) {
  const r = await fetch(`${BASE}/weather/optimize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(weather),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function runScenario(payload: object) {
  const r = await fetch(`${BASE}/scenarios/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function stopSimulation(simId: string) {
  const r = await fetch(`${BASE}/scenarios/${simId}/stop`, { method: 'POST' })
  return r.json()
}

export async function fetchHistory() {
  const r = await fetch(`${BASE}/history`)
  return r.json()
}

export async function generateReport(payload: object) {
  const r = await fetch(`${BASE}/reports/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export function getReportDownloadUrl(simId: string) {
  return `${BASE}/reports/${simId}/download`
}

export async function batchRun(payload: object) {
  const r = await fetch(`${BASE}/scenarios/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export function createWebSocket(simId: string): WebSocket {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return new WebSocket(`${proto}://${window.location.host}/ws/simulation/${simId}`)
}

export async function fetchScenarioFrames(scenarioId: string) {
  const r = await fetch(`${BASE}/scenarios/${encodeURIComponent(scenarioId)}/frames`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function generateScenario(payload: object) {
  const r = await fetch(`${BASE}/scenarios/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function compareScenarios(payload: object) {
  const r = await fetch(`${BASE}/scenarios/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function fetchLoadPresets() {
  const r = await fetch(`${BASE}/load/presets`)
  return r.json()
}

export async function calculateLoad(payload: object) {
  const r = await fetch(`${BASE}/load/calculate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function fetchActiveEvents() {
  const r = await fetch(`${BASE}/events/active`)
  return r.json()
}

export async function addEvent(payload: object) {
  const r = await fetch(`${BASE}/events/add`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function deleteEvent(eventId: string) {
  const r = await fetch(`${BASE}/events/${eventId}`, { method: 'DELETE' })
  return r.json()
}

export async function addRandomEvents(payload: object) {
  const r = await fetch(`${BASE}/events/random`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
