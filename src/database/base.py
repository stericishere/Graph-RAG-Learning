"""
Abstract Graph Database Interface

This module defines the abstract base class that all graph database adapters must implement.
It ensures consistent API across different backends (Neo4j, NetworkX, etc.).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import uuid


class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass


class NodeNotFoundError(Exception):
    """Raised when a requested node is not found."""
    pass


class RelationshipNotFoundError(Exception):
    """Raised when a requested relationship is not found."""
    pass


class ValidationError(Exception):
    """Raised when input data fails validation."""
    pass


class GraphDatabase(ABC):
    """
    Abstract base class for graph database adapters.
    
    This interface defines the contract that all graph database implementations
    must follow to ensure consistent behavior across different backends.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the database adapter with configuration.
        
        Args:
            config: Database configuration dictionary
        """
        self.config = config
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if the database is connected."""
        return self._connected
    
    # Connection Management
    @abstractmethod
    async def connect(self) -> None:
        """
        Establish connection to the database.
        
        Raises:
            DatabaseConnectionError: If connection fails
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close the database connection.
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the database is healthy and responsive.
        
        Returns:
            bool: True if database is healthy, False otherwise
        """
        pass
    
    # Node Operations
    @abstractmethod
    async def create_node(
        self, 
        label: str, 
        properties: Dict[str, Any], 
        node_id: Optional[str] = None
    ) -> str:
        """
        Create a new node in the graph.
        
        Args:
            label: Node label/type (e.g., "Rule", "Learnt")
            properties: Node properties as key-value pairs
            node_id: Optional custom node ID (UUID will be generated if not provided)
        
        Returns:
            str: The ID of the created node
            
        Raises:
            ValidationError: If properties are invalid
            DatabaseConnectionError: If database is not connected
        """
        pass
    
    @abstractmethod
    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a node by its ID.
        
        Args:
            node_id: The ID of the node to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Node data including properties and metadata,
                                    None if node not found
        """
        pass
    
    @abstractmethod
    async def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """
        Update properties of an existing node.
        
        Args:
            node_id: The ID of the node to update
            properties: New/updated properties
            
        Returns:
            bool: True if update successful, False if node not found
            
        Raises:
            ValidationError: If properties are invalid
        """
        pass
    
    @abstractmethod
    async def delete_node(self, node_id: str) -> bool:
        """
        Delete a node from the graph.
        
        Args:
            node_id: The ID of the node to delete
            
        Returns:
            bool: True if deletion successful, False if node not found
            
        Note:
            This should also delete all relationships connected to the node
        """
        pass
    
    @abstractmethod
    async def get_nodes_by_label(
        self, 
        label: str, 
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all nodes with a specific label.
        
        Args:
            label: The label to filter by
            filters: Optional property filters as key-value pairs
            limit: Optional limit on number of results
            
        Returns:
            List[Dict[str, Any]]: List of matching nodes
        """
        pass
    
    # Relationship Operations
    @abstractmethod
    async def create_relationship(
        self, 
        start_node_id: str, 
        end_node_id: str, 
        relationship_type: str, 
        properties: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a relationship between two nodes.
        
        Args:
            start_node_id: ID of the source node
            end_node_id: ID of the target node
            relationship_type: Type of relationship (e.g., "IMPROVES_RULE")
            properties: Optional relationship properties
            
        Returns:
            str: The ID of the created relationship
            
        Raises:
            NodeNotFoundError: If either node doesn't exist
            ValidationError: If relationship data is invalid
        """
        pass
    
    @abstractmethod
    async def get_relationships(
        self, 
        node_id: str, 
        relationship_type: Optional[str] = None,
        direction: str = "both"
    ) -> List[Dict[str, Any]]:
        """
        Get relationships for a specific node.
        
        Args:
            node_id: The node ID to get relationships for
            relationship_type: Optional filter by relationship type
            direction: "incoming", "outgoing", or "both"
            
        Returns:
            List[Dict[str, Any]]: List of relationships with their properties
        """
        pass
    
    @abstractmethod
    async def delete_relationship(self, relationship_id: str) -> bool:
        """
        Delete a relationship.
        
        Args:
            relationship_id: The ID of the relationship to delete
            
        Returns:
            bool: True if deletion successful, False if relationship not found
        """
        pass
    
    # Utility Methods
    @abstractmethod
    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a raw query against the database.
        
        Args:
            query: The query string (backend-specific)
            parameters: Optional query parameters
            
        Returns:
            Any: Query results (backend-specific format)
            
        Note:
            This method is backend-specific and should be used sparingly
        """
        pass
    
    @abstractmethod
    async def clear_all_data(self) -> None:
        """
        Clear all data from the database.
        
        Warning:
            This operation is irreversible. Use with caution.
        """
        pass
    
    # Helper Methods (with default implementations)
    def generate_node_id(self) -> str:
        """Generate a unique node ID."""
        return str(uuid.uuid4())
    
    def validate_node_properties(self, properties: Dict[str, Any]) -> None:
        """
        Validate node properties.
        
        Args:
            properties: Properties to validate
            
        Raises:
            ValidationError: If properties are invalid
        """
        if not isinstance(properties, dict):
            raise ValidationError("Properties must be a dictionary")
        
        # Check for reserved keys
        reserved_keys = {"id", "_id", "node_id"}
        for key in reserved_keys:
            if key in properties:
                raise ValidationError(f"Property key '{key}' is reserved")
    
    def validate_relationship_type(self, relationship_type: str) -> None:
        """
        Validate relationship type.
        
        Args:
            relationship_type: Relationship type to validate
            
        Raises:
            ValidationError: If relationship type is invalid
        """
        if not isinstance(relationship_type, str) or not relationship_type.strip():
            raise ValidationError("Relationship type must be a non-empty string")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect() 