import { useEffect } from 'react'
import { useStore } from '../store'
import { tr } from '../tr'
import { fetchActiveEvents, addEvent, deleteEvent, addRandomEvents } from '../api'

const EVENT_DEFS = [
  { type: 'kaya_dusme',       icon: '🪨', color: '#ef4444' },
  { type: 'yol_calismasi',    icon: '🚧', color: '#f59e0b' },
  { type: 'su_birikintisi',   icon: '💧', color: '#3b82f6' },
  { type: 'toz_bulutu',       icon: '💨', color: '#92400e' },
  { type: 'diger_arac_arizasi', icon: '🔧', color: '#7c3aed' },
] as const

export default function EventControlPanel() {
  const {
    activeEvents, setActiveEvents, removeEventZone,
    eventPlacingType, setEventPlacingType,
  } = useStore()

  // Periodically fetch active events
  useEffect(() => {
    const load = async () => {
      try {
        const data = await fetchActiveEvents()
        setActiveEvents(data.events ?? [])
      } catch { /* silent if backend is unavailable */ }
    }
    load()
    const id = setInterval(load, 3000)
    return () => clearInterval(id)
  }, [setActiveEvents])

  const handleQuickAdd = (eventType: string) => {
    setEventPlacingType(eventPlacingType === eventType ? null : eventType)
  }

  const handleRemove = async (eventId: string) => {
    try {
      await deleteEvent(eventId)
      removeEventZone(eventId)
    } catch { /* sessiz */ }
  }

  const handleRandom = async () => {
    try {
      await addRandomEvents({ count: 2, x_min: -40, x_max: 40, y_min: -40, y_max: 40 })
      const data = await fetchActiveEvents()
      setActiveEvents(data.events ?? [])
    } catch { /* sessiz */ }
  }

  const typeName = (t: string) => (tr.eventZones.types as Record<string, string>)[t] ?? t

  return (
    <div className="bg-husim-surface rounded-lg p-3 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-bold text-husim-accent uppercase tracking-wider">
          {tr.eventZones.title}
        </h3>
        <span className="text-xs text-slate-400">
          {tr.eventZones.active}: <span className="text-white font-bold">{activeEvents.length}</span>
        </span>
      </div>

      {/* Quick add buttons */}
      <div>
        <p className="text-[10px] text-slate-500 mb-1">{tr.eventZones.quickAdd}:</p>
        <div className="flex gap-1 flex-wrap">
          {EVENT_DEFS.map((def) => (
            <button
              key={def.type}
              onClick={() => handleQuickAdd(def.type)}
              title={typeName(def.type)}
              className={`text-base px-1.5 py-0.5 rounded border transition-all ${
                eventPlacingType === def.type
                  ? 'border-white bg-white/10 scale-110'
                  : 'border-slate-600 hover:border-slate-400 hover:bg-white/5'
              }`}
            >
              {def.icon}
            </button>
          ))}
          <button
            onClick={handleRandom}
            className="text-[10px] px-1.5 py-0.5 rounded border border-slate-600 text-slate-400 hover:text-white hover:border-slate-400"
          >
            {tr.eventZones.randomEvent}
          </button>
        </div>

        {eventPlacingType && (
          <div className="flex items-center justify-between mt-1.5">
            <p className="text-[10px] text-yellow-400 animate-pulse">
              📍 {tr.eventZones.clickToPlace}
            </p>
            <button
              onClick={() => setEventPlacingType(null)}
              className="text-[10px] text-slate-400 hover:text-white underline"
            >
              {tr.eventZones.cancelPlacing}
            </button>
          </div>
        )}
      </div>

      {/* Aktif olaylar listesi */}
      <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
        {activeEvents.length === 0 ? (
          <p className="text-[10px] text-slate-500 text-center py-2">{tr.eventZones.noEvents}</p>
        ) : (
          activeEvents.map((ev) => (
            <div
              key={ev.id}
              className="flex items-center justify-between rounded px-2 py-1 bg-slate-800/60"
            >
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-sm flex-shrink-0">{ev.icon}</span>
                <div className="min-w-0">
                  <p className="text-[10px] font-medium text-white truncate">{ev.name}</p>
                  <p className="text-[9px] text-slate-400">
                    ({ev.x.toFixed(0)}, {ev.y.toFixed(0)}) · {tr.eventZones.remainingTime}: {ev.remaining_time?.toFixed(0)}s
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleRemove(ev.id)}
                className="text-slate-500 hover:text-red-400 text-xs ml-1 flex-shrink-0"
              >
                ✕
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
