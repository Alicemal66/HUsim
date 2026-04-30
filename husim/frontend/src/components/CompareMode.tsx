import { useEffect, useRef, useState } from 'react'
import { tr } from '../tr'
import { useStore } from '../store'
import { compareScenarios } from '../api'

const CW = 340
const CH = 250

interface Transform { scale: number; offX: number; offY: number }

function computeT(geom: any, frames: any[]): Transform {
  const pts: { x: number; y: number }[] = []
  if (geom?.segments) geom.segments.forEach((s: any) => { pts.push(s.from, s.to) })
  const step = Math.max(1, Math.floor(frames.length / 10))
  for (let i = 0; i < frames.length; i += step) {
    frames[i].vehicles.forEach((v: any) => pts.push({ x: v.x, y: v.y }))
  }
  if (!pts.length) return { scale: 3.5, offX: CW / 2, offY: CH / 2 }

  const xs = pts.map((p) => p.x)
  const ys = pts.map((p) => p.y)
  const pad = 15
  const minX = Math.min(...xs) - pad, maxX = Math.max(...xs) + pad
  const minY = Math.min(...ys) - pad, maxY = Math.max(...ys) + pad
  const margin = 20
  const scale = Math.min((CW - margin * 2) / Math.max(maxX - minX, 1), (CH - margin * 2) / Math.max(maxY - minY, 1))
  return { scale, offX: margin - minX * scale, offY: CH - margin + minY * scale }
}

function toPx(x: number, y: number, t: Transform) {
  return { cx: t.offX + x * t.scale, cy: t.offY - y * t.scale }
}

function drawScene(ctx: CanvasRenderingContext2D, geom: any, frame: any, t: Transform) {
  ctx.fillStyle = '#0c1117'
  ctx.fillRect(0, 0, CW, CH)

  // Roads
  if (geom?.segments) {
    for (const seg of geom.segments) {
      const { cx: x1, cy: y1 } = toPx(seg.from.x, seg.from.y, t)
      const { cx: x2, cy: y2 } = toPx(seg.to.x, seg.to.y, t)
      const w = Math.max(6, (seg.width ?? 8) * t.scale)
      ctx.strokeStyle = '#0c1f15'; ctx.lineWidth = w + 4; ctx.lineCap = 'round'
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
      ctx.strokeStyle = '#173d24'; ctx.lineWidth = w
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
    }
    ctx.setLineDash([8, 8])
    for (const seg of geom.segments) {
      const { cx: x1, cy: y1 } = toPx(seg.from.x, seg.from.y, t)
      const { cx: x2, cy: y2 } = toPx(seg.to.x, seg.to.y, t)
      ctx.strokeStyle = 'rgba(255,210,30,0.25)'; ctx.lineWidth = 1
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
    }
    ctx.setLineDash([])
    for (const z of geom.conflict_zones ?? []) {
      const { cx, cy } = toPx(z.x, z.y, t)
      const r = (z.r ?? 10) * t.scale
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, r)
      g.addColorStop(0, 'rgba(239,68,68,0.25)'); g.addColorStop(1, 'rgba(239,68,68,0)')
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fill()
    }
  }

  if (!frame) return

  // Vehicles
  let agN = 1
  for (const v of frame.vehicles) {
    const { cx, cy } = toPx(v.x, v.y, t)
    const isEgo = v.id === 'ego'
    const L = Math.max(10, ((v.length ?? (isEgo ? 8.5 : 5)) * t.scale))
    const W = Math.max(6, ((v.width ?? (isEgo ? 3.5 : 2)) * t.scale))
    const col = isEgo ? '#f59e0b' : '#3b82f6'
    const brd = isEgo ? '#fcd34d' : '#93c5fd'

    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(-v.heading)
    ctx.fillStyle = col; ctx.strokeStyle = brd; ctx.lineWidth = 1.2
    ctx.beginPath(); ctx.roundRect(-L / 2, -W / 2, L, W, 2); ctx.fill(); ctx.stroke()
    // front
    ctx.fillStyle = isEgo ? 'rgba(255,240,180,0.8)' : 'rgba(180,220,255,0.7)'
    ctx.beginPath(); ctx.roundRect(L / 2 - Math.min(4, L * 0.18), -W / 2 + 1.5, Math.min(4, L * 0.18), W - 3, 1); ctx.fill()
    ctx.restore()

    ctx.fillStyle = isEgo ? '#fcd34d' : '#93c5fd'
    ctx.font = `bold ${isEgo ? 9 : 8}px sans-serif`
    ctx.textAlign = 'center'; ctx.textBaseline = 'bottom'
    ctx.fillText(isEgo ? 'EGO' : String(agN++), cx, cy - W / 2 - 1)
  }
}

interface SideData {
  frames: any[]
  road_geometry: any
  metrics: { risk_score: number; collision_count: number; average_speed: number }
}

export default function CompareMode() {
  const { selectedScenario, optimizedParams } = useStore()
  const normalCanvas = useRef<HTMLCanvasElement>(null)
  const optCanvas = useRef<HTMLCanvasElement>(null)

  const [data, setData] = useState<{ normal: SideData; optimized: SideData } | null>(null)
  const [loading, setLoading] = useState(false)
  const [frameIdx, setFrameIdx] = useState(0)
  const [playing, setPlaying] = useState(false)
  const playRef = useRef(false)
  playRef.current = playing

  async function handleCompare() {
    if (!selectedScenario) return
    setLoading(true)
    setData(null)
    setFrameIdx(0)
    setPlaying(false)
    try {
      const res = await compareScenarios({
        scenario_id: selectedScenario,
        weather_params: optimizedParams ?? {},
      })
      setData(res)
    } catch (e) {
      console.error('Karşılaştırma hatası:', e)
    } finally {
      setLoading(false)
    }
  }

  // Playback
  useEffect(() => {
    if (!playing || !data) return
    const totalFrames = data.normal.frames.length
    const id = setInterval(() => {
      if (!playRef.current) return
      setFrameIdx((prev) => {
        if (prev + 1 >= totalFrames) { setPlaying(false); return prev }
        return prev + 1
      })
    }, 100)
    return () => clearInterval(id)
  }, [playing, data])

  // Canvas render
  useEffect(() => {
    if (!data) return

    const nFrame = data.normal.frames[frameIdx]
    const oFrame = data.optimized.frames[frameIdx]
    const t = computeT(data.normal.road_geometry, data.normal.frames)

    const nc = normalCanvas.current
    const oc = optCanvas.current
    if (nc) {
      const ctx = nc.getContext('2d')!
      drawScene(ctx, data.normal.road_geometry, nFrame, t)
    }
    if (oc) {
      const ctx = oc.getContext('2d')!
      drawScene(ctx, data.optimized.road_geometry, oFrame, t)
    }
  }, [data, frameIdx])

  const totalFrames = data?.normal.frames.length ?? 0

  return (
    <div className="p-3 bg-husim-surface rounded-lg flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-husim-accent uppercase tracking-wider">
          {tr.compareMode.title}
        </h2>
        <button
          onClick={handleCompare}
          disabled={!selectedScenario || loading}
          className="text-xs px-2.5 py-1 rounded bg-blue-700 text-white hover:bg-blue-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? tr.compareMode.comparing : 'Karşılaştır'}
        </button>
      </div>

      {!selectedScenario && (
        <p className="text-xs text-slate-500 italic">{tr.compareMode.selectScenario}</p>
      )}

      {data && (
        <>
          {/* Yan yana canvas'lar */}
          <div className="grid grid-cols-2 gap-2">
            {/* Normal */}
            <div className="flex flex-col gap-1">
              <div className="flex flex-col items-center gap-0.5">
                <div className="text-xs font-bold text-slate-300 text-center">{tr.compareMode.normal}</div>
                <div className="text-[10px] text-slate-500 text-center">Standart (Literatür Değerleri)</div>
              </div>
              <canvas
                ref={normalCanvas}
                width={CW}
                height={CH}
                style={{ width: '100%', height: 'auto', display: 'block', borderRadius: 4 }}
              />
              <div className="grid grid-cols-3 gap-1 text-center">
                <div className="bg-slate-700 rounded p-1">
                  <div className="text-[10px] text-slate-400">{tr.compareMode.risk}</div>
                  <div className={`text-xs font-bold ${data.normal.metrics.risk_score > 60 ? 'text-red-400' : 'text-yellow-400'}`}>
                    {data.normal.metrics.risk_score}/100
                  </div>
                </div>
                <div className="bg-slate-700 rounded p-1">
                  <div className="text-[10px] text-slate-400">{tr.compareMode.avgSpeed}</div>
                  <div className="text-xs font-bold text-slate-200">{data.normal.metrics.average_speed.toFixed(1)}m/s</div>
                </div>
                <div className="bg-slate-700 rounded p-1">
                  <div className="text-[10px] text-slate-400">{tr.compareMode.collisions}</div>
                  <div className={`text-xs font-bold ${data.normal.metrics.collision_count > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                    {data.normal.metrics.collision_count}
                  </div>
                </div>
              </div>
            </div>

            {/* Optimize */}
            <div className="flex flex-col gap-1">
              <div className="flex flex-col items-center gap-0.5">
                <div className="text-xs font-bold text-emerald-400 text-center">{tr.compareMode.optimized}</div>
                <div className="text-[10px] text-emerald-700 text-center">HÜsim Optimize (Levin Telematics Kalibrasyonu)</div>
              </div>
              <canvas
                ref={optCanvas}
                width={CW}
                height={CH}
                style={{ width: '100%', height: 'auto', display: 'block', borderRadius: 4 }}
              />
              <div className="grid grid-cols-3 gap-1 text-center">
                <div className="bg-slate-700 rounded p-1">
                  <div className="text-[10px] text-slate-400">{tr.compareMode.risk}</div>
                  <div className={`text-xs font-bold ${data.optimized.metrics.risk_score > 30 ? 'text-yellow-400' : 'text-emerald-400'}`}>
                    {data.optimized.metrics.risk_score}/100
                  </div>
                </div>
                <div className="bg-slate-700 rounded p-1">
                  <div className="text-[10px] text-slate-400">{tr.compareMode.avgSpeed}</div>
                  <div className="text-xs font-bold text-slate-200">{data.optimized.metrics.average_speed.toFixed(1)}m/s</div>
                </div>
                <div className="bg-slate-700 rounded p-1">
                  <div className="text-[10px] text-slate-400">{tr.compareMode.collisions}</div>
                  <div className={`text-xs font-bold ${data.optimized.metrics.collision_count > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                    {data.optimized.metrics.collision_count}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Shared playback controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => { setPlaying(false); setFrameIdx(0) }}
              className="text-slate-400 hover:text-white text-xs px-1"
            >⏮</button>
            <button
              onClick={() => setPlaying(!playing)}
              className={`text-sm font-bold px-2 ${playing ? 'text-husim-accent' : 'text-slate-300'} hover:text-white`}
            >
              {playing ? '⏸' : '▶'}
            </button>
            <button
              onClick={() => { setPlaying(false); setFrameIdx(totalFrames - 1) }}
              className="text-slate-400 hover:text-white text-xs px-1"
            >⏭</button>
            <input
              type="range"
              min={0}
              max={Math.max(0, totalFrames - 1)}
              value={frameIdx}
              onChange={(e) => { setPlaying(false); setFrameIdx(Number(e.target.value)) }}
              className="flex-1 h-1"
              style={{ accentColor: '#f59e0b' }}
            />
            <span className="text-xs text-slate-400 tabular-nums min-w-[48px] text-right">
              {frameIdx + 1}/{totalFrames}
            </span>
          </div>

          {/* Fark tablosu */}
          <div className="bg-slate-800/60 rounded p-2">
            <div className="text-[10px] font-bold text-husim-accent uppercase tracking-wider mb-1.5">
              Parametre İyileştirme Tablosu
            </div>
            <div className="space-y-1">
              {[
                {
                  label: 'Risk Skoru',
                  normal: data.normal.metrics.risk_score,
                  opt: data.optimized.metrics.risk_score,
                  unit: '/100',
                  lowerIsBetter: true,
                },
                {
                  label: 'Ortalama Hız',
                  normal: data.normal.metrics.average_speed,
                  opt: data.optimized.metrics.average_speed,
                  unit: ' m/s',
                  lowerIsBetter: false,
                },
                {
                  label: 'Çarpışma',
                  normal: data.normal.metrics.collision_count,
                  opt: data.optimized.metrics.collision_count,
                  unit: ' adet',
                  lowerIsBetter: true,
                },
              ].map((row) => {
                const diff = row.opt - row.normal
                const improved = row.lowerIsBetter ? diff < 0 : diff > 0
                const pct = row.normal !== 0 ? Math.abs(diff / row.normal * 100).toFixed(0) : '—'
                return (
                  <div key={row.label} className="flex items-center gap-2 text-[10px]">
                    <span className="text-slate-400 w-20">{row.label}</span>
                    <span className="text-slate-300 w-12 text-right">{row.normal.toFixed(1)}{row.unit}</span>
                    <span className="text-slate-500">→</span>
                    <span className="text-slate-300 w-12 text-right">{row.opt.toFixed(1)}{row.unit}</span>
                    <span className={`ml-auto font-bold ${improved ? 'text-emerald-400' : diff === 0 ? 'text-slate-400' : 'text-red-400'}`}>
                      {diff === 0 ? '=' : improved ? `↓${pct}%` : `↑${pct}%`}
                    </span>
                  </div>
                )
              })}
            </div>
            <div className="mt-1.5 pt-1.5 border-t border-slate-700">
              <div style={{
                background: '#1a3a1a', border: '1px solid #22c55e',
                borderRadius: '4px', padding: '2px 8px',
                fontSize: '10px', color: '#22c55e', display: 'inline-flex',
                alignItems: 'center', gap: '4px',
              }}>
                <span>✓</span><span>Levin Telematics — 15,847 gerçek araç verisi</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
