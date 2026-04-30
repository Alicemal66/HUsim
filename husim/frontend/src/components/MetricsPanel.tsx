import { tr } from '../tr'
import { useStore } from '../store'
import {
  RadialBarChart, RadialBar, PolarAngleAxis,
  LineChart, Line, ResponsiveContainer, Tooltip
} from 'recharts'

function RiskGauge({ score }: { score: number }) {
  const color = score < 30 ? '#10b981' : score < 60 ? '#f59e0b' : score < 80 ? '#f97316' : '#ef4444'
  const data = [{ value: score, fill: color }]

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-24 h-24">
        <RadialBarChart
          width={96} height={96}
          cx={48} cy={48}
          innerRadius={28} outerRadius={44}
          startAngle={180} endAngle={0}
          data={[{ value: 100, fill: '#1e293b' }, ...data]}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
          <RadialBar dataKey="value" cornerRadius={4} />
        </RadialBarChart>
        <div className="absolute inset-0 flex flex-col items-center justify-center mt-4">
          <span className="text-lg font-bold" style={{ color }}>{score.toFixed(0)}</span>
          <span className="text-xs text-slate-400">/100</span>
        </div>
      </div>
      <span className="text-xs text-slate-400">{tr.metrics.riskScore}</span>
    </div>
  )
}

function MetricCard({
  title,
  items,
  accentColor = '#10b981',
  progressItems,
}: {
  title: string
  items: { label: string; value: string | number; unit?: string }[]
  accentColor?: string
  progressItems?: { label: string; pct: number; color: string }[]
}) {
  return (
    <div className="bg-slate-800/60 rounded p-2">
      <h4 className="text-xs font-bold mb-1.5 uppercase tracking-wider" style={{ color: accentColor }}>
        {title}
      </h4>
      <div className="space-y-1">
        {items.map((item) => (
          <div key={item.label} className="flex justify-between text-xs">
            <span className="text-slate-400">{item.label}</span>
            <span className="font-medium text-husim-text">
              {item.value}{item.unit && <span className="text-slate-500 ml-0.5">{item.unit}</span>}
            </span>
          </div>
        ))}
        {progressItems?.map((pi) => (
          <div key={pi.label} className="mt-1">
            <div className="flex justify-between text-[10px] mb-0.5">
              <span className="text-slate-400">{pi.label}</span>
              <span style={{ color: pi.color }}>{pi.pct.toFixed(0)}%</span>
            </div>
            <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, pi.pct)}%`, background: pi.color }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function EngineTempBar({ temp, vehicleId }: { temp: number; vehicleId: string }) {
  const pct = Math.min(100, Math.max(0, ((temp - 60) / (150 - 60)) * 100))
  const color = temp >= 125 ? '#ef4444' : temp >= 115 ? '#ef4444' : temp >= 105 ? '#f59e0b' : '#10b981'
  const label = temp >= 125 ? tr.engineSystem.status.emergency
    : temp >= 115 ? tr.engineSystem.status.critical
    : temp >= 105 ? tr.engineSystem.status.warning
    : tr.engineSystem.status.normal

  return (
    <div className="flex items-center gap-1.5 text-xs">
      <span className="text-slate-400 w-14 truncate">{vehicleId}</span>
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="font-mono text-[10px]" style={{ color }}>{temp.toFixed(0)}°C</span>
      <span className="text-[10px]" style={{ color }}>{label}</span>
    </div>
  )
}

export default function MetricsPanel() {
  const { simMetrics, frames, simStatus } = useStore()

  // Live speed chart data (last 40 frames)
  const speedData = frames
    .slice(-40)
    .map((f) => {
      const ego = f.vehicles.find((v) => v.id === 'ego')
      return { t: f.time, speed: ego?.speed ?? 0 }
    })

  // Engine temperature chart (EGO, last 40 frames)
  const engineTempData = frames
    .slice(-40)
    .map((f) => {
      const ego = f.vehicles.find((v) => v.id === 'ego')
      return { t: f.time, temp: (ego as any)?.engine_temp ?? 80 }
    })

  // Current vehicle engine states (last frame)
  const lastFrame = frames[frames.length - 1]
  const vehicleEngineStates = lastFrame?.vehicles
    .filter((v) => (v as any).engine_temp != null)
    .map((v) => ({
      id: v.id === 'ego' ? 'EGO' : v.id.replace('agent_', 'Ajan '),
      temp: (v as any).engine_temp as number,
      status: (v as any).engine_status as string,
    })) ?? []

  const defaultMetrics = {
    collision_count: 0,
    near_miss_count: 0,
    min_safety_distance: 0,
    risk_score: 0,
    completion_time: 0,
    path_efficiency: 0,
    average_speed: 0,
    max_acceleration: 0,
    max_deceleration: 0,
    steering_smoothness: 0,
    task_completed: false,
    completion_rate: 0,
    algorithm_name: '—',
  }

  const m = simMetrics ?? (simStatus === 'idle' ? defaultMetrics : defaultMetrics)

  return (
    <div className="flex flex-col gap-2 p-3 bg-husim-surface rounded-lg h-full overflow-y-auto">
      <h2 className="text-sm font-bold text-husim-accent uppercase tracking-wider">{tr.metrics.title}</h2>

      {/* Risk Gauge */}
      <div className="flex justify-center py-1">
        <RiskGauge score={m?.risk_score ?? 0} />
      </div>

      {/* Speed Chart */}
      {speedData.length > 2 && (
        <div>
          <p className="text-xs text-slate-400 mb-1">Anlık Hız (m/s)</p>
          <ResponsiveContainer width="100%" height={50}>
            <LineChart data={speedData}>
              <Line type="monotone" dataKey="speed" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: 'none', fontSize: 10 }}
                labelFormatter={(v) => `${Number(v).toFixed(1)}s`}
                formatter={(v: any) => [`${Number(v).toFixed(2)} m/s`, 'Hız']}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Engine Status */}
      {vehicleEngineStates.length > 0 && (
        <div className="bg-slate-800/60 rounded p-2">
          <h4 className="text-xs font-bold mb-1.5 uppercase tracking-wider text-orange-400">
            {tr.engineSystem.title}
          </h4>
          <div className="space-y-1.5">
            {vehicleEngineStates.map((vs) => (
              <EngineTempBar key={vs.id} temp={vs.temp} vehicleId={vs.id} />
            ))}
          </div>
          {engineTempData.length > 2 && (
            <div className="mt-2">
              <p className="text-[10px] text-slate-500 mb-0.5">EGO Sıcaklık Grafiği</p>
              <ResponsiveContainer width="100%" height={40}>
                <LineChart data={engineTempData}>
                  <Line type="monotone" dataKey="temp" stroke="#f97316" strokeWidth={1.5} dot={false} />
                  <Tooltip
                    contentStyle={{ background: '#1e293b', border: 'none', fontSize: 10 }}
                    labelFormatter={(v) => `${Number(v).toFixed(1)}s`}
                    formatter={(v: any) => [`${Number(v).toFixed(1)}°C`, 'Sıcaklık']}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Metric Cards */}
      <MetricCard
        title={tr.metrics.safety}
        accentColor="#ef4444"
        items={[
          { label: tr.metrics.collisions, value: m?.collision_count ?? 0 },
          { label: tr.metrics.nearMisses, value: m?.near_miss_count ?? 0 },
          { label: 'Min. Mesafe', value: (m?.min_safety_distance ?? 0).toFixed(1), unit: 'm' },
        ]}
        progressItems={[
          {
            label: 'Güvenlik Skoru',
            pct: Math.max(0, 100 - (m?.risk_score ?? 0)),
            color: '#22c55e',
          },
        ]}
      />

      <MetricCard
        title={tr.metrics.efficiency}
        accentColor="#10b981"
        items={[
          { label: tr.metrics.completionTime, value: (m?.completion_time ?? 0).toFixed(1), unit: 'sn' },
          { label: tr.metrics.pathEfficiency, value: `%${((m?.path_efficiency ?? 0) * 100).toFixed(0)}` },
          { label: 'Ort. Hız', value: (m?.average_speed ?? 0).toFixed(1), unit: 'm/s' },
        ]}
        progressItems={[
          {
            label: 'Güzergah Verimliliği',
            pct: (m?.path_efficiency ?? 0) * 100,
            color: '#3b82f6',
          },
        ]}
      />

      <MetricCard
        title={tr.metrics.smoothness}
        accentColor="#60a5fa"
        items={[
          { label: 'Maks. İvme', value: (m?.max_acceleration ?? 0).toFixed(2), unit: 'm/s²' },
          { label: 'Maks. Frenleme', value: (m?.max_deceleration ?? 0).toFixed(2), unit: 'm/s²' },
          { label: 'Dümen Yumuşaklığı', value: `%${((m?.steering_smoothness ?? 0) * 100).toFixed(0)}` },
        ]}
        progressItems={[
          {
            label: 'Sürüş Yumuşaklığı',
            pct: (m?.steering_smoothness ?? 0) * 100,
            color: '#a78bfa',
          },
        ]}
      />

      {/* Task Status */}
      {simMetrics ? (
        <div className={`rounded p-2 text-center text-sm font-bold ${
          m.task_completed
            ? 'bg-husim-success/20 text-husim-success border border-husim-success/30'
            : 'bg-husim-danger/20 text-husim-danger border border-husim-danger/30'
        }`}>
          {m.task_completed ? `✓ ${tr.metrics.taskCompleted}` : `✗ ${tr.metrics.taskFailed}`}
          <span className="ml-2 text-xs opacity-75">({m.algorithm_name})</span>
        </div>
      ) : (
        <div className="rounded p-2 text-center text-xs text-slate-500 border border-slate-700">
          Simülasyon başlatılınca güncellenecek
        </div>
      )}
    </div>
  )
}
