import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { tr } from '../tr'
import { useStore } from '../store'
import {
  fetchScenarios, runScenario, stopSimulation, createWebSocket,
  fetchScenarioFrames,
} from '../api'

type FilterType = 'all' | 'minesim_real' | 'demo' | 'generated' | 'fleet' | 'extended'

function badgeStyle(source: string, badge?: string) {
  if (badge === 'Stabil') return 'bg-emerald-600 text-emerald-100'
  if (badge === 'Beta') return 'bg-yellow-700 text-yellow-100'
  if (badge === 'Faza-E') return 'bg-blue-700 text-blue-100'
  if (source === 'minesim_real') return 'bg-emerald-700 text-emerald-100'
  if (source === 'generated') return 'bg-purple-700 text-purple-100'
  if (source === 'extended') return 'bg-blue-700 text-blue-100'
  return 'bg-slate-600 text-slate-300'
}

function badgeLabel(source: string, badge: string) {
  if (badge) return badge
  if (source === 'minesim_real') return 'Gerçek Veri'
  if (source === 'generated') return 'Üretilmiş'
  return 'Demo'
}

export default function ScenarioSelector() {
  const {
    selectedScenario, setSelectedScenario,
    optimizedParams,
    activeSimId, setActiveSimId,
    simStatus, setSimStatus,
    setSimProgress, setSimMetrics,
    addFrame, clearFrames, setFrames,
    setRoadGeometry,
    addAlert, alertThreshold,
    loadParams,
  } = useStore()

  const [loading, setLoading] = useState(false)
  const [preloading, setPreloading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<FilterType>('all')

  const { data } = useQuery({
    queryKey: ['scenarios'],
    queryFn: fetchScenarios,
    retry: 3,
  })
  const scenarios: any[] = data?.senaryolar ?? []

  const filtered = scenarios.filter((s) => {
    if (filter === 'all') return true
    if (filter === 'minesim_real') return s.source === 'minesim_real'
    if (filter === 'demo') return s.source === 'demo' && !s.id.startsWith('fleet_')
    if (filter === 'generated') return s.source === 'generated'
    if (filter === 'fleet') return s.id.startsWith('fleet_')
    if (filter === 'extended') return s.source === 'extended'
    return true
  })

  // Senaryo seçilince frame'leri önceden yükle
  useEffect(() => {
    if (!selectedScenario) {
      clearFrames()
      setRoadGeometry(null)
      return
    }
    let cancelled = false
    setPreloading(true)
    fetchScenarioFrames(selectedScenario)
      .then((data) => {
        if (cancelled) return
        if (data.frames?.length) setFrames(data.frames)
        if (data.road_geometry) setRoadGeometry(data.road_geometry)
      })
      .catch((e) => {
        if (!cancelled) console.warn('Frame yükleme hatası:', e)
      })
      .finally(() => {
        if (!cancelled) setPreloading(false)
      })
    return () => { cancelled = true }
  }, [selectedScenario])

  async function handleRun() {
    if (!selectedScenario || !optimizedParams) return
    setLoading(true)
    setError(null)
    clearFrames()
    setSimMetrics(null)

    try {
      const res = await runScenario({
        scenario_id: selectedScenario,
        optimized_params: optimizedParams,
        algorithm: optimizedParams.recommended_algorithm,
        load_percent: loadParams.loadPercent,
        grade_percent: loadParams.gradePercent,
        vehicle_type: loadParams.vehicleType,
      })

      const simId: string = res.simulasyon_id
      setActiveSimId(simId)
      setSimStatus('running')

      const ws = createWebSocket(simId)

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        if (msg.tip === 'frame') {
          addFrame(msg.veri)
          setSimProgress(Math.min(99, Math.floor((msg.veri.frame / 150) * 100)))
        } else if (msg.tip === 'tamamlandi') {
          setSimStatus('completed')
          setSimProgress(100)
          setSimMetrics(msg.metrikler)
          if (msg.metrikler?.risk_score >= alertThreshold) {
            addAlert({ message: `Risk skoru eşiği aşıldı: ${msg.metrikler.risk_score}/100`, level: 'uyarı' })
          }
          ws.close()
        } else if (msg.tip === 'hata') {
          setSimStatus('failed')
          setError(msg.mesaj)
          ws.close()
        }
      }
      ws.onerror = () => { setSimStatus('failed'); setError('WebSocket bağlantı hatası') }
      ws.onclose = () => {
        const st = useStore.getState().simStatus
        if (st === 'running') {
          setTimeout(() => {
            const ws2 = createWebSocket(simId)
            ws2.onmessage = ws.onmessage
          }, 5000)
        }
      }
    } catch (e: any) {
      setError('Simülasyon başlatılamadı: ' + e.message)
      setSimStatus('failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleStop() {
    if (!activeSimId) return
    await stopSimulation(activeSimId)
    setSimStatus('stopped')
    addAlert({ message: 'Simülasyon kullanıcı tarafından durduruldu.', level: 'bilgi' })
  }

  const isRunning = simStatus === 'running'

  const filterButtons: { key: FilterType; label: string }[] = [
    { key: 'all', label: tr.scenarioFilter.all },
    { key: 'minesim_real', label: tr.scenarioFilter.real },
    { key: 'demo', label: tr.scenarioFilter.demo },
    { key: 'fleet', label: tr.scenarioFilter.fleet },
    { key: 'extended', label: 'Faza E' },
    { key: 'generated', label: tr.scenarioFilter.generated },
  ]

  return (
    <div className="flex flex-col gap-2 p-3 bg-husim-surface rounded-lg">
      <h2 className="text-sm font-bold text-husim-accent uppercase tracking-wider">
        {tr.scenario.title}
      </h2>

      {/* Filtre butonları */}
      <div className="flex gap-1 flex-wrap">
        {filterButtons.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`text-xs px-2 py-0.5 rounded transition-colors ${
              filter === key
                ? 'bg-husim-accent text-husim-bg font-bold'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            {label}
            {key !== 'all' && (
              <span className="ml-1 opacity-60">
                ({scenarios.filter((s) =>
                  key === 'minesim_real' ? s.source === 'minesim_real' :
                  key === 'demo' ? (s.source === 'demo' && !s.id.startsWith('fleet_')) :
                  key === 'fleet' ? s.id.startsWith('fleet_') :
                  key === 'extended' ? s.source === 'extended' :
                  s.source === 'generated'
                ).length})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Kart listesi */}
      <div className="flex flex-col gap-1.5 max-h-52 overflow-y-auto pr-0.5 pt-0.5 pb-1">
        {scenarios.length === 0 && (
          <div className="text-xs text-slate-500 text-center py-3">
            {tr.scenarioFilter.loading}
          </div>
        )}
        {filtered.map((s) => {
          const isSelected = selectedScenario === s.id
          return (
            <button
              key={s.id}
              onClick={() => setSelectedScenario(isSelected ? null : s.id)}
              disabled={isRunning}
              className={`text-left p-2 rounded border transition-all ${
                isSelected
                  ? 'border-husim-accent bg-husim-accent/10'
                  : 'border-slate-700 bg-slate-700/40 hover:border-slate-500'
              } disabled:opacity-50`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-husim-text truncate">{s.name}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded shrink-0 ${badgeStyle(s.source, s.badge)}`}>
                  {badgeLabel(s.source, s.badge)}
                </span>
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">
                {s.agent_count} {tr.scenarioFilter.agentCount} • {s.total_time.toFixed(0)}{tr.scenarioFilter.seconds}
                {s.scenario_type && ` • ${s.scenario_type}`}
                {s.grade_label && (
                  <span className="ml-1" style={{ color: (s.grade ?? 0) > 0 ? '#22c55e' : (s.grade ?? 0) < 0 ? '#eab308' : '#94a3b8' }}>
                    {' • '}{s.grade_label}
                  </span>
                )}
              </div>
            </button>
          )
        })}
      </div>

      {/* Yükleme göstergesi */}
      {preloading && (
        <div className="text-xs text-blue-400 animate-pulse">{tr.scenarioFilter.previewLoading}</div>
      )}

      {/* Hava optimizasyonu uyarısı */}
      {!optimizedParams && (
        <p className="text-xs text-yellow-400">⚠️ Önce hava koşullarını optimize edin.</p>
      )}

      {/* Progress */}
      {isRunning && (
        <div>
          <div className="flex justify-between text-xs text-slate-400 mb-1">
            <span>{tr.scenario.running}</span>
            <span>{useStore.getState().simProgress}%</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-1.5">
            <div
              className="bg-husim-accent h-1.5 rounded-full transition-all"
              style={{ width: `${useStore.getState().simProgress}%` }}
            />
          </div>
        </div>
      )}

      {simStatus === 'completed' && (
        <div className="text-xs text-husim-success font-medium">✓ Simülasyon tamamlandı</div>
      )}
      {simStatus === 'failed' && (
        <div className="text-xs text-husim-danger font-medium">✗ Simülasyon başarısız</div>
      )}
      {simStatus === 'stopped' && (
        <div className="text-xs text-slate-400 font-medium">⏹ Durduruldu</div>
      )}
      {error && <p className="text-xs text-husim-danger">{error}</p>}

      {/* Çalıştır / Durdur */}
      <div className="flex gap-2">
        <button
          onClick={handleRun}
          disabled={!selectedScenario || !optimizedParams || isRunning || loading}
          className="flex-1 py-1.5 rounded text-sm font-bold bg-husim-success text-white hover:bg-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {isRunning ? tr.scenario.running : tr.scenario.run}
        </button>
        {isRunning && (
          <button
            onClick={handleStop}
            className="py-1.5 px-3 rounded text-sm font-bold bg-husim-danger text-white hover:bg-red-400 transition-colors"
          >
            {tr.scenario.stop}
          </button>
        )}
      </div>
    </div>
  )
}
