import { tr } from '../tr'
import { useStore } from '../store'

export default function Header() {
  const { backendConnected, activePage, setActivePage, presentationMode, setPresentationMode } = useStore()

  const navItems = [
    { key: 'dashboard' as const, label: tr.nav.dashboard },
    { key: 'scenarios' as const, label: tr.nav.scenarios },
    { key: 'history' as const, label: tr.nav.history },
  ]

  return (
    <header className="flex items-center justify-between px-4 py-2 bg-husim-primary border-b border-slate-700 select-none">
      <div className="flex items-center gap-3">
        <span className="text-2xl">⛏️</span>
        <div>
          <span className="font-bold text-lg text-white tracking-wide">{tr.app.name}</span>
          <span className="ml-2 text-xs text-slate-400 hidden sm:inline">{tr.app.subtitle}</span>
        </div>
        <span className="text-xs text-slate-500 ml-1">{tr.app.version}</span>
      </div>

      <nav className="flex gap-1">
        {navItems.map((item) => (
          <button
            key={item.key}
            onClick={() => setActivePage(item.key)}
            className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
              activePage === item.key
                ? 'bg-husim-accent text-husim-bg'
                : 'text-slate-300 hover:text-white hover:bg-slate-700'
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="flex items-center gap-3 text-sm">
        <button
          onClick={() => setPresentationMode(!presentationMode)}
          className={`px-3 py-1.5 rounded text-sm font-bold transition-all border ${
            presentationMode
              ? 'bg-husim-accent text-husim-bg border-husim-accent'
              : 'border-slate-600 text-slate-300 hover:border-husim-accent hover:text-husim-accent'
          }`}
          title={presentationMode ? tr.presentationMode.exit : tr.presentationMode.enter}
        >
          {presentationMode ? '✕ ' : '🎯 '}{presentationMode ? tr.presentationMode.exit : tr.presentationMode.title}
        </button>

        <span
          className={`inline-block w-2 h-2 rounded-full ${
            backendConnected ? 'bg-husim-success' : 'bg-husim-danger'
          }`}
        />
        <span className={backendConnected ? 'text-husim-success' : 'text-husim-danger'}>
          {backendConnected ? tr.status.connected : tr.status.disconnected}
        </span>
      </div>
    </header>
  )
}
