"""
🔀 Agent Message Bus - 에이전트 간 비동기 메시지 버스
이벤트 기반 에이전트 통신 및 상태 관리
"""

from datetime import datetime
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass, field
import threading


@dataclass
class AgentEvent:
    """에이전트 이벤트"""
    event_type: str
    agent_name: str
    timestamp: str
    data: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "event_type": self.event_type,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp,
            "data": self.data,
        }


class AgentMessageBus:
    """
    🔀 에이전트 간 비동기 메시지 버스 (싱글턴)

    기능:
    - publish/subscribe 패턴으로 에이전트 이벤트 관리
    - 이벤트 히스토리 저장 (인메모리)
    - 파이프라인별 이벤트 필터링
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[AgentEvent] = []
        self._pipeline_events: Dict[str, List[AgentEvent]] = {}
        self._max_history = 1000
        self._initialized = True

    def publish(self, agent_name: str, event_type: str, data: Dict = None, pipeline_id: str = None):
        """이벤트 발행"""
        event = AgentEvent(
            event_type=event_type,
            agent_name=agent_name,
            timestamp=datetime.now().isoformat(),
            data=data or {},
        )

        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

        if pipeline_id:
            if pipeline_id not in self._pipeline_events:
                self._pipeline_events[pipeline_id] = []
            self._pipeline_events[pipeline_id].append(event)

        # 구독자에게 전달
        for cb in self._subscribers.get(event_type, []):
            try:
                cb(event)
            except Exception:
                pass

        # 와일드카드 구독
        for cb in self._subscribers.get("*", []):
            try:
                cb(event)
            except Exception:
                pass

    def subscribe(self, event_type: str, callback: Callable):
        """이벤트 구독"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """구독 해제"""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb != callback
            ]

    def get_history(self, limit: int = 50, agent_name: str = None, event_type: str = None) -> List[Dict]:
        """이벤트 히스토리 조회"""
        events = self._event_history
        if agent_name:
            events = [e for e in events if e.agent_name == agent_name]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [e.to_dict() for e in events[-limit:]]

    def get_pipeline_events(self, pipeline_id: str) -> List[Dict]:
        """특정 파이프라인의 이벤트 조회"""
        events = self._pipeline_events.get(pipeline_id, [])
        return [e.to_dict() for e in events]

    def clear_history(self):
        """히스토리 초기화"""
        self._event_history.clear()
        self._pipeline_events.clear()


# 글로벌 메시지 버스 인스턴스
def get_message_bus() -> AgentMessageBus:
    return AgentMessageBus()
