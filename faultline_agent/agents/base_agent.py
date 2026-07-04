"""
Faultline Base Agent
Abstract base class for all agents in the multi-agent system.
Provides common interface, reasoning loop, and tool execution framework.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AgentMessage(BaseModel):
    """Message passed between agents."""
    sender: str
    receiver: str
    content: Any
    message_type: str = "data"  # data, request, response, error
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    """Result of an agent's execution."""
    agent_name: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    reasoning: list[str] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """
    Abstract base agent with reasoning loop and tool execution.
    All Faultline agents inherit from this class.
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.reasoning_log: list[str] = []
        self.message_inbox: list[AgentMessage] = []
        self.message_outbox: list[AgentMessage] = []
        self._tools: dict[str, callable] = {}
        self._is_active = False
        self._execution_count = 0
    
    @abstractmethod
    def execute(self, context: dict[str, Any]) -> AgentResult:
        """
        Main execution method. Each agent implements its specific logic.
        Context contains shared state and data from other agents.
        """
        pass
    
    def reason(self, observation: str) -> str:
        """
        Reasoning step - agent thinks about what to do next.
        Returns the reasoning conclusion.
        """
        reasoning = f"[{self.name}] Observing: {observation}"
        self.reasoning_log.append(reasoning)
        return reasoning
    
    def use_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a registered tool."""
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not registered for agent '{self.name}'")
        
        self.reason(f"Using tool: {tool_name} with args: {kwargs}")
        result = self._tools[tool_name](**kwargs)
        self.reason(f"Tool result: {type(result).__name__}")
        return result
    
    def register_tool(self, name: str, func: callable) -> None:
        """Register a tool for this agent to use."""
        self._tools[name] = func
    
    def send_message(self, receiver: str, content: Any, msg_type: str = "data") -> None:
        """Send a message to another agent."""
        msg = AgentMessage(
            sender=self.name,
            receiver=receiver,
            content=content,
            message_type=msg_type,
        )
        self.message_outbox.append(msg)
    
    def receive_message(self, message: AgentMessage) -> None:
        """Receive a message from another agent."""
        self.message_inbox.append(message)
    
    def get_messages(self, msg_type: Optional[str] = None) -> list[AgentMessage]:
        """Get messages from inbox, optionally filtered by type."""
        if msg_type:
            return [m for m in self.message_inbox if m.message_type == msg_type]
        return self.message_inbox
    
    def clear_messages(self) -> None:
        """Clear message inbox and outbox."""
        self.message_inbox.clear()
        self.message_outbox.clear()
    
    def _build_result(
        self,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        start_time: Optional[datetime] = None,
    ) -> AgentResult:
        """Build a standardized agent result."""
        exec_time = 0.0
        if start_time:
            exec_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return AgentResult(
            agent_name=self.name,
            success=success,
            data=data,
            error=error,
            reasoning=list(self.reasoning_log[-10:]),  # Last 10 reasoning steps
            execution_time_ms=exec_time,
        )
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name='{self.name}')>"