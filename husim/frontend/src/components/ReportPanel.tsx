import { useState } from 'react'
import { tr } from '../tr'
import { useStore } from '../store'
import { generateReport, getReportDownloadUrl } from '../api'

export default function ReportPanel() {
  const { activeSimId, simStatus, simMetrics } = useStore()
  const [generating, setGenerating] = useState(false)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [opts, setOpts] = useState({
    include_metrics: true,
    include_charts: true,
    include_weather: true,
    include_comparison: false,
  })

  const canGenerate = !!activeSimId && (simStatus === 'completed' || simStatus === 'failed')

  async function handleGenerate() {
    if (!activeSimId) return
    setGenerating(true)
    setReady(false)
    setError(null)
    try {
      await generateReport({ simulation_id: activeSimId, ...opts })
      setReady(true)
    } catch (e: any) {
      setError('Rapor oluşturulamadı: ' + e.message)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="flex flex-col gap-2 p-3 bg-husim-surface rounded-lg">
      <h2 className="text-sm font-bold text-husim-accent uppercase tracking-wider">{tr.report.title}</h2>

      <div className="space-y-1.5">
        {[
          { key: 'include_metrics', label: tr.report.metrics },
          { key: 'include_charts', label: tr.report.charts },
          { key: 'include_weather', label: tr.report.weather },
          { key: 'include_comparison', label: tr.report.comparison },
        ].map(({ key, label }) => (
          <label key={key} className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={opts[key as keyof typeof opts]}
              onChange={(e) => setOpts((o) => ({ ...o, [key]: e.target.checked }))}
              className="accent-husim-accent"
            />
            {label}
          </label>
        ))}
      </div>

      {!canGenerate && (
        <p className="text-xs text-slate-500 italic">Rapor oluşturmak için bir simülasyon tamamlanmalı.</p>
      )}

      {error && <p className="text-xs text-husim-danger">{error}</p>}

      <button
        onClick={handleGenerate}
        disabled={!canGenerate || generating}
        className="w-full py-1.5 rounded text-sm font-bold bg-husim-primary text-husim-accent border border-husim-accent/40 hover:bg-husim-primary/80 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        {generating ? tr.report.generating : 'Rapor Oluştur'}
      </button>

      {ready && activeSimId && (
        <a
          href={getReportDownloadUrl(activeSimId)}
          download
          className="block text-center py-1.5 rounded text-sm font-bold bg-husim-success text-white hover:bg-emerald-400 transition-colors"
        >
          ⬇️ {tr.report.generate}
        </a>
      )}
    </div>
  )
}
