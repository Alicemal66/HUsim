import { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import { useStore } from '../store'
import { tr } from '../tr'
import { addEvent, fetchActiveEvents } from '../api'

const SPEED_OPTIONS = [0.5, 1, 2, 4]
const FRAME_MS_AT_1X = 100

interface Transform {
  scale: number
  offX: number
  offY: number
}

function getSafetyScaleFactor(optimizedParams: any): number {
  if (!optimizedParams) return 1.0
  const risk = optimizedParams.risk_level
  if (risk === 'kritik') return 2.0
  if (risk === 'yüksek') return 1.6
  if (risk === 'orta') return 1.3
  return 1.0
}

function computeTransform(
  roadGeometry: any,
  sampleVehicles: { x: number; y: number }[],
  cw: number,
  ch: number,
): Transform {
  const vb = roadGeometry?.viewport_bounds
  if (vb && typeof vb.x_min === 'number') {
    const pad = 12
    const minX = vb.x_min - pad
    const maxX = vb.x_max + pad
    const minY = vb.y_min - pad
    const maxY = vb.y_max + pad
    const wW = Math.max(maxX - minX, 1)
    const wH = Math.max(maxY - minY, 1)
    const margin = 24
    const scale = Math.min((cw - margin * 2) / wW, (ch - margin * 2) / wH)
    const offX = margin - minX * scale
    const offY = ch - margin + minY * scale
    return { scale, offX, offY }
  }

  const pts: { x: number; y: number }[] = []
  if (roadGeometry?.segments) {
    for (const seg of roadGeometry.segments) {
      pts.push(seg.from, seg.to)
    }
  }
  for (const v of sampleVehicles) pts.push(v)

  if (pts.length === 0) {
    return { scale: 4.5, offX: cw / 2 - 50, offY: ch / 2 }
  }

  const xs = pts.map((p) => p.x)
  const ys = pts.map((p) => p.y)
  const pad = 18
  const minX = Math.min(...xs) - pad
  const maxX = Math.max(...xs) + pad
  const minY = Math.min(...ys) - pad
  const maxY = Math.max(...ys) + pad
  const wW = Math.max(maxX - minX, 1)
  const wH = Math.max(maxY - minY, 1)
  const margin = 28
  const scale = Math.min((cw - margin * 2) / wW, (ch - margin * 2) / wH)
  const offX = margin - minX * scale
  const offY = ch - margin + minY * scale
  return { scale, offX, offY }
}

// userZoom ve userPan'ı base transform'a uygula
function applyUserTransform(base: Transform, userZoom: number, userPan: { x: number; y: number }): Transform {
  return {
    scale: base.scale * userZoom,
    offX: base.offX * userZoom + userPan.x,
    offY: base.offY * userZoom + userPan.y,
  }
}

function toCanvas(x: number, y: number, t: Transform) {
  return { cx: t.offX + x * t.scale, cy: t.offY - y * t.scale }
}

function drawRoads(ctx: CanvasRenderingContext2D, geom: any, t: Transform, ch: number) {
  // Katman 2 — drivable_polygons varsa MineSim tarzı çiz
  if (geom?.drivable_polygons?.length) {
    for (const poly of geom.drivable_polygons) {
      if (!poly.points?.length) continue
      const pts = poly.points.map((p: any) => toCanvas(p.x, p.y, t))
      ctx.beginPath()
      pts.forEach(({ cx: px, cy: py }: any, i: number) => {
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)
      })
      ctx.closePath()
      if (poly.type === 'intersection') {
        ctx.fillStyle = '#3d2a2e'
      } else if (poly.type === 'loading') {
        ctx.fillStyle = '#3a3820'
      } else {
        ctx.fillStyle = '#3d3d3d'
      }
      ctx.fill()
      ctx.strokeStyle = '#555'
      ctx.lineWidth = 1
      ctx.stroke()
    }

    // Katman 3 — centerlines
    for (const cl of geom.centerlines ?? []) {
      if (!cl.points?.length) continue
      const pts = cl.points.map((p: any) => toCanvas(p.x, p.y, t))
      ctx.beginPath()
      pts.forEach(({ cx: px, cy: py }: any, i: number) => {
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)
      })
      if (cl.type === 'connector') {
        ctx.strokeStyle = 'rgba(102,153,204,0.4)'
        ctx.setLineDash([3, 5])
      } else {
        ctx.strokeStyle = 'rgba(136,136,136,0.5)'
        ctx.setLineDash([8, 6])
      }
      ctx.lineWidth = 1
      ctx.lineCap = 'butt'
      ctx.stroke()
      ctx.setLineDash([])
    }
  } else if (geom?.segments) {
    // Fallback: eski segment tarzı
    for (const seg of geom.segments) {
      const { cx: x1, cy: y1 } = toCanvas(seg.from.x, seg.from.y, t)
      const { cx: x2, cy: y2 } = toCanvas(seg.to.x, seg.to.y, t)
      const w = Math.max(8, (seg.width ?? 8) * t.scale)
      ctx.strokeStyle = '#3d3d3d'
      ctx.lineWidth = w + 4
      ctx.lineCap = 'round'
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
      ctx.strokeStyle = '#3d3d3d'
      ctx.lineWidth = w
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
    }
    ctx.setLineDash([8, 6])
    for (const seg of geom.segments) {
      const { cx: x1, cy: y1 } = toCanvas(seg.from.x, seg.from.y, t)
      const { cx: x2, cy: y2 } = toCanvas(seg.to.x, seg.to.y, t)
      ctx.strokeStyle = 'rgba(136,136,136,0.5)'
      ctx.lineWidth = 1
      ctx.lineCap = 'butt'
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke()
    }
    ctx.setLineDash([])
  } else {
    // Hiç geometri yok
    ctx.strokeStyle = '#3d3d3d'
    ctx.lineWidth = 32
    ctx.lineCap = 'round'
    ctx.beginPath()
    ctx.moveTo(30, ch / 2)
    ctx.lineTo(ctx.canvas.width - 30, ch / 2)
    ctx.stroke()
    ctx.strokeStyle = 'rgba(136,136,136,0.5)'
    ctx.lineWidth = 1
    ctx.setLineDash([8, 6])
    ctx.beginPath()
    ctx.moveTo(30, ch / 2)
    ctx.lineTo(ctx.canvas.width - 30, ch / 2)
    ctx.stroke()
    ctx.setLineDash([])
    return
  }

  // Conflict zones
  for (const zone of geom.conflict_zones ?? []) {
    const { cx, cy } = toCanvas(zone.x, zone.y, t)
    const r = (zone.r ?? 10) * t.scale
    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, r)
    grad.addColorStop(0, 'rgba(239,68,68,0.28)')
    grad.addColorStop(0.6, 'rgba(239,68,68,0.10)')
    grad.addColorStop(1, 'rgba(239,68,68,0)')
    ctx.fillStyle = grad
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.fill()
    ctx.strokeStyle = 'rgba(239,68,68,0.45)'
    ctx.lineWidth = 1.5
    ctx.setLineDash([5, 5])
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.stroke()
    ctx.setLineDash([])
    ctx.fillStyle = 'rgba(239,68,68,0.7)'
    ctx.font = '10px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('⚡', cx, cy + 3.5)
  }
}

function speedToColor(speed: number): string {
  if (speed < 2) return '#3b82f6'   // düşük hız — mavi
  if (speed < 5) return '#8b5cf6'   // orta hız — mor
  if (speed < 8) return '#f97316'   // yüksek hız — turuncu
  return '#ef4444'                  // çok yüksek hız — kırmızı
}

function drawNorthArrow(ctx: CanvasRenderingContext2D, cw: number, userZoom: number) {
  const x = cw - 55
  const y = 55
  const arrowLen = 16

  ctx.save()
  ctx.fillStyle = 'rgba(0,0,0,0.45)'
  ctx.beginPath()
  ctx.arc(x, y, 26, 0, Math.PI * 2)
  ctx.fill()

  // N ok (yukarı)
  ctx.strokeStyle = '#e2e8f0'
  ctx.lineWidth = 2
  ctx.lineCap = 'round'
  ctx.beginPath()
  ctx.moveTo(x, y + arrowLen / 2)
  ctx.lineTo(x, y - arrowLen / 2)
  ctx.stroke()
  ctx.beginPath()
  ctx.moveTo(x, y - arrowLen / 2)
  ctx.lineTo(x - 4, y - arrowLen / 2 + 6)
  ctx.moveTo(x, y - arrowLen / 2)
  ctx.lineTo(x + 4, y - arrowLen / 2 + 6)
  ctx.stroke()

  ctx.fillStyle = '#e2e8f0'
  ctx.font = 'bold 9px sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText('N', x, y - arrowLen / 2 - 8)

  // E (sağa)
  ctx.strokeStyle = 'rgba(200,210,220,0.6)'
  ctx.lineWidth = 1.2
  ctx.beginPath()
  ctx.moveTo(x + 4, y)
  ctx.lineTo(x + arrowLen / 2, y)
  ctx.stroke()
  ctx.fillStyle = 'rgba(200,210,220,0.7)'
  ctx.font = '8px sans-serif'
  ctx.fillText('E', x + arrowLen / 2 + 7, y)

  // Zoom göstergesi
  ctx.fillStyle = 'rgba(148,163,184,0.85)'
  ctx.font = '9px monospace'
  ctx.textAlign = 'center'
  ctx.fillText(`${userZoom.toFixed(1)}×`, x, y + 22)

  ctx.restore()
}

function drawBottomStrip(
  ctx: CanvasRenderingContext2D,
  frame: any,
  scenarioId: string,
  scenarioType: string,
  cw: number,
  ch: number,
) {
  const stripH = 22
  const y0 = ch - stripH
  ctx.fillStyle = 'rgba(10,12,16,0.85)'
  ctx.fillRect(0, y0, cw, stripH)

  const ego = frame?.vehicles?.find((v: any) => v.id === 'ego')
  const t = frame?.time ?? 0

  ctx.font = '9px monospace'
  ctx.textBaseline = 'middle'
  const my = y0 + stripH / 2

  ctx.fillStyle = '#9ca3af'
  ctx.textAlign = 'left'
  ctx.fillText(`${scenarioId}  |  ${scenarioType}  |  t=${t.toFixed(1)}s`, 8, my)

  if (ego) {
    ctx.textAlign = 'right'
    ctx.fillStyle = '#9ca3af'
    ctx.fillText(`EGO: ${ego.speed?.toFixed(1) ?? '—'} m/s`, cw - 8, my)
  }
}

function drawGoalPolygon(
  ctx: CanvasRenderingContext2D,
  geom: any,
  t: Transform,
  reached: boolean,
) {
  const poly: { x: number; y: number }[] | undefined = geom?.goal_polygon
  if (!poly || poly.length < 3) return

  const pts = poly.map((p) => toCanvas(p.x, p.y, t))

  ctx.beginPath()
  pts.forEach(({ cx, cy }, i) => {
    i === 0 ? ctx.moveTo(cx, cy) : ctx.lineTo(cx, cy)
  })
  ctx.closePath()

  ctx.fillStyle = reached ? 'rgba(239,68,68,0.28)' : 'rgba(239,68,68,0.08)'
  ctx.fill()
  ctx.strokeStyle = reached ? 'rgba(239,68,68,0.95)' : 'rgba(239,68,68,0.55)'
  ctx.lineWidth = reached ? 2.5 : 1.5
  ctx.setLineDash([8, 5])
  ctx.stroke()
  ctx.setLineDash([])

  const gcx = pts.reduce((s, p) => s + p.cx, 0) / pts.length
  const gcy = pts.reduce((s, p) => s + p.cy, 0) / pts.length
  ctx.fillStyle = reached ? '#ef4444' : 'rgba(239,68,68,0.65)'
  ctx.font = `bold ${reached ? 12 : 9}px sans-serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(reached ? '✓ HEDEF' : 'HEDEF', gcx, gcy)
}

function drawVehicle(
  ctx: CanvasRenderingContext2D,
  v: any,
  t: Transform,
  isCollision: boolean,
  label: string,
  safetyScale: number,
  cw: number,
) {
  const { cx, cy } = toCanvas(v.x, v.y, t)
  const isEgo = v.id === 'ego'
  const isObstacle = v.vehicle_type === 'StaticObstacle'
  const rawL = v.length ?? (isEgo ? 8.5 : 5.0)
  const rawW = v.width ?? (isEgo ? 3.5 : 2.0)

  const minL = isEgo ? 18 : 10
  const maxL = cw * 0.15
  const L = Math.max(minL, Math.min(maxL, rawL * t.scale))
  const W = Math.max(isEgo ? 10 : 6, Math.min(L * 0.55, rawW * t.scale))

  if (isEgo && !isObstacle) {
    const safeR = Math.max(30, 15 * t.scale * safetyScale)
    const warnR = Math.max(20, 8 * t.scale * safetyScale)

    const gGrad = ctx.createRadialGradient(cx, cy, warnR, cx, cy, safeR)
    gGrad.addColorStop(0, 'rgba(34,197,94,0.0)')
    gGrad.addColorStop(1, 'rgba(34,197,94,0.06)')
    ctx.fillStyle = gGrad
    ctx.beginPath()
    ctx.arc(cx, cy, safeR, 0, Math.PI * 2)
    ctx.fill()

    const yGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, warnR)
    yGrad.addColorStop(0, 'rgba(234,179,8,0.08)')
    yGrad.addColorStop(1, 'rgba(234,179,8,0.0)')
    ctx.fillStyle = yGrad
    ctx.beginPath()
    ctx.arc(cx, cy, warnR, 0, Math.PI * 2)
    ctx.fill()

    const isStopped = (v.speed ?? 0) < 0.3
    ctx.strokeStyle = isStopped ? 'rgba(239,68,68,0.35)' : 'rgba(34,197,94,0.25)'
    ctx.lineWidth = 1
    ctx.setLineDash([4, 6])
    ctx.beginPath()
    ctx.arc(cx, cy, safeR, 0, Math.PI * 2)
    ctx.stroke()
    ctx.setLineDash([])
  }

  ctx.save()
  ctx.translate(cx, cy)
  ctx.rotate(-v.heading)

  const isStopped = (v.speed ?? 0) < 0.3
  let bodyColor: string
  let glowColor: string

  if (isObstacle) {
    bodyColor = '#6b7280'; glowColor = '#9ca3af'
  } else if (isCollision) {
    bodyColor = '#ef4444'; glowColor = '#fca5a5'
  } else if (isEgo) {
    bodyColor = isStopped ? '#dc2626' : '#f59e0b'
    glowColor = isStopped ? '#fca5a5' : '#fcd34d'
  } else {
    bodyColor = '#3b82f6'; glowColor = '#93c5fd'
  }

  ctx.shadowColor = glowColor
  ctx.shadowBlur = isEgo ? 12 : 5

  ctx.fillStyle = bodyColor
  ctx.lineWidth = isEgo ? 2 : 1.5
  ctx.strokeStyle = isEgo ? (isStopped ? '#ef4444' : '#22c55e') : glowColor
  ctx.beginPath()
  const radius = Math.min(4, W * 0.25)
  ctx.roundRect(-L / 2, -W / 2, L, W, radius)
  ctx.fill()
  ctx.stroke()
  ctx.shadowBlur = 0

  if (!isObstacle) {
    // Ön kısım — daha parlak renk (farlar)
    const frontW = Math.min(6, L * 0.20)
    const frontColor = isEgo ? 'rgba(255,240,180,0.95)' : 'rgba(180,220,255,0.85)'
    ctx.fillStyle = frontColor
    ctx.beginPath()
    ctx.roundRect(L / 2 - frontW, -W / 2 + 2, frontW, W - 4, 1)
    ctx.fill()

    // Arka kısım — kırmızımsı (stop ışıkları)
    const rearW = Math.min(4, L * 0.12)
    ctx.fillStyle = isEgo ? 'rgba(220,50,50,0.7)' : 'rgba(180,50,50,0.5)'
    ctx.beginPath()
    ctx.roundRect(-L / 2, -W / 2 + 3, rearW, W - 6, 1)
    ctx.fill()

    // Tekerlekler — 4 köşede siyah dikdörtgenler
    const wheelW = Math.max(3, L * 0.10)
    const wheelH = Math.max(3, W * 0.22)
    ctx.fillStyle = '#111'
    const wheelPositions = [
      { x: L / 2 - wheelW - 1, y: -W / 2 },          // sağ ön
      { x: L / 2 - wheelW - 1, y: W / 2 - wheelH },  // sağ arka
      { x: -L / 2 + 1, y: -W / 2 },                  // sol ön
      { x: -L / 2 + 1, y: W / 2 - wheelH },           // sol arka
    ]
    for (const wp of wheelPositions) {
      ctx.beginPath()
      ctx.roundRect(wp.x, wp.y, wheelW, wheelH, 1)
      ctx.fill()
    }

    // Yön oku — kalın ve belirgin
    const arrowStart = -L * 0.25
    const arrowEnd = L / 2 - frontW - 4
    ctx.strokeStyle = 'rgba(255,255,255,0.70)'
    ctx.lineWidth = isEgo ? 2.5 : 1.8
    ctx.lineCap = 'round'
    ctx.beginPath()
    ctx.moveTo(arrowStart, 0)
    ctx.lineTo(arrowEnd, 0)
    ctx.stroke()
    ctx.beginPath()
    const ah = arrowEnd
    ctx.moveTo(ah, 0)
    ctx.lineTo(ah - 6, -3.5)
    ctx.moveTo(ah, 0)
    ctx.lineTo(ah - 6, 3.5)
    ctx.stroke()
  } else {
    ctx.strokeStyle = '#ef4444'
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(-L * 0.3, -W * 0.3)
    ctx.lineTo(L * 0.3, W * 0.3)
    ctx.moveTo(L * 0.3, -W * 0.3)
    ctx.lineTo(-L * 0.3, W * 0.3)
    ctx.stroke()
  }

  ctx.restore()

  ctx.save()
  ctx.fillStyle = isObstacle ? '#ef4444' : isEgo ? (isStopped ? '#fca5a5' : '#fcd34d') : '#93c5fd'
  ctx.font = `bold ${isEgo ? 11 : 10}px sans-serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'bottom'
  ctx.fillText(isObstacle ? 'ENGEL' : label, cx, cy - W / 2 - 2)
  ctx.restore()

  if (!isObstacle && (v.speed ?? 0) > 0.2) {
    ctx.save()
    ctx.fillStyle = 'rgba(200,220,200,0.65)'
    ctx.font = '8px monospace'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillText(`${(v.speed ?? 0).toFixed(1)}m/s`, cx, cy + W / 2 + 3)
    ctx.restore()
  }

  // Motor sıcaklığı göstergesi
  if (!isObstacle && v.engine_temp != null) {
    const temp: number = v.engine_temp
    const status: string = v.engine_status ?? 'normal'
    let tempColor = '#9ca3af'
    let tempIcon = '🌡'
    if (status === 'acil_durdurma') { tempColor = '#ef4444'; tempIcon = '🚨' }
    else if (status === 'kritik') { tempColor = '#ef4444'; tempIcon = '🔥' }
    else if (status === 'uyarı') { tempColor = '#f59e0b'; tempIcon = '⚠' }

    ctx.save()
    ctx.font = 'bold 9px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'bottom'

    if (status === 'acil_durdurma') {
      // Kırmızı flash efekti — Math.sin kullanarak
      const flash = Math.abs(Math.sin(Date.now() / 200)) > 0.5
      if (flash) {
        ctx.fillStyle = '#ef4444'
        ctx.fillText(`${tempIcon} ACİL DURDURMA`, cx, cy - W / 2 - 14)
      }
    } else if (status === 'kritik' || status === 'uyarı') {
      ctx.fillStyle = tempColor
      ctx.fillText(`${tempIcon} ${temp.toFixed(0)}°C`, cx, cy - W / 2 - 14)
    } else {
      ctx.fillStyle = tempColor
      ctx.font = '8px sans-serif'
      ctx.fillText(`${temp.toFixed(0)}°C`, cx, cy - W / 2 - 14)
    }
    ctx.restore()

    // Kritik durumda araç kenarı kırmızı çizgi
    if (status === 'kritik') {
      ctx.save()
      ctx.translate(cx, cy)
      ctx.rotate(-v.heading)
      ctx.strokeStyle = '#ef4444'
      ctx.lineWidth = 3
      ctx.setLineDash([])
      ctx.beginPath()
      ctx.roundRect(-L / 2, -W / 2, L, W, Math.min(4, W * 0.25))
      ctx.stroke()
      ctx.restore()
    } else if (status === 'acil_durdurma') {
      ctx.save()
      ctx.translate(cx, cy)
      ctx.rotate(-v.heading)
      const flash2 = Math.abs(Math.sin(Date.now() / 200)) > 0.5
      ctx.strokeStyle = flash2 ? '#ef4444' : '#fca5a5'
      ctx.lineWidth = 4
      ctx.beginPath()
      ctx.roundRect(-L / 2, -W / 2, L, W, Math.min(4, W * 0.25))
      ctx.stroke()
      ctx.restore()
    }
  }
}

function drawInfoPanel(
  ctx: CanvasRenderingContext2D,
  frame: any,
  frameDisplayIdx: number,
  totalFrames: number,
  hasCollision: boolean,
  userZoom: number,
  cw: number,
  ch: number,
) {
  const ego = frame.vehicles.find((v: any) => v.id === 'ego')
  const agentCount = frame.vehicles.filter((v: any) => v.id !== 'ego').length

  ctx.fillStyle = 'rgba(0,0,0,0.65)'
  ctx.beginPath()
  ctx.roundRect(6, 6, 182, 68, 4)
  ctx.fill()

  ctx.textBaseline = 'top'
  ctx.fillStyle = '#f59e0b'
  ctx.font = 'bold 10px monospace'
  ctx.textAlign = 'left'
  // Sorun 1 düzeltme: frame.frame+1 yerine frameDisplayIdx kullan (slider ile uyumlu)
  ctx.fillText(`Frame ${frameDisplayIdx} / ${totalFrames}`, 12, 11)

  ctx.fillStyle = '#9ca3af'
  ctx.font = '9px monospace'
  ctx.fillText(`Süre: ${frame.time.toFixed(1)}s`, 12, 26)
  ctx.fillText(`Ajan: ${agentCount} araç`, 12, 39)
  if (ego) {
    const hue = Math.max(0, 120 - (ego.speed / 12) * 120)
    ctx.fillStyle = `hsl(${hue},85%,60%)`
    ctx.fillText(`EGO: ${ego.speed.toFixed(1)} m/s`, 12, 52)
  }

  // Zoom seviyesi — sağ üst köşe
  ctx.fillStyle = 'rgba(0,0,0,0.5)'
  ctx.beginPath()
  ctx.roundRect(cw - 50, 6, 44, 18, 3)
  ctx.fill()
  ctx.fillStyle = '#94a3b8'
  ctx.font = '9px monospace'
  ctx.textAlign = 'right'
  ctx.textBaseline = 'top'
  ctx.fillText(`🔍 ${userZoom.toFixed(1)}x`, cw - 8, 11)

  if (hasCollision) {
    ctx.fillStyle = 'rgba(239,68,68,0.18)'
    ctx.fillRect(0, 0, cw, ch)
    ctx.fillStyle = '#ef4444'
    ctx.font = 'bold 20px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillText('⚠ ÇARPIŞMA!', cw / 2, 10)
  }
}

function drawGradeIndicator(
  ctx: CanvasRenderingContext2D,
  grade: number | undefined,
  cw: number,
  ch: number,
) {
  if (grade === undefined || grade === null) return
  const x = 10
  const y = ch - 52
  const w = 110
  const h = 22

  ctx.fillStyle = 'rgba(0,0,0,0.55)'
  ctx.beginPath()
  ctx.roundRect(x, y, w, h, 4)
  ctx.fill()

  let label: string
  let color: string
  if (grade > 0) {
    label = `↗ +${grade}% Yokuş Yukarı`
    color = '#22c55e'
  } else if (grade < 0) {
    label = `↘ ${grade}% Yokuş Aşağı`
    color = '#eab308'
  } else {
    label = '→ 0% Düz'
    color = '#94a3b8'
  }

  ctx.fillStyle = color
  ctx.font = 'bold 9px monospace'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  ctx.fillText(label, x + 6, y + h / 2)
}

function drawCollisionAvoidanceRing(
  ctx: CanvasRenderingContext2D,
  ego: any,
  t: Transform,
  phase: 'warning' | 'braking' | 'none',
) {
  if (!ego || phase === 'none') return
  const { cx, cy } = toCanvas(ego.x, ego.y, t)
  const r = Math.max(28, 16 * t.scale)

  ctx.save()
  if (phase === 'braking') {
    ctx.strokeStyle = 'rgba(239,68,68,0.85)'
    ctx.lineWidth = 3
    ctx.setLineDash([6, 4])
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.stroke()
    ctx.fillStyle = 'rgba(239,68,68,0.7)'
    ctx.font = 'bold 8px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText('FRENLEME', cx, cy - r - 8)
  } else {
    ctx.strokeStyle = 'rgba(234,179,8,0.75)'
    ctx.lineWidth = 2
    ctx.setLineDash([5, 5])
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.stroke()
  }
  ctx.setLineDash([])
  ctx.restore()
}

function drawEventZones(
  ctx: CanvasRenderingContext2D,
  events: any[],
  t: Transform,
  currentTime: number,
  vehicles: any[],
) {
  for (const ev of events) {
    const { cx, cy } = toCanvas(ev.x, ev.y, t)
    const r = ev.radius_m * t.scale

    // Yarı şeffaf dolgu
    ctx.save()
    ctx.globalAlpha = 0.25
    ctx.fillStyle = ev.color ?? '#888'
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.fill()
    ctx.globalAlpha = 1

    // Kesik çizgili kenar
    ctx.strokeStyle = ev.color ?? '#888'
    ctx.lineWidth = 2
    ctx.setLineDash([6, 4])
    ctx.beginPath()
    ctx.arc(cx, cy, r, 0, Math.PI * 2)
    ctx.stroke()
    ctx.setLineDash([])
    ctx.restore()

    // İkon
    ctx.save()
    ctx.font = `${Math.max(12, Math.min(24, r * 0.4))}px sans-serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(ev.icon ?? '⚠', cx, cy)
    ctx.restore()

    // Olay adı ve kalan süre
    ctx.save()
    ctx.fillStyle = 'rgba(255,255,255,0.85)'
    ctx.font = '9px sans-serif'
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'
    ctx.fillText(ev.name, cx, cy + r * 0.5 + 4)
    if (ev.remaining_time != null) {
      ctx.fillStyle = 'rgba(200,200,200,0.7)'
      ctx.font = '8px monospace'
      ctx.fillText(`${ev.remaining_time.toFixed(0)}s`, cx, cy + r * 0.5 + 15)
    }
    ctx.restore()
  }

  // Araç olay bölgesinde mi? → halka çiz
  for (const v of vehicles) {
    for (const ev of events) {
      const dist = Math.hypot(v.x - ev.x, v.y - ev.y)
      if (dist < ev.radius_m) {
        const { cx, cy } = toCanvas(v.x, v.y, t)
        ctx.save()
        ctx.strokeStyle = ev.color ?? '#f59e0b'
        ctx.lineWidth = 3
        ctx.setLineDash([4, 3])
        ctx.beginPath()
        ctx.arc(cx, cy, 22, 0, Math.PI * 2)
        ctx.stroke()
        ctx.setLineDash([])
        ctx.restore()
        break
      }
    }
  }
}

function useMineBackground(roadGeometry: any): HTMLImageElement | null {
  const [img, setImg] = useState<HTMLImageElement | null>(null)
  useEffect(() => {
    const scenarioType = roadGeometry?.type ?? ''
    const paths = [
      '/mine-images/mine_intersection.jpg',
      '/mine-images/mine_straight.jpg',
      '/mine-images/mine_road.jpg',
      '/mine-images/mine_scene.jpg',
      '/mine-images/mine1.jpg',
    ]
    const src = scenarioType.includes('straight') ? (paths[1] || paths[0]) : paths[0]
    const image = new Image()
    image.onload = () => setImg(image)
    image.onerror = () => setImg(null)
    image.src = src
  }, [roadGeometry?.type])
  return img
}

export default function SimulationViewer() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const {
    frames, currentFrameIdx, setCurrentFrameIdx,
    simStatus, roadGeometry, optimizedParams,
    selectedScenario, activeEvents, setActiveEvents,
    eventPlacingType, setEventPlacingType,
  } = useStore()
  const mineBackground = useMineBackground(roadGeometry)

  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [canvasSize, setCanvasSize] = useState({ w: 700, h: 500 })

  // Kullanıcı zoom ve pan durumu
  const [userZoom, setUserZoom] = useState(1.0)
  const [userPan, setUserPan] = useState({ x: 0, y: 0 })
  const isDragging = useRef(false)
  const dragStart = useRef({ x: 0, y: 0 })
  const panAtDrag = useRef({ x: 0, y: 0 })

  const playingRef = useRef(false)
  const speedRef = useRef(1)
  playingRef.current = playing
  speedRef.current = speed

  // Container boyutunu izle
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 10 && height > 10) {
          setCanvasSize({ w: Math.round(width), h: Math.round(height) })
        }
      }
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const currentFrame = frames[currentFrameIdx]
  const { w: cw, h: ch } = canvasSize

  // Base auto-scale transform
  const baseTransform = useMemo<Transform>(() => {
    const sampleVehicles: { x: number; y: number }[] = []
    const step = Math.max(1, Math.floor(frames.length / 15))
    for (let i = 0; i < frames.length; i += step) {
      frames[i].vehicles.forEach((v) => sampleVehicles.push({ x: v.x, y: v.y }))
    }
    return computeTransform(roadGeometry, sampleVehicles, cw, ch)
  }, [roadGeometry, frames.length, cw, ch])

  // userZoom/pan değişince transform'u yeniden hesapla
  const transform = useMemo(
    () => applyUserTransform(baseTransform, userZoom, userPan),
    [baseTransform, userZoom, userPan],
  )

  // Senaryo değişince zoom/pan'ı sıfırla
  useEffect(() => {
    setUserZoom(1.0)
    setUserPan({ x: 0, y: 0 })
  }, [roadGeometry])

  // Mouse wheel — zoom (fare konumunu merkez al)
  const handleWheel = useCallback((e: React.WheelEvent<HTMLCanvasElement>) => {
    e.preventDefault()
    const factor = e.deltaY < 0 ? 1.15 : 0.87
    setUserZoom((prev) => {
      const newZoom = Math.min(5.0, Math.max(0.3, prev * factor))
      const rect = canvasRef.current?.getBoundingClientRect()
      if (!rect) return newZoom
      const mx = e.clientX - rect.left
      const my = e.clientY - rect.top
      setUserPan((prevPan) => ({
        x: mx - (mx - prevPan.x) * newZoom / prev,
        y: my - (my - prevPan.y) * newZoom / prev,
      }))
      return newZoom
    })
  }, [])

  // Mouse drag — pan
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    isDragging.current = true
    dragStart.current = { x: e.clientX, y: e.clientY }
    panAtDrag.current = { ...userPan }
  }, [userPan])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDragging.current) return
    const dx = e.clientX - dragStart.current.x
    const dy = e.clientY - dragStart.current.y
    setUserPan({
      x: panAtDrag.current.x + dx,
      y: panAtDrag.current.y + dy,
    })
  }, [])

  const handleMouseUp = useCallback(() => { isDragging.current = false }, [])

  // Olay yerleştirme: canvas tıklama → dünya koordinatına dönüştür
  const handleCanvasClick = useCallback(async (e: React.MouseEvent<HTMLCanvasElement>) => {
    const placingType = useStore.getState().eventPlacingType
    if (!placingType) return
    if (isDragging.current) return

    const rect = canvasRef.current?.getBoundingClientRect()
    if (!rect) return
    const px = e.clientX - rect.left
    const py = e.clientY - rect.top
    const t = transform
    // Canvas → dünya
    const wx = (px - t.offX) / t.scale
    const wy = (t.offY - py) / t.scale

    try {
      await addEvent({ x: wx, y: wy, event_type: placingType })
      const data = await fetchActiveEvents()
      setActiveEvents(data.events ?? [])
    } catch { /* sessiz */ }
    setEventPlacingType(null)
  }, [transform, setActiveEvents, setEventPlacingType])

  // Zoom/pan sıfırla
  const handleReset = useCallback(() => {
    setUserZoom(1.0)
    setUserPan({ x: 0, y: 0 })
  }, [])

  // Otomatik oynatma
  useEffect(() => {
    if (!playing) return
    const ms = Math.round(FRAME_MS_AT_1X / speedRef.current)
    const id = setInterval(() => {
      if (!playingRef.current) return
      const st = useStore.getState()
      const next = st.currentFrameIdx + 1
      if (next >= st.frames.length) {
        setPlaying(false)
        return
      }
      st.setCurrentFrameIdx(next)
    }, ms)
    return () => clearInterval(id)
  }, [playing, speed])

  useEffect(() => {
    if (simStatus === 'completed') setPlaying(false)
  }, [simStatus])

  useEffect(() => {
    if (simStatus === 'running' && frames.length === 1) setPlaying(true)
  }, [simStatus, frames.length])

  // Canvas render
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const t = transform
    const safetyScale = getSafetyScaleFactor(optimizedParams)

    ctx.fillStyle = '#1c1c1c'
    ctx.fillRect(0, 0, cw, ch)

    ctx.strokeStyle = '#242424'
    ctx.lineWidth = 0.5
    for (let x = 0; x < cw; x += 30) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, ch); ctx.stroke()
    }
    for (let y = 0; y < ch; y += 30) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(cw, y); ctx.stroke()
    }

    // Maden arka planı — görsel varsa düşük opaklıkta göster
    if (mineBackground) {
      ctx.globalAlpha = 0.10
      ctx.drawImage(mineBackground, 0, 0, cw, ch)
      ctx.globalAlpha = 1.0
    }

    drawRoads(ctx, roadGeometry, t, ch)

    if (!currentFrame) {
      ctx.fillStyle = '#374151'
      ctx.font = '13px sans-serif'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(tr.viewer.empty, cw / 2, ch / 2)
      return
    }

    const goalReached = currentFrame.completed || false
    drawGoalPolygon(ctx, roadGeometry, t, goalReached)

    // Kavşak merkezi highlight — tehlike bölgesi göstergesi
    for (const zone of roadGeometry?.conflict_zones ?? []) {
      const { cx, cy } = toCanvas(zone.x, zone.y, t)
      const r = (zone.r ?? 10) * t.scale * 0.35
      ctx.beginPath()
      ctx.arc(cx, cy, r, 0, Math.PI * 2)
      ctx.fillStyle = goalReached ? 'rgba(34,197,94,0.25)' : 'rgba(239,68,68,0.20)'
      ctx.fill()
    }

    // Katman 4 — hız bazlı renk gradyanı izleri (son 60 frame)
    const TRAIL_LEN = 60
    const trailStart = Math.max(0, currentFrameIdx - TRAIL_LEN)
    const trailFrames = frames.slice(trailStart, currentFrameIdx + 1)

    // EGO izi
    const egoTrail = trailFrames
      .map((f) => f.vehicles.find((v: any) => v.id === 'ego'))
      .filter(Boolean) as any[]

    for (let i = 1; i < egoTrail.length; i++) {
      const v = egoTrail[i]
      const vp = egoTrail[i - 1]
      const { cx: x1, cy: y1 } = toCanvas(vp.x, vp.y, t)
      const { cx: x2, cy: y2 } = toCanvas(v.x, v.y, t)
      const alpha = 0.15 + 0.55 * (i / egoTrail.length)
      const col = speedToColor(v.speed ?? 0)
      ctx.strokeStyle = col.replace(')', `,${alpha.toFixed(2)})`).replace('rgb', 'rgba').replace('#', '')
      // Hex shortcut
      ctx.globalAlpha = alpha
      ctx.strokeStyle = col
      ctx.lineWidth = 1.5 + Math.min(2.5, (v.speed ?? 0) * 0.3)
      ctx.lineCap = 'round'
      ctx.beginPath()
      ctx.moveTo(x1, y1)
      ctx.lineTo(x2, y2)
      ctx.stroke()
    }
    ctx.globalAlpha = 1

    // Agent izleri
    const agentIds = currentFrame.vehicles
      .filter((v: any) => v.id !== 'ego' && v.vehicle_type !== 'StaticObstacle')
      .map((v: any) => v.id)

    agentIds.forEach((aid: string) => {
      const trail = trailFrames
        .map((f) => f.vehicles.find((v: any) => v.id === aid))
        .filter(Boolean) as any[]
      for (let i = 1; i < trail.length; i++) {
        const v = trail[i]
        const vp = trail[i - 1]
        const { cx: x1, cy: y1 } = toCanvas(vp.x, vp.y, t)
        const { cx: x2, cy: y2 } = toCanvas(v.x, v.y, t)
        const alpha = 0.08 + 0.35 * (i / trail.length)
        ctx.globalAlpha = alpha
        ctx.strokeStyle = speedToColor(v.speed ?? 0)
        ctx.lineWidth = 1.5
        ctx.lineCap = 'round'
        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
        ctx.stroke()
      }
    })
    ctx.globalAlpha = 1

    // Olay bölgelerini çiz (araçlardan önce)
    const eventsNow = useStore.getState().activeEvents
    drawEventZones(ctx, eventsNow, t, currentFrame.time, currentFrame.vehicles)

    // Olay bölgesi uyarı banner'ı
    if (eventsNow.length > 0) {
      const egoV = currentFrame.vehicles.find((v: any) => v.id === 'ego')
      if (egoV) {
        const inZone = eventsNow.find((ev) => Math.hypot(egoV.x - ev.x, egoV.y - ev.y) < ev.radius_m)
        if (inZone) {
          ctx.save()
          ctx.fillStyle = 'rgba(0,0,0,0.7)'
          ctx.fillRect(cw / 2 - 110, 6, 220, 22)
          ctx.fillStyle = inZone.color ?? '#f59e0b'
          ctx.font = 'bold 11px sans-serif'
          ctx.textAlign = 'center'
          ctx.textBaseline = 'middle'
          ctx.fillText(`${inZone.icon} ${inZone.name} — Hız Kısıtlandı`, cw / 2, 17)
          ctx.restore()
        }
      }
    }

    // Çarpışma tespiti (5m eşiği)
    const ego = currentFrame.vehicles.find((v: any) => v.id === 'ego')
    const collisionIds = new Set<string>()
    if (ego) {
      for (const v of currentFrame.vehicles) {
        if (v.id === 'ego') continue
        const d = Math.hypot(v.x - ego.x, v.y - ego.y)
        if (d < 5) { collisionIds.add(v.id); collisionIds.add('ego') }
      }
    }

    let agentN = 1
    for (const v of currentFrame.vehicles) {
      const label = v.id === 'ego' ? 'EGO' : String(agentN++)
      drawVehicle(ctx, v, t, collisionIds.has(v.id), label, safetyScale, cw)
    }

    drawInfoPanel(ctx, currentFrame, currentFrameIdx + 1, frames.length, collisionIds.size > 0, userZoom, cw, ch)

    // Katman 7 — Kuzey oku
    drawNorthArrow(ctx, cw, userZoom)

    // Katman 8 — Eğim göstergesi
    const grade = roadGeometry?.grade
    drawGradeIndicator(ctx, grade, cw, ch)

    // Katman 9 — Çarpışma önleme ring
    if (ego) {
      const nearestDist = currentFrame.vehicles
        .filter((v: any) => v.id !== 'ego')
        .reduce((mn: number, v: any) => Math.min(mn, Math.hypot(v.x - ego.x, v.y - ego.y)), Infinity)
      const phase = nearestDist < 8 ? 'braking' : nearestDist < 20 ? 'warning' : 'none'
      drawCollisionAvoidanceRing(ctx, ego, t, phase)
    }

    // Katman 10 — Alt bilgi şeridi
    const scenarioType = roadGeometry?.type ?? ''
    drawBottomStrip(ctx, currentFrame, selectedScenario ?? '', scenarioType, cw, ch)

  }, [currentFrame, frames, currentFrameIdx, roadGeometry, transform, optimizedParams, cw, ch, userZoom, activeEvents, mineBackground])

  const totalFrames = frames.length

  return (
    <div className="flex flex-col bg-husim-surface rounded-lg overflow-hidden">
      {/* Canvas container */}
      <div
        ref={containerRef}
        style={{ width: '100%', height: '500px', position: 'relative', flexShrink: 0 }}
      >
        <canvas
          ref={canvasRef}
          width={cw}
          height={ch}
          style={{
            width: '100%', height: '100%',
            cursor: eventPlacingType ? 'crosshair' : isDragging.current ? 'grabbing' : 'grab',
            display: 'block',
          }}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onClick={handleCanvasClick}
        />
      </div>

      {/* Kontroller */}
      <div className="flex flex-col gap-1.5 px-3 py-2 bg-slate-800/90 border-t border-slate-700">
        <input
          type="range"
          min={0}
          max={Math.max(0, totalFrames - 1)}
          value={currentFrameIdx}
          onChange={(e) => {
            setPlaying(false)
            setCurrentFrameIdx(Number(e.target.value))
          }}
          className="w-full h-1.5"
          style={{ accentColor: '#f59e0b' }}
        />

        <div className="flex items-center gap-0.5">
          <button
            onClick={() => { setPlaying(false); setCurrentFrameIdx(0) }}
            className="text-slate-400 hover:text-white px-1.5 py-0.5 text-xs"
            title={tr.viewer.controls.rewind}
          >⏮</button>

          <button
            onClick={() => { setPlaying(false); setCurrentFrameIdx(Math.max(0, currentFrameIdx - 1)) }}
            className="text-slate-400 hover:text-white px-1.5 py-0.5 text-xs"
            title={tr.viewer.controls.stepBack}
          >◀</button>

          <button
            onClick={() => setPlaying(!playing)}
            className={`px-2 py-0.5 text-base font-bold ${playing ? 'text-husim-accent' : 'text-slate-300'} hover:text-white`}
            title={playing ? tr.viewer.controls.pause : tr.viewer.controls.play}
          >
            {playing ? '⏸' : '▶'}
          </button>

          <button
            onClick={() => { setPlaying(false); setCurrentFrameIdx(Math.min(totalFrames - 1, currentFrameIdx + 1)) }}
            className="text-slate-400 hover:text-white px-1.5 py-0.5 text-xs"
            title={tr.viewer.controls.stepForward}
          >▶</button>

          <button
            onClick={() => { setPlaying(false); setCurrentFrameIdx(totalFrames - 1) }}
            className="text-slate-400 hover:text-white px-1.5 py-0.5 text-xs"
            title={tr.viewer.controls.end}
          >⏭</button>

          {/* Zoom sıfırla butonu */}
          <button
            onClick={handleReset}
            title="Zoom ve kaydırmayı sıfırla"
            className={`text-xs px-1.5 py-0.5 rounded transition-colors ml-1 ${
              userZoom !== 1.0 || userPan.x !== 0 || userPan.y !== 0
                ? 'bg-husim-accent text-husim-bg font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            ⊡
          </button>

          <div className="flex-1" />

          <span className="text-xs text-slate-500 mr-1">{tr.viewer.controls.speed}:</span>
          {SPEED_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => { setSpeed(s) }}
              className={`text-xs px-1.5 py-0.5 rounded transition-colors ${
                speed === s
                  ? 'bg-husim-accent text-husim-bg font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {s}x
            </button>
          ))}

          <span className="text-xs text-slate-500 ml-2 min-w-[64px] text-right tabular-nums">
            {currentFrameIdx + 1}/{totalFrames}
          </span>
        </div>
      </div>
    </div>
  )
}
