import { useState } from 'react'
import { tr } from '../tr'
import { useStore } from '../store'
import { optimizeWeather } from '../api'

const WEATHER_ICONS: Record<string, string> = {
  clear: '☀️',
  cloudy: '☁️',
  rainy: '🌧️',
  snowy: '❄️',
  foggy: '🌫️',
  stormy: '⛈️',
}

const RISK_COLORS: Record<string, string> = {
  düşük: 'bg-husim-success text-white',
  orta: 'bg-yellow-500 text-white',
  yüksek: 'bg-orange-500 text-white',
  kritik: 'bg-husim-danger text-white',
}

export default function WeatherPanel() {
  const { weather, setWeather, optimizedParams, setOptimizedParams } = useStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleOptimize() {
    setLoading(true)
    setError(null)
    try {
      const result = await optimizeWeather(weather)
      setOptimizedParams(result)
    } catch (e: any) {
      setError('Optimizasyon başarısız: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col gap-3 p-3 bg-husim-surface rounded-lg h-full overflow-y-auto">
      <div>
        <h2 className="text-sm font-bold text-husim-accent uppercase tracking-wider">{tr.weather.title}</h2>
        <p className="text-xs text-slate-400 mt-0.5">{tr.weather.subtitle}</p>
      </div>

      {/* Hava Tipi Butonları */}
      <div>
        <label className="text-xs text-slate-400 mb-1 block">{tr.weather.type}</label>
        <div className="grid grid-cols-3 gap-1">
          {Object.entries(tr.weather.types).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setWeather({ weather_type: key })}
              className={`flex flex-col items-center py-1.5 px-1 rounded text-xs font-medium transition-all border ${
                weather.weather_type === key
                  ? 'border-husim-accent bg-husim-accent/20 text-husim-accent'
                  : 'border-slate-600 text-slate-400 hover:border-slate-400 hover:text-slate-200'
              }`}
            >
              <span className="text-base">{WEATHER_ICONS[key]}</span>
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Sıcaklık */}
      <SliderField
        label={`${tr.weather.temperature}: ${weather.temperature}°C`}
        min={-30}
        max={50}
        value={weather.temperature}
        onChange={(v) => setWeather({ temperature: v })}
        color={weather.temperature < 0 ? '#60a5fa' : weather.temperature > 35 ? '#ef4444' : '#10b981'}
      />

      {/* Rüzgar */}
      <SliderField
        label={`${tr.weather.wind}: ${weather.wind_speed} km/s`}
        min={0}
        max={120}
        value={weather.wind_speed}
        onChange={(v) => setWeather({ wind_speed: v })}
        color={weather.wind_speed > 80 ? '#ef4444' : weather.wind_speed > 40 ? '#f59e0b' : '#10b981'}
      />

      {/* Görüş Mesafesi */}
      <SliderField
        label={`${tr.weather.visibility}: ${weather.visibility} m`}
        min={0}
        max={1000}
        value={weather.visibility}
        onChange={(v) => setWeather({ visibility: v })}
        color={weather.visibility < 100 ? '#ef4444' : weather.visibility < 300 ? '#f59e0b' : '#10b981'}
      />

      {/* Zemin */}
      <div>
        <label className="text-xs text-slate-400 mb-1 block">{tr.weather.ground}</label>
        <select
          value={weather.ground_type}
          onChange={(e) => setWeather({ ground_type: e.target.value })}
          className="w-full bg-slate-700 border border-slate-600 text-husim-text text-sm rounded px-2 py-1.5 focus:outline-none focus:border-husim-accent"
        >
          {Object.entries(tr.weather.grounds).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>
      </div>

      {/* Optimize Butonu */}
      <button
        onClick={handleOptimize}
        disabled={loading}
        className="w-full py-2 rounded font-bold text-sm bg-husim-accent text-husim-bg hover:bg-amber-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? tr.weather.optimizing : tr.weather.optimize}
      </button>

      {error && <p className="text-xs text-husim-danger">{error}</p>}

      {/* Optimizasyon Sonucu */}
      {optimizedParams && (
        <div className="border border-slate-600 rounded p-2 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-husim-accent">{tr.optimization.title}</span>
            <span className={`px-2 py-0.5 rounded text-xs font-bold ${RISK_COLORS[optimizedParams.risk_level] || 'bg-slate-600'}`}>
              {optimizedParams.risk_level.toUpperCase()}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-1">
            <ParamRow label={tr.optimization.speed} value={`×${optimizedParams.max_speed_factor.toFixed(2)}`} />
            <ParamRow label={tr.optimization.braking} value={`×${optimizedParams.braking_distance_factor.toFixed(2)}`} />
            <ParamRow label={tr.optimization.visibility} value={`${optimizedParams.visibility_range.toFixed(0)} m`} />
            <ParamRow label={tr.optimization.safety} value={`×${optimizedParams.safety_margin_factor.toFixed(2)}`} />
          </div>

          <div>
            <span className="text-slate-400">{tr.optimization.algorithm}: </span>
            <span className="text-husim-accent font-bold">{optimizedParams.recommended_algorithm}</span>
          </div>

          {optimizedParams.warnings.length > 0 && (
            <div className="space-y-1">
              {optimizedParams.warnings.map((w, i) => (
                <div key={i} className="text-xs text-yellow-300 bg-yellow-900/30 rounded px-2 py-1">{w}</div>
              ))}
            </div>
          )}

          {optimizedParams.optimization_notes && (
            <p className="text-slate-400 text-xs italic">{optimizedParams.optimization_notes}</p>
          )}

          {/* Dataset rozeti */}
          <div style={{
            background: '#1a3a1a',
            border: '1px solid #22c55e',
            borderRadius: '4px',
            padding: '3px 8px',
            fontSize: '10px',
            color: '#22c55e',
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
          }}>
            <span>✓</span>
            <span>{tr.dataset.telematicsSource}</span>
          </div>
        </div>
      )}
    </div>
  )
}

function SliderField({
  label, min, max, value, onChange, color,
}: {
  label: string; min: number; max: number; value: number
  onChange: (v: number) => void; color?: string
}) {
  return (
    <div>
      <label className="text-xs text-slate-300 mb-1 block">{label}</label>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ accentColor: color }}
        className="w-full h-1.5 rounded cursor-pointer"
      />
    </div>
  )
}

function ParamRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between bg-slate-700/50 rounded px-1.5 py-1">
      <span className="text-slate-400">{label}</span>
      <span className="text-husim-text font-medium">{value}</span>
    </div>
  )
}
