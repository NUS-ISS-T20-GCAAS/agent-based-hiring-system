"""
In-memory shared storage for artifacts
Thread-safe append-only storage
"""

from typing import Dict, List
from threading import Lock


class SharedMemory:
    """
    Thread-safe in-memory storage for agent artifacts
    
    This is a simple implementation for development/testing.
    In production, replace with Redis or PostgreSQL.
    """
    
    def __init__(self):
        self._store: List[Dict] = []
        self._lock = Lock()

    def append(self, artifact: Dict) -> None:
        """
        Append an artifact to storage (thread-safe)
        
        Args:
            artifact: Artifact dictionary with all required fields
        """
        with self._lock:
            self._store.append(artifact)

    def get_by_entity(self, entity_id: str) -> List[Dict]:
        """
        Get all artifacts for a specific entity
        
        Args:
            entity_id: The entity (candidate) ID
            
        Returns:
            List of artifacts for this entity
        """
        with self._lock:
            return [a for a in self._store if a["entity_id"] == entity_id]

    def get_by_correlation(self, correlation_id: str) -> List[Dict]:
        """
        Get all artifacts for a specific correlation ID
        
        Args:
            correlation_id: The correlation ID (e.g., job application ID)
            
        Returns:
            List of artifacts for this correlation
        """
        with self._lock:
            return [a for a in self._store if a.get("correlation_id") == correlation_id]

    def all(self) -> List[Dict]:
        """
        Get all artifacts
        
        Returns:
            List of all artifacts in storage
        """
        with self._lock:
            return list(self._store)
    
    def clear(self) -> None:
        """
        Clear all artifacts (for testing)
        """
        with self._lock:
            self._store.clear()
    
    def count(self) -> int:
        """
        Get count of artifacts
        
        Returns:
            Number of artifacts in storage
        """
        with self._lock:
            return len(self._store)