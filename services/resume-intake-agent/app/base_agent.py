from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from app.shared_memory import SharedMemory
from app.logger import get_logger


class BaseAgent(ABC):
    """
    Base class for all agents in the system.

    This class enforces:
    - standardized execution flow
    - structured logging
    - append-only shared memory writes
    - explainability guarantees
    """

    def __init__(
        self,
        agent_type: str,
        shared_memory: SharedMemory,
    ):
        self.agent_id = str(uuid.uuid4())
        self.agent_type = agent_type
        self.shared_memory = shared_memory
        self.logger = get_logger(agent_type)

    def run(self, *, entity_id: str, correlation_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entry point called by the Coordinator.
        Handles logging, error capture, and memory persistence.
        """

        start_time = datetime.now(timezone.utc)

        self.logger.info(
            "agent_started",
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            entity_id=entity_id,
            correlation_id=correlation_id,
            input=input_data,
        )

        try:
            result = self.handle(input_data)

            artifact = {
                "artifact_id": str(uuid.uuid4()),
                "entity_id": entity_id,
                "agent_id": self.agent_id,
                "agent_type": self.agent_type,
                "artifact_type": self.artifact_type(),
                "payload": result.get("payload"),
                "confidence": result.get("confidence"),
                "explanation": result.get("explanation"),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "version": 1,
                "correlation_id": correlation_id,
            }

            self.shared_memory.append(artifact)

            self.logger.info(
                "agent_completed",
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                entity_id=entity_id,
                duration_ms=(datetime.now(timezone.utc) - start_time).total_seconds()
                * 1000,
                artifact_id=artifact["artifact_id"],
            )

            return artifact

        except Exception as exc:
            self.logger.error(
                "agent_failed",
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                entity_id=entity_id,
                error=str(exc),
            )
            raise

    @abstractmethod
    def handle(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core agent logic.

        Must return:
        {
            "payload": Any,
            "confidence": float,
            "explanation": str
        }
        """
        pass

    @abstractmethod
    def artifact_type(self) -> str:
        """
        Returns the artifact type written to shared memory.
        Example: 'resume_parsed', 'qualification_screened'
        """
        pass
