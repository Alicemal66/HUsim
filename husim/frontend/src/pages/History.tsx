import { useQuery } from '@tanstack/react-query'
import { tr } from '../tr'
import { fetchHistory } from '../api'

const WEATHER_TR: Record<string, string> = {
  clear: 'Açık', cloudy: 'Bulutlu', rainy: 'Yağmurlu',
  snowy: 'Karlı', foggy: 'Sisli', stormy: 'Fırtınalı',
}

export default function History() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['history'],
    queryFn: fetchHistory,
    refetchInterval: 10000,
  })

  const history: any[] = data?.gecmis ?? []

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400 text-sm">
        Geçmiş yükleniyor...
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-64 text-husim-danger text-sm">
        Geçmiş yüklenemedi — sunucu bağlantısı kontrol edin.
      </div>
    )
  }

  return (
    <div className="p-4 max-w-5xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-husim-accent">{tr.history.title}</h1>
        <span className="text-xs text-slate-400">{history.length} kayıt</span>
      </div>

      {history.length === 0 ? (
        <div className="text-center py-16 text-slate-500">
          <p className="text-4xl mb-3">📋</p>
          <p>{tr.history.noHistory}</p>
        </div>
      ) : (
        <div className="bg-husim-surface rounded-lg overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-husim-primary text-slate-300 text-xs">
                <th className="text-left p-2">{tr.history.date}</th>
                <th className="text-left p-2">{tr.history.scenario}</th>
                <th className="text-left p-2">{tr.history.weather}</th>
                <th className="text-left p-2">Algoritma</th>
                <th className="text-left p-2">{tr.history.result}</th>
                <th className="text-left p-2">{tr.history.duration}</th>
                <th className="text-left p-2">Risk</th>
                <th className="text-left p-2">Çarpışma</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item: any) => {
                const completed = item.metrics?.task_completed
                const date = new Date(item.created_at)
                const weatherType = item.weather?.weather_type ?? '—'

                return (
                  <tr key={item.id} className="border-t border-slate-700 hover:bg-slate-700/20 transition-colors">
                    <td className="p-2 text-xs text-slate-400">
                      {date.toLocaleDateString('tr-TR')} {date.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="p-2 text-husim-text font-medium text-xs max-w-[140px] truncate">
                      {item.scenario_id}
                    </td>
                    <td className="p-2 text-xs text-slate-400">
                      {WEATHER_TR[weatherType] ?? weatherType}
                    </td>
                    <td className="p-2 text-xs text-husim-accent">{item.algorithm}</td>
                    <td className="p-2">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                        item.status === 'completed'
                          ? completed
                            ? 'bg-husim-success/20 text-husim-success'
                            : 'bg-orange-500/20 text-orange-300'
                          : item.status === 'failed'
                          ? 'bg-husim-danger/20 text-husim-danger'
                          : 'bg-slate-600 text-slate-300'
                      }`}>
                        {item.status === 'completed'
                          ? completed ? tr.history.success : 'Tamamlanmadı'
                          : item.status === 'failed' ? tr.history.failed
                          : item.status === 'stopped' ? 'Durduruldu'
                          : item.status}
                      </span>
                    </td>
                    <td className="p-2 text-xs text-slate-400">
                      {item.metrics?.completion_time != null
                        ? `${item.metrics.completion_time.toFixed(1)}s`
                        : '—'}
                    </td>
                    <td className="p-2 text-xs">
                      {item.metrics?.risk_score != null ? (
                        <span className={
                          item.metrics.risk_score > 60 ? 'text-husim-danger' :
                          item.metrics.risk_score > 30 ? 'text-yellow-400' :
                          'text-husim-success'
                        }>
                          {item.metrics.risk_score}/100
                        </span>
                      ) : '—'}
                    </td>
                    <td className="p-2 text-xs text-slate-300">
                      {item.metrics?.collision_count ?? '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
