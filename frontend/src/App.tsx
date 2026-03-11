import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/layout/Layout'
import PlayPage from './pages/PlayPage'
import AnalyzePage from './pages/AnalyzePage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/play" element={<PlayPage />} />
        <Route path="/analyze" element={<AnalyzePage />} />
        <Route path="/" element={<Navigate to="/play" replace />} />
      </Route>
    </Routes>
  )
}
