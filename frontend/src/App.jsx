import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Portfolio from './pages/Portfolio'
import AnalysisResult from './pages/AnalysisResult'
import './App.css'

function App() {
    return (
        <Router>
            <div className="app">
                <header className="app-header">
                    <div className="logo">
                        <span className="logo-icon">🎓</span>
                        <h1>GAIM Lab</h1>
                    </div>
                    <nav className="nav">
                        <a href="/">대시보드</a>
                        <a href="/upload">수업 분석</a>
                        <a href="/portfolio">포트폴리오</a>
                    </nav>
                </header>
                <main className="app-main">
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/upload" element={<Upload />} />
                        <Route path="/portfolio" element={<Portfolio />} />
                        <Route path="/analysis/:analysisId" element={<AnalysisResult />} />
                    </Routes>
                </main>
                <footer className="app-footer">
                    <p>© 2026 GINUE AI Microteaching Lab | 경인교육대학교</p>
                </footer>
            </div>
        </Router>
    )
}

export default App
