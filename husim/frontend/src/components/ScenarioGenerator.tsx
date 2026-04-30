import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { tr } from '../tr'
import { useStore } from '../store'
import { generateScenario } from '../api'

type IntersectionType = 'T' | 'cross' | 'straight' | 'complex'
type Difficulty = 'kolay' | 'orta' | 'zor' | 'kritik'
type SpecialCondition = 'normal' | 'dar_yol' | 'egim' | 'kor_kavsak'

const INTERSECTION_TYPES: { key: IntersectionType; label: string; icon: string }[] = [
  { key: 'T', label: tr.scenarioGenerator.types.T, icon: '┤' },
  { key: 'cross', label: tr.scenarioGenerator.types.cross, icon: '┼' },
  { key: 'straight', label: tr.scenarioGenerator.types.straight, icon: '═' },
  { key: 'complex', label: tr.scenarioGenerator.types.complex, icon: '✦' },
]

const DIFFICULTIES: { key: Difficulty; label: string; color: string }[] = [
  { key: 'kolay', label: tr.scenarioGenerator.difficulties.easy, color: 'text-emerald-400' },
  { key: 'orta', label: tr.scenarioGenerator.difficulties.medium, color: 'text-yellow-400' },
  { key: 'zor', label: tr.scenarioGenerator.difficulties.hard, color: 'text-orange-400' },
  { key: 'kritik', label: tr.scenarioGenerator.difficulties.critical, color: 'text-red-400' },
]

const SPECIAL_CONDITIONS: { key: SpecialCondition; label: string }[] = [
  { key: 'normal', label: tr.scenarioGenerator.conditions.normal },
  { key: 'dar_yol', label: tr.scenarioGenerator.conditions.narrow },
  { key: 'egim', label: tr.scenarioGenerator.conditions.slope },
  { key: 'kor_kavsak', label: tr.scenarioGenerator.conditions.blind },
]

export default function ScenarioGenerator() {
  const { optimizedParams } = useStore()
  const queryClient = useQueryClient()

  const [intersectionType, setIntersectionType] = useState<IntersectionType>('T')
  const [vehicleCount, setVehicleCount] = useState(3)
  const [difficulty, setDifficulty] = useState<Difficulty>('orta')
  const [specialCondition, setSpecialCondition] = useState<SpecialCondition>('normal')
  const [scenarioName, setScenarioName] = useState('')
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<{ success: boolean; name?: string; id?: string } | null>(null)

  async function handleGenerate() {
    setGenerating(true)
    setResult(null)
    try {
      const res = await generateScenario({
        intersection_type: intersectionType,
        vehicle_count: vehicleCount,
        difficulty,
        special_condition: specialCondition,
        weather_params: optimizedParams ?? {},
        name: scenarioName.trim(),
      })
      setResult({
        success: true,
        name: res.senaryo?.name ?? scenarioName,
        id: res.senaryo?.scenario_id,
      })
      // Senaryo listesini yenile
      queryClient.invalidateQueries({ queryKey: ['scenarios'] })
      setScenarioName('')
    } catch (e: any) {
      setResult({ success: false })
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="p-3 bg-husim-surface rounded-lg flex flex-col gap-3">
      <h2 className="text-sm font-bold text-husim-accent uppercase tracking-wider">
        {tr.scenarioGenerator.title}
      </h2>

      {/* Intersection Type */}
      <div>
        <p className="text-xs text-slate-400 mb-1.5">{tr.scenarioGenerator.intersectionType}</p>
        <div className="grid grid-cols-4 gap-1.5">
          {INTERSECTION_TYPES.map(({ key, label, icon }) => (
            <button
              key={key}
              onClick={() => setIntersectionType(key)}
              className={`py-1.5 rounded text-xs flex flex-col items-center gap-0.5 border transition-colors ${
                intersectionType === key
                  ? 'border-husim-accent bg-husim-accent/10 text-husim-accent font-bold'
                  : 'border-slate-600 bg-slate-700 text-slate-300 hover:border-slate-500'
              }`}
            >
              <span className="text-lg leading-none">{icon}</span>
              <span className="leading-tight">{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Vehicle Count */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <p className="text-xs text-slate-400">{tr.scenarioGenerator.vehicleCount}</p>
          <span className="text-sm font-bold text-husim-accent">{vehicleCount}</span>
        </div>
        <input
          type="range"
          min={2}
          max={8}
          value={vehicleCount}
          onChange={(e) => setVehicleCount(Number(e.target.value))}
          className="w-full h-1.5"
          style={{ accentColor: '#f59e0b' }}
        />
        <div className="flex justify-between text-[10px] text-slate-500 mt-0.5">
          <span>2</span><span>4</span><span>6</span><span>8</span>
        </div>
      </div>

      {/* Difficulty */}
      <div>
        <p className="text-xs text-slate-400 mb-1.5">{tr.scenarioGenerator.difficulty}</p>
        <div className="grid grid-cols-4 gap-1.5">
          {DIFFICULTIES.map(({ key, label, color }) => (
            <button
              key={key}
              onClick={() => setDifficulty(key)}
              className={`py-1.5 rounded text-xs font-medium border transition-colors ${
                difficulty === key
                  ? `border-current bg-slate-700 ${color} font-bold`
                  : 'border-slate-600 bg-slate-700 text-slate-400 hover:border-slate-500'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Special Condition */}
      <div>
        <p className="text-xs text-slate-400 mb-1.5">{tr.scenarioGenerator.specialCondition}</p>
        <div className="grid grid-cols-2 gap-1.5">
          {SPECIAL_CONDITIONS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setSpecialCondition(key)}
              className={`py-1 rounded text-xs border transition-colors ${
                specialCondition === key
                  ? 'border-husim-accent bg-husim-accent/10 text-husim-accent font-bold'
                  : 'border-slate-600 bg-slate-700 text-slate-400 hover:border-slate-500'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Scenario Name */}
      <div>
        <p className="text-xs text-slate-400 mb-1">{tr.scenarioGenerator.scenarioName}</p>
        <input
          type="text"
          value={scenarioName}
          onChange={(e) => setScenarioName(e.target.value)}
          placeholder={`${intersectionType} — ${vehicleCount} Araç`}
          className="w-full bg-slate-700 border border-slate-600 text-husim-text text-xs rounded px-2 py-1.5 focus:outline-none focus:border-husim-accent"
        />
      </div>

      {/* Generate button */}
      <button
        onClick={handleGenerate}
        disabled={generating}
        className="w-full py-2 rounded text-sm font-bold bg-purple-700 text-white hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {generating ? tr.scenarioGenerator.generating : tr.scenarioGenerator.generate}
      </button>

      {/* Result message */}
      {result && (
        <div
          className={`text-xs px-2 py-1.5 rounded ${
            result.success
              ? 'bg-emerald-900/40 text-emerald-400 border border-emerald-700/30'
              : 'bg-red-900/40 text-red-400 border border-red-700/30'
          }`}
        >
          {result.success
            ? `✓ ${result.name || tr.scenarioGenerator.success}`
            : '✗ Senaryo üretilemedi. Backend çalışıyor mu?'}
        </div>
      )}
    </div>
  )
}
