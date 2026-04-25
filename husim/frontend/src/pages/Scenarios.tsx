import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { tr } from '../tr'
import { useStore } from '../store'
import { fetchScenarios, batchRun, createWebSocket } from '../api'

export default function Scenarios() {
  const { optimizedParams, addAlert, setSimMetrics, clearFrames, addFrame, setSimStatus, setSimProgress } = useStore()
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [batchStatus, setBatchStatus] = useState<Record<string, 'pending' | 'running' | 'completed' | 'failed'>>({})
  const [batchRunning, setBatchRunning] = useState(false)
  const [batchResults, setBatchResults] = useState<Record<string, any>>({})

  const { data } = useQuery({
    queryKey: ['scenarios'],
    queryFn: fetchScenarios,
  })
  const scenarios: any[] = data?.senaryolar ?? []

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const completedCount = Object.values(batchStatus).filter((s) => s === 'completed').length
  const totalSelected = selected.size

  async function handleBatchRun() {
    if (!optimizedParams || selected.size === 0) return
    setBatchRunning(true)
    clearFrames()

    const ids = Array.from(selected)
    const initialStatus: Record<string, any> = {}
    ids.forEach((id) => { initialStatus[id] = 'pending' })
    setBatchStatus(initialStatus)

    try {
      const res = await batchRun({
        scenario_ids: ids,
        optimized_params: optimizedParams,
        algorithm: optimizedParams.recommended_algorithm,
      })

      const simIds: string[] = res.simulasyon_idleri
      const pairs = ids.map((scenarioId, i) => ({ scenarioId, simId: simIds[i] }))

      for (const { scenarioId, simId } of pairs) {
        setBatchStatus((prev) => ({ ...prev, [scenarioId]: 'running' }))

        await new Promise<void>((resolve) => {
          const ws = createWebSocket(simId)
          ws.onmessage = (e) => {
            const msg = JSON.parse(e.data)
            if (msg.tip === 'frame') {
              addFrame(msg.veri)
            } else if (msg.tip === 'tamamlandi') {
              setBatchStatus((prev) => ({ ...prev, [scenarioId]: 'completed' }))
              setBatchResults((prev) => ({ ...prev, [scenarioId]: msg.metrikler }))
              ws.close()
              resolve()
            } else if (msg.tip === 'hata') {
              setBatchStatus((prev) => ({ ...prev, [scenarioId]: 'failed' }))
              ws.close()
              resolve()
            }
          }
          ws.onerror = () => {
            setBatchStatus((prev) => ({ ...prev, [scenarioId]: 'failed' }))
            resolve()
          }
        })
      }

      addAlert({ message: `Toplu simülasyon tamamlandı: ${pairs.length} senaryo`, level: 'bilgi' })
    } catch (e: any) {
      addAlert({ message: 'Toplu çalıştırma hatası: ' + e.message, level: 'kritik' })
    } finally {
      setBatchRunning(false)
    }
  }

  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      pending: 'bg-slate-600 text-slate-300',
      running: 'bg-blue-600 text-white animate-pulse',
      completed: 'bg-husim-success text-white',
      failed: 'bg-husim-danger text-white',
    }
    const labels: Record<string, string> = {
      pending: 'Bekliyor',
      running: 'Çalışıyor',
      completed: 'Tamamlandı',
      failed: 'Başarısız',
    }
    return (
      <span className={`text-xs px-2 py-0.5 rounded ${map[status] ?? 'bg-slate-600'}`}>
        {labels[status] ?? status}
      </span>
    )
  }

  return (
    <div className="p-4 max-w-4xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-husim-accent">{tr.scenario.title}</h1>
        <div className="flex items-center gap-2">
          {!optimizedParams && (
            <span className="text-xs text-yellow-400">⚠️ Önce hava optimizasyonu yapın</span>
          )}
          {batchRunning && (
            <span className="text-xs text-blue-400">
              {completedCount}/{totalSelected} tamamlandı
            </span>
          )}
          <button
            onClick={handleBatchRun}
            disabled={selected.size === 0 || !optimizedParams || batchRunning}
            className="px-3 py-1.5 rounded text-sm font-bold bg-husim-accent text-husim-bg hover:bg-amber-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {batchRunning ? `Çalışıyor (${completedCount}/${totalSelected})` : tr.scenario.batchRun}
          </button>
        </div>
      </div>

      {/* Progress bar */}
      {batchRunning && (
        <div className="w-full bg-slate-700 rounded-full h-2">
          <div
            className="bg-husim-accent h-2 rounded-full transition-all"
            style={{ width: `${totalSelected > 0 ? (completedCount / totalSelected) * 100 : 0}%` }}
          />
        </div>
      )}

      {/* Senaryo Tablosu */}
      <div className="bg-husim-surface rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-husim-primary text-slate-300 text-xs">
              <th className="w-8 p-2"></th>
              <th className="text-left p-2">Senaryo</th>
              <th className="text-left p-2">Açıklama</th>
              <th className="text-left p-2">Tür</th>
              <th className="text-left p-2">Durum</th>
              <th className="text-left p-2">Risk Skoru</th>
            </tr>
          </thead>
          <tbody>
            {scenarios.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-8 text-slate-500">
                  Senaryo yükleniyor...
                </td>
              </tr>
            )}
            {scenarios.map((s: any) => {
              const status = batchStatus[s.id]
              const result = batchResults[s.id]
              return (
                <tr
                  key={s.id}
                  className={`border-t border-slate-700 hover:bg-slate-700/30 transition-colors ${
                    selected.has(s.id) ? 'bg-husim-accent/5' : ''
                  }`}
                >
                  <td className="p-2">
                    <input
                      type="checkbox"
                      checked={selected.has(s.id)}
                      onChange={() => toggleSelect(s.id)}
                      className="accent-husim-accent"
                      disabled={batchRunning}
                    />
                  </td>
                  <td className="p-2 font-medium text-husim-text">{s.name}</td>
                  <td className="p-2 text-xs text-slate-400">{s.description}</td>
                  <td className="p-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${s.demo ? 'bg-slate-600 text-slate-300' : 'bg-husim-primary text-husim-accent'}`}>
                      {s.demo ? 'Demo' : 'Gerçek'}
                    </span>
                  </td>
                  <td className="p-2">{status ? statusBadge(status) : <span className="text-xs text-slate-500">—</span>}</td>
                  <td className="p-2 text-xs">
                    {result ? (
                      <span className={result.risk_score > 60 ? 'text-husim-danger' : result.risk_score > 30 ? 'text-yellow-400' : 'text-husim-success'}>
                        {result.risk_score}/100
                      </span>
                    ) : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Seçim özeti */}
      <div className="text-xs text-slate-400">
        {selected.size > 0
          ? `${selected.size} senaryo seçildi`
          : 'Toplu çalıştırmak için senaryo seçin'}
      </div>
    </div>
  )
}
