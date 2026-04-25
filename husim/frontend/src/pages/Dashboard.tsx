import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchHealth } from '../api'
import { useStore } from '../store'
import WeatherPanel from '../components/WeatherPanel'
import LoadPanel from '../components/LoadPanel'
import SimulationViewer from '../components/SimulationViewer'
import MetricsPanel from '../components/MetricsPanel'
import AlertPanel from '../components/AlertPanel'
import ScenarioSelector from '../components/ScenarioSelector'
import ScenarioGenerator from '../components/ScenarioGenerator'
import CompareMode from '../components/CompareMode'
import ReportPanel from '../components/ReportPanel'
import FleetPanel from '../components/FleetPanel'
import EventControlPanel from '../components/EventControlPanel'

type CenterTab = 'viewer' | 'compare' | 'generate'

export default function Dashboard() {
  const setBackendConnected = useStore((s) => s.setBackendConnected)
  const presentationMode = useStore((s) => s.presentationMode)
  const [centerTab, setCenterTab] = useState<CenterTab>('viewer')

  const { data, isSuccess, isError } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 5000,
    retry: false,
  })

  useEffect(() => {
    if (isSuccess) setBackendConnected(true)
    if (isError) setBackendConnected(false)
  }, [isSuccess, isError, setBackendConnected])

  const backendConnected = useStore((s) => s.backendConnected)

  const tabClass = (t: CenterTab) =>
    `text-xs px-2.5 py-1 rounded-t transition-colors ${
      centerTab === t
        ? 'bg-husim-surface text-husim-accent font-bold'
        : 'bg-slate-800/50 text-slate-400 hover:text-slate-200'
    }`

  return (
    <div className="flex flex-col h-full">
      {!backendConnected && (
        <div className="bg-husim-danger/20 border-b border-husim-danger/40 text-husim-danger text-xs text-center py-1.5 animate-pulse">
          ⚠️ Sunucuya bağlanılamıyor — otomatik yeniden bağlanma deneniyor...
        </div>
      )}

      {data?.demo_modu && (
        <div className="bg-yellow-900/20 border-b border-yellow-700/20 text-yellow-600/70 text-[10px] text-right px-3 py-0.5">
          Demo Modu
        </div>
      )}

      {/* Sunum Modu alt notu */}
      {presentationMode && (
        <div className="bg-husim-accent/10 border-b border-husim-accent/30 text-husim-accent text-xs text-center py-1 font-bold tracking-wide">
          HÜsim — MineSim + Levin Telematics + ORCA
        </div>
      )}

      {/* Ana Grid — Normal veya Sunum Modu */}
      {presentationMode ? (
        <div className="flex-1 grid grid-cols-[1fr_300px] gap-2 p-2 min-h-0 overflow-hidden">
          {/* Orta: Büyük simülasyon */}
          <div className="flex flex-col gap-2 min-h-0">
            <SimulationViewer />
            <ScenarioSelector />
          </div>
          {/* Sağ: Büyük metrikler */}
          <div className="flex flex-col gap-2 min-h-0 overflow-hidden">
            <MetricsPanel />
            <AlertPanel />
          </div>
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-[272px_1fr_256px] gap-2 p-2 min-h-0 overflow-hidden">
          {/* Sol Sütun: Hava + Yük + Rapor */}
          <div className="flex flex-col gap-2 min-h-0 overflow-hidden">
            <div className="flex-[2] min-h-0 overflow-y-auto">
              <WeatherPanel />
            </div>
            <div className="flex-shrink-0">
              <LoadPanel />
            </div>
            <ReportPanel />
          </div>

          {/* Orta Sütun: Sekmeli */}
          <div className="flex flex-col gap-0 min-h-0">
            {/* Sekme başlıkları */}
            <div className="flex gap-0.5 px-1 pt-1">
              <button className={tabClass('viewer')} onClick={() => setCenterTab('viewer')}>
                Simülasyon
              </button>
              <button className={tabClass('compare')} onClick={() => setCenterTab('compare')}>
                Karşılaştırma
              </button>
              <button className={tabClass('generate')} onClick={() => setCenterTab('generate')}>
                Senaryo Üret
              </button>
            </div>

            {/* Sekme içerikleri */}
            <div className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-2">
              {centerTab === 'viewer' && (
                <>
                  <SimulationViewer />
                  <ScenarioSelector />
                </>
              )}
              {centerTab === 'compare' && (
                <>
                  <ScenarioSelector />
                  <CompareMode />
                </>
              )}
              {centerTab === 'generate' && (
                <>
                  <ScenarioGenerator />
                </>
              )}
            </div>
          </div>

          {/* Sağ Sütun: Metrikler + Filo + Olaylar + Uyarılar */}
          <div className="flex flex-col gap-2 min-h-0 overflow-hidden">
            <div className="flex-shrink-0">
              <MetricsPanel />
            </div>
            <div className="flex-shrink-0">
              <FleetPanel />
            </div>
            <div className="flex-shrink-0">
              <EventControlPanel />
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto">
              <AlertPanel />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
