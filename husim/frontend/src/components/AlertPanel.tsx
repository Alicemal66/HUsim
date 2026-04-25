import { useState } from 'react'
import { tr } from '../tr'
import { useStore } from '../store'

const LEVEL_STYLES = {
  bilgi: 'border-blue-500/40 bg-blue-500/10 text-blue-300',
  uyarı: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-200',
  kritik: 'flash-critical border-husim-danger/60 text-red-200',
}

export default function AlertPanel() {
  const { alerts, removeAlert, clearAlerts, alertThreshold, setAlertThreshold } = useStore()
  const [showSettings, setShowSettings] = useState(false)

  return (
    <div className="flex flex-col gap-2 p-3 bg-husim-surface rounded-lg h-full overflow-y-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-husim-accent uppercase tracking-wider">{tr.alerts.title}</h2>
        <div className="flex gap-1">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="text-xs text-slate-400 hover:text-white px-1.5 py-0.5 rounded border border-slate-600 hover:border-slate-400"
          >
            ⚙️
          </button>
          {alerts.length > 0 && (
            <button
              onClick={clearAlerts}
              className="text-xs text-slate-400 hover:text-husim-danger px-1.5 py-0.5 rounded border border-slate-600"
            >
              Tümünü Temizle
            </button>
          )}
        </div>
      </div>

      {showSettings && (
        <div className="bg-slate-700/50 rounded p-2 text-xs">
          <label className="text-slate-300 block mb-1">
            Uyarı Eşiği: Risk skoru &gt; {alertThreshold}
          </label>
          <input
            type="range"
            min={0}
            max={100}
            value={alertThreshold}
            onChange={(e) => setAlertThreshold(Number(e.target.value))}
            className="w-full"
            style={{ accentColor: '#f59e0b' }}
          />
          <div className="flex justify-between text-slate-500 mt-0.5">
            <span>0</span><span>50</span><span>100</span>
          </div>
        </div>
      )}

      {alerts.length === 0 ? (
        <p className="text-xs text-slate-500 italic">{tr.alerts.none}</p>
      ) : (
        <div className="space-y-1.5">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`flex items-start justify-between rounded border px-2 py-1.5 text-xs ${
                LEVEL_STYLES[alert.level] || LEVEL_STYLES.bilgi
              }`}
            >
              <div>
                <p className="font-medium">{alert.message}</p>
                <p className="text-slate-500 text-xs mt-0.5">
                  {new Date(alert.timestamp).toLocaleTimeString('tr-TR')}
                </p>
              </div>
              <button
                onClick={() => removeAlert(alert.id)}
                className="text-slate-500 hover:text-white ml-2 shrink-0"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
