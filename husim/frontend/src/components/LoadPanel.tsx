import { useEffect } from 'react'
import { tr } from '../tr'
import { useStore } from '../store'
import { calculateLoad } from '../api'

const VEHICLE_TYPES = ['MineTruck_XG90G', 'MineTruck_NTE200']

export default function LoadPanel() {
  const { loadParams, setLoadParams, calculatedLoad, setCalculatedLoad } = useStore()

  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const result = await calculateLoad({
          vehicle_type: loadParams.vehicleType,
          load_percent: loadParams.loadPercent,
          grade_percent: loadParams.gradePercent,
        })
        setCalculatedLoad(result)
      } catch (_) {
        // Backend may not have started yet
      }
    }, 250)
    return () => clearTimeout(timer)
  }, [loadParams.vehicleType, loadParams.loadPercent, loadParams.gradePercent, setCalculatedLoad])

  const gradeColor =
    loadParams.gradePercent > 5
      ? '#22c55e'
      : loadParams.gradePercent < -5
      ? '#eab308'
      : '#94a3b8'

  const gradeLabel =
    loadParams.gradePercent > 0
      ? `↗ +${loadParams.gradePercent}% ${tr.loadSystem.uphill}`
      : loadParams.gradePercent < 0
      ? `↘ ${loadParams.gradePercent}% ${tr.loadSystem.downhill}`
      : `→ 0% ${tr.loadSystem.flat}`

  return (
    <div className="flex flex-col gap-2 p-3 bg-husim-surface rounded-lg">
      <h2 className="text-sm font-bold text-husim-accent uppercase tracking-wider">
        {tr.loadSystem.title}
      </h2>

      {/* Vehicle Type */}
      <div>
        <label className="text-xs text-slate-400 mb-1 block">{tr.loadSystem.vehicleType}</label>
        <select
          value={loadParams.vehicleType}
          onChange={(e) => setLoadParams({ vehicleType: e.target.value })}
          className="w-full bg-slate-700 border border-slate-600 text-husim-text text-xs rounded px-2 py-1.5 focus:outline-none focus:border-husim-accent"
        >
          {VEHICLE_TYPES.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {/* Load Percentage */}
      <div>
        <label className="text-xs text-slate-300 mb-1 block">
          {tr.loadSystem.loadPercent}: {loadParams.loadPercent}%
        </label>
        <input
          type="range" min={0} max={100} step={5}
          value={loadParams.loadPercent}
          onChange={(e) => setLoadParams({ loadPercent: Number(e.target.value) })}
          style={{ accentColor: '#f59e0b' }}
          className="w-full h-1.5 rounded cursor-pointer"
        />
        {/* Quick Preset Buttons */}
        <div className="flex gap-1 mt-1.5">
          {([['Boş', 0, 'empty'], ['Yarı', 50, 'halfLoaded'], ['Tam', 100, 'fullLoaded']] as const).map(([, pct, key]) => (
            <button
              key={key}
              onClick={() => setLoadParams({ loadPercent: pct })}
              className={`flex-1 py-0.5 rounded text-xs transition-all border ${
                loadParams.loadPercent === pct
                  ? 'border-husim-accent bg-husim-accent/20 text-husim-accent font-bold'
                  : 'border-slate-600 text-slate-400 hover:border-slate-500'
              }`}
            >
              {tr.loadSystem[key]}
            </button>
          ))}
        </div>
      </div>

      {/* Grade */}
      <div>
        <label className="text-xs mb-1 block" style={{ color: gradeColor }}>
          {tr.loadSystem.grade}: {gradeLabel}
        </label>
        <input
          type="range" min={-15} max={15} step={1}
          value={loadParams.gradePercent}
          onChange={(e) => setLoadParams({ gradePercent: Number(e.target.value) })}
          style={{ accentColor: gradeColor }}
          className="w-full h-1.5 rounded cursor-pointer"
        />
      </div>

      {/* Calculated Values */}
      {calculatedLoad && (
        <div className="grid grid-cols-2 gap-1 text-xs mt-1">
          <ParamRow label={tr.loadSystem.maxSpeed} value={`${calculatedLoad.max_speed_ms} m/s`} />
          <ParamRow label={tr.loadSystem.maxAccel} value={`${calculatedLoad.max_accel} m/s²`} />
          <ParamRow label={tr.loadSystem.brakeDistance} value={`${calculatedLoad.brake_distance_m} m`} />
          <ParamRow label={tr.loadSystem.totalWeight} value={`${calculatedLoad.total_weight_ton} ton`} />
        </div>
      )}
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
