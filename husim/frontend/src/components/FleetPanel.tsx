import { useMemo } from 'react'
import { useStore } from '../store'
import { tr } from '../tr'

const STATUS_COLORS: Record<string, string> = {
  moving: 'text-emerald-400',
  slowing: 'text-yellow-400',
  waiting: 'text-red-400',
  completed: 'text-slate-400',
  approaching: 'text-blue-400',
  bypassing: 'text-purple-400',
}

const STATUS_DOT: Record<string, string> = {
  moving: 'bg-emerald-400',
  slowing: 'bg-yellow-400',
  waiting: 'bg-red-400',
  completed: 'bg-slate-500',
  approaching: 'bg-blue-400',
  bypassing: 'bg-purple-400',
}

const PRIORITY_COLORS: Record<string, string> = {
  '1': 'text-red-300',
  '2': 'text-orange-300',
  '3': 'text-yellow-300',
  '4': 'text-slate-400',
}

function statusLabel(status: string): string {
  const map = (tr.fleet.statuses as Record<string, string>)
  return map[status] ?? status
}

function priorityLabel(priority: number): string {
  const map = (tr.fleet.priorities as Record<string, string>)
  return map[String(priority)] ?? String(priority)
}

export default function FleetPanel() {
  const { frames, currentFrameIdx } = useStore()

  const currentFrame = frames[currentFrameIdx]

  const vehicles = useMemo(() => {
    if (!currentFrame) return []
    return currentFrame.vehicles.filter((v: any) => v.vehicle_type !== 'StaticObstacle')
  }, [currentFrame])

  const obstacle = useMemo(() => {
    if (!currentFrame) return null
    return currentFrame.vehicles.find((v: any) => v.vehicle_type === 'StaticObstacle') ?? null
  }, [currentFrame])

  // Filo özet — interventions: şu anda bekleyen veya yavaşlayan araç sayısı
  const summary = useMemo(() => {
    const active = vehicles.filter((v: any) => v.status === 'moving' || v.status === 'approaching' || v.status === 'bypassing').length
    const waiting = vehicles.filter((v: any) => v.status === 'waiting' || v.status === 'slowing').length
    const interventions = vehicles.filter((v: any) => v.status === 'waiting' || v.status === 'slowing').length
    return { active, waiting, interventions }
  }, [vehicles])

  // Fleet verisi var mı? (sadece status alanı olan araçlar için göster)
  const hasFleetData = vehicles.some((v: any) => v.status !== undefined)

  return (
    <div className="flex flex-col gap-1.5 p-3 bg-husim-surface rounded-lg text-xs">
      <h2 className="text-sm font-bold text-husim-accent uppercase tracking-wider shrink-0">
        {tr.fleet.title}
      </h2>

      {!hasFleetData || vehicles.length === 0 ? (
        <div className="text-slate-500 text-center py-2">{tr.fleet.noFleetData}</div>
      ) : (
        <>
          {/* Özet satırı */}
          <div className="flex gap-2 text-[10px] text-slate-400 border-b border-slate-700 pb-1.5">
            <span>
              <span className="text-emerald-400 font-bold">{summary.active}</span>{' '}
              {tr.fleet.summary.active}
            </span>
            <span>•</span>
            <span>
              <span className="text-red-400 font-bold">{summary.waiting}</span>{' '}
              {tr.fleet.summary.waiting}
            </span>
            <span>•</span>
            <span>
              <span className="text-yellow-400 font-bold">{summary.interventions}</span>{' '}
              {tr.fleet.summary.interventions}
            </span>
          </div>

          {/* Araç tablosu */}
          <div className="flex flex-col gap-1 max-h-48 overflow-y-auto">
            {vehicles.map((v: any) => {
              const isEgo = v.id === 'ego'
              const statusKey = v.status ?? 'moving'
              const dotClass = STATUS_DOT[statusKey] ?? 'bg-slate-500'
              const txtClass = STATUS_COLORS[statusKey] ?? 'text-slate-400'
              const priColor = PRIORITY_COLORS[String(v.priority)] ?? 'text-slate-400'

              return (
                <div
                  key={v.id}
                  className={`flex items-center gap-1.5 p-1.5 rounded border ${
                    isEgo
                      ? 'border-husim-accent/40 bg-husim-accent/5'
                      : 'border-slate-700/60 bg-slate-800/30'
                  }`}
                >
                  {/* Durum noktası */}
                  <span className={`w-2 h-2 rounded-full shrink-0 ${dotClass}`} />

                  {/* ID */}
                  <span className={`font-bold w-14 truncate ${isEgo ? 'text-husim-accent' : 'text-slate-300'}`}>
                    {isEgo ? 'EGO' : v.id.replace('agent_', '#')}
                  </span>

                  {/* Durum */}
                  <span className={`flex-1 ${txtClass}`}>{statusLabel(statusKey)}</span>

                  {/* Hız */}
                  <span className="text-slate-400 w-12 text-right tabular-nums">
                    {(v.speed ?? 0).toFixed(1)}m/s
                  </span>

                  {/* Öncelik */}
                  {v.priority !== undefined && (
                    <span className={`w-10 text-right shrink-0 ${priColor}`}>
                      {priorityLabel(v.priority)}
                    </span>
                  )}
                </div>
              )
            })}
          </div>

          {/* Engel uyarısı */}
          {obstacle && (
            <div className="flex items-center gap-1.5 text-[10px] text-red-400 border border-red-800/40 rounded px-2 py-1 bg-red-900/10 mt-0.5">
              <span>⚠</span>
              <span>{tr.fleet.obstacleDetected}</span>
            </div>
          )}
        </>
      )}
    </div>
  )
}
