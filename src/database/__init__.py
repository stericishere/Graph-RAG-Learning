"""
Database adapters package for dual Neo4j and NetworkX support.
"""

from typing import Dict, Any

from .base import (
    GraphDatabase,
    DatabaseConnectionError,
    NodeNotFoundError,
    RelationshipNotFoundError,
    ValidationError
)
from .neo4j_adapter import Neo4jAdapter
from .networkx_adapter import NetworkXAdapter


def create_database(db_type: str, config: Dict[str, Any]) -> GraphDatabase:
    """
    Factory function to create database adapter instances.
    
    Args:
        db_type: Database type ("neo4j" or "networkx")
        config: Configuration dictionary for the adapter
        
    Returns:
        GraphDatabase: Initialized database adapter instance
        
    Raises:
        ValueError: If unsupported database type is specified
        ValidationError: If configuration is invalid
    """
    db_type_lower = db_type.lower().strip()
    
    if db_type_lower == "neo4j":
        return Neo4jAdapter(config)
    elif db_type_lower == "networkx":
        return NetworkXAdapter(config)
    else:
        raise ValueError(f"Unsupported database type: {db_type}. Supported types: 'neo4j', 'networkx'")


# Export all public classes and functions
__all__ = [
    # Base classes and exceptions
    "GraphDatabase",
    "DatabaseConnectionError", 
    "NodeNotFoundError",
    "RelationshipNotFoundError",
    "ValidationError",
    # Adapter implementations
    "Neo4jAdapter",
    "NetworkXAdapter",
    # Factory function
    "create_database"
] 