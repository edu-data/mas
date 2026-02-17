import { useState, useEffect } from 'react'

export default function AgentCard({ agent, isActive }) {
    const [pulse, setPulse] = useState(false)

    useEffect(() => {
        if (agent.status === 'running') {
            setPulse(true)
        } else {
            setPulse(false)
        }
    }, [agent.status])

    const statusColor = {
        idle: '#6b7280',
        running: '#3b82f6',
        done: '#10b981',
        error: '#ef4444',
        skipped: '#9ca3af',
    }

    const statusLabel = {
        idle: '대기 중',
        running: '실행 중',
        done: '완료',
        error: '오류',
        skipped: '건너뜀',
    }

    const color = statusColor[agent.status] || '#6b7280'
    const label = statusLabel[agent.status] || agent.status

    return (
        <div className={`agent-card ${agent.status} ${pulse ? 'pulse' : ''} ${isActive ? 'active' : ''}`}>
            <div className="agent-card-header">
                <span className="agent-icon">{agent.icon}</span>
                <div className="agent-info">
                    <h4 className="agent-name">{agent.name}</h4>
                    <p className="agent-role">{agent.role}</p>
                </div>
                <div className="agent-status-badge" style={{ backgroundColor: color }}>
                    {label}
                </div>
            </div>

            {agent.status === 'running' && (
                <div className="agent-progress-bar">
                    <div
                        className="agent-progress-fill"
                        style={{ width: `${agent.progress || 50}%` }}
                    />
                </div>
            )}

            {agent.status === 'done' && agent.elapsed_seconds > 0 && (
                <div className="agent-result">
                    <span className="result-time">⏱️ {agent.elapsed_seconds.toFixed(1)}s</span>
                    {agent.has_result && <span className="result-check">✅ 결과 생성</span>}
                </div>
            )}

            {agent.status === 'error' && (
                <div className="agent-error">
                    <span>⚠️ {agent.error || '오류 발생'}</span>
                </div>
            )}

            {agent.dependencies && agent.dependencies.length > 0 && (
                <div className="agent-deps">
                    <span className="deps-label">의존:</span>
                    {agent.dependencies.map(dep => (
                        <span key={dep} className="dep-tag">{dep}</span>
                    ))}
                </div>
            )}
        </div>
    )
}
