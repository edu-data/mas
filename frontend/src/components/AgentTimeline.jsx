export default function AgentTimeline({ agents, phases }) {
    const defaultPhases = phases || [
        { phase: 'extract', label: '추출', agents: ['extractor'] },
        { phase: 'analyze', label: '분석', agents: ['vision', 'content', 'stt', 'vibe'] },
        { phase: 'evaluate', label: '평가', agents: ['pedagogy'] },
        { phase: 'feedback', label: '피드백', agents: ['feedback'] },
        { phase: 'synthesize', label: '종합', agents: ['master'] },
    ]

    const getPhaseStatus = (phase) => {
        const phaseAgents = phase.agents.map(name => agents[name]).filter(Boolean)
        if (phaseAgents.every(a => a.status === 'done')) return 'done'
        if (phaseAgents.some(a => a.status === 'running')) return 'running'
        if (phaseAgents.some(a => a.status === 'error')) return 'error'
        return 'idle'
    }

    const statusColors = {
        idle: '#374151',
        running: '#3b82f6',
        done: '#10b981',
        error: '#ef4444',
    }

    return (
        <div className="agent-timeline">
            <div className="timeline-track">
                {defaultPhases.map((phase, index) => {
                    const status = getPhaseStatus(phase)
                    const color = statusColors[status]
                    return (
                        <div key={phase.phase} className={`timeline-node ${status}`}>
                            {index > 0 && (
                                <div
                                    className={`timeline-connector ${status === 'idle' ? '' : 'active'}`}
                                    style={{ backgroundColor: status !== 'idle' ? color : '#1f2937' }}
                                />
                            )}
                            <div className="timeline-dot" style={{ borderColor: color, backgroundColor: status === 'done' ? color : 'transparent' }}>
                                {status === 'done' && '✓'}
                                {status === 'running' && <span className="dot-pulse" />}
                            </div>
                            <div className="timeline-label">
                                <span className="phase-name">{phase.label}</span>
                                <div className="phase-agents">
                                    {phase.agents.map(name => {
                                        const agent = agents[name]
                                        return agent ? (
                                            <span key={name} className={`mini-agent ${agent.status}`} title={agent.role}>
                                                {agent.icon}
                                            </span>
                                        ) : null
                                    })}
                                </div>
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
