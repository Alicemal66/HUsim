import Header from './components/Header'
import Dashboard from './pages/Dashboard'
import Scenarios from './pages/Scenarios'
import History from './pages/History'
import { useStore } from './store'

export default function App() {
  const activePage = useStore((s) => s.activePage)

  return (
    <div className="flex flex-col h-screen bg-husim-bg text-husim-text overflow-hidden">
      <Header />
      <main className="flex-1 overflow-auto">
        {activePage === 'dashboard' && <Dashboard />}
        {activePage === 'scenarios' && <Scenarios />}
        {activePage === 'history' && <History />}
      </main>
    </div>
  )
}
