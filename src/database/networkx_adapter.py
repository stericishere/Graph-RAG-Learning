"""
NetworkX Database Adapter

This module implements the GraphDatabase interface for NetworkX using
in-memory graph operations with JSON file persistence.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import networkx as nx
from networkx.readwrite import json_graph

from .base import (
    GraphDatabase,
    DatabaseConnectionError,
    NodeNotFoundError,
    RelationshipNotFoundError,
    ValidationError
)

logger = logging.getLogger(__name__)


class NetworkXAdapter(GraphDatabase):
    """
    NetworkX implementation of the GraphDatabase interface.
    
    This adapter uses NetworkX for in-memory graph operations with
    JSON file persistence for Rules and Learnt nodes.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the NetworkX adapter.
        
        Args:
            config: Configuration dictionary containing:
                - data_file: Path to JSON file for persistence
                - auto_save: Whether to auto-save after operations (default: True)
                - backup_count: Number of backup files to keep (default: 3)
        """
        super().__init__(config)
        self.graph: nx.Graph = nx.Graph()
        self.data_file = Path(config.get("data_file", "data/graph_data.json"))
        self.auto_save = config.get("auto_save", True)
        self.backup_count = config.get("backup_count", 3)
        
        # Ensure data directory exists
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Node and relationship tracking
        self._nodes_by_label: Dict[str, set] = {}
        self._relationship_counter = 0
    
    async def connect(self) -> None:
        """
        Initialize the NetworkX graph and load data from file.
        
        Raises:
            DatabaseConnectionError: If file loading fails
        """
        try:
            await self._load_graph()
            self._connected = True
            logger.info(f"Successfully connected to NetworkX database: {self.data_file}")
            
        except Exception as e:
            logger.error(f"Failed to connect to NetworkX database: {e}")
            raise DatabaseConnectionError(f"NetworkX connection failed: {e}")
    
    async def disconnect(self) -> None:
        """
        Save the graph and close the connection.
        """
        if self._connected:
            await self._save_graph()
            self._connected = False
            logger.info("Disconnected from NetworkX database")
    
    async def health_check(self) -> bool:
        """
        Check if the database is healthy.
        
        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            # Simple check: verify graph is accessible
            node_count = self.graph.number_of_nodes()
            edge_count = self.graph.number_of_edges()
            logger.debug(f"Health check: {node_count} nodes, {edge_count} edges")
            return self._connected
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    async def create_node(
        self, 
        label: str, 
        properties: Dict[str, Any], 
        node_id: Optional[str] = None
    ) -> str:
        """
        Create a new node in the NetworkX graph.
        
        Args:
            label: Node label (e.g., "Rule", "Learnt")
            properties: Node properties
            node_id: Optional custom node ID
            
        Returns:
            str: The ID of the created node
        """
        if not self._connected:
            raise DatabaseConnectionError("Database is not connected")
        
        self.validate_node_properties(properties)
        
        # Generate node ID if not provided
        if node_id is None:
            node_id = self.generate_node_id()
        
        # Check if node already exists
        if self.graph.has_node(node_id):
            raise ValidationError(f"Node with ID {node_id} already exists")
        
        # Prepare node attributes
        node_attrs = {
            "node_id": node_id,
            "label": label,
            **properties
        }
        
        # Add node to graph
        self.graph.add_node(node_id, **node_attrs)
        
        # Track node by label
        if label not in self._nodes_by_label:
            self._nodes_by_label[label] = set()
        self._nodes_by_label[label].add(node_id)
        
        # Auto-save if enabled
        if self.auto_save:
            await self._save_graph()
        
        logger.debug(f"Created {label} node with ID: {node_id}")
        return node_id
    
    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a node by its ID.
        
        Args:
            node_id: The ID of the node to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Node data or None if not found
        """
        if not self._connected:
            raise DatabaseConnectionError("Database is not connected")
        
        if not self.graph.has_node(node_id):
            return None
        
        # Get node attributes
        node_attrs = dict(self.graph.nodes[node_id])
        
        # Add metadata
        result = {
            **node_attrs,
            "degree": self.graph.degree(node_id),
            "neighbors": list(self.graph.neighbors(node_id))
        }
        
        return result
    
    async def update_node(self, node_id: str, properties: Dict[str, Any]) -> bool:
        """
        Update properties of an existing node.
        
        Args:
            node_id: The ID of the node to update
            properties: New/updated properties
            
        Returns:
            bool: True if update successful, False if node not found
        """
        if not self._connected:
            raise DatabaseConnectionError("Database is not connected")
        
        if not self.graph.has_node(node_id):
            return False
        
        self.validate_node_properties(properties)
        
        # Update node attributes
        self.graph.nodes[node_id].update(properties)
        
        # Auto-save if enabled
        if self.auto_save:
            await self._save_graph()
        
        logger.debug(f"Updated node {node_id}")
        return True
    
    async def delete_node(self, node_id: str) -> bool:
        """
        Delete a node and all its relationships.
        
        Args:
            node_id: The ID of the node to delete
            
        Returns:
            bool: True if deletion successful, False if node not found
        """
        if not self._connected:
            raise DatabaseConnectionError("Database is not connected")
        
        if not self.graph.has_node(node_id):
            return False
        
        # Get node label for tracking cleanup
        node_attrs = self.graph.nodes[node_id]
        label = node_attrs.get("label")
        
        # Remove node (automatically removes all connected edges)
        self.graph.remove_node(node_id)
        
        # Clean up label tracking
        if label and label in self._nodes_by_label:
            self._nodes_by_label[label].discard(node_id)
            if not self._nodes_by_label[label]:
                del self._nodes_by_label[label]
        
        # Auto-save if enabled
        if self.auto_save:
            await self._save_graph()
        
        logger.debug(f"Deleted node {node_id}")
        return True
    
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
            filters: Optional property filters
            limit: Optional limit on results
            
        Returns:
            List[Dict[str, Any]]: List of matching nodes
        """
        if not self._connected:
            raise DatabaseConnectionError("Database is not connected")
        
        results = []
        
        # Get nodes with matching label
        for node_id, node_attrs in self.graph.nodes(data=True):
            if node_attrs.get("label") == label:
                # Apply filters if provided
                if filters:
                    match = True
                    for key, value in filters.items():
                        if node_attrs.get(key) != value:
                            match = False
                            break
                    if not match:
                        continue
                
                # Build result
                result = {
                    **node_attrs,
                    "degree": self.graph.degree(node_id),
                    "neighbors": list(self.graph.neighbors(node_id))
                }
                results.append(result)
                
                # Apply limit if specified
                if limit and len(results) >= limit:
                    break
        
        # Sort by node_id for consistent ordering
        results.sort(key=lambda x: x.get("node_id", ""))
        
        logger.debug(f"Retrieved {len(results)} nodes with label {label}")
        return results
    
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
            relationship_type: Type of relationship
            properties: Optional relationship properties
            
        Returns:
            str: The ID of the created relationship
        """
        if not self._connected:
            raise DatabaseConnectionError("Database is not connected")
        
        # Validate nodes exist
        if not self.graph.has_node(start_node_id):
            raise NodeNotFoundError(f"Start node {start_node_id} not found")
        if not self.graph.has_node(end_node_id):
            raise NodeNotFoundError(f"End node {end_node_id} not found")
        
        self.validate_relationship_type(relationship_type)
        
        if properties is None:
            properties = {}
        
        # Generate relationship ID
        rel_id = str(uuid4())
        self._relationship_counter += 1
        
        # Prepare edge attributes
        edge_attrs = {
            "rel_id": rel_id,
            "type": relationship_type,
            "start_node_id": start_node_id,
            "end_node_id": end_node_id,
            **properties
        }
        
        # Add edge to graph
        self.graph.add_edge(start_node_id, end_node_id, **edge_attrs)
        
        # Auto-save if enabled
        if self.auto_save:
            await self._save_graph()
        
        logger.debug(f"Created {relationship_type} relationship: {rel_id}")
        return rel_id
    
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
            List[Dict[str, Any]]: List of relationships
        """
        if not self._connected:
            raise DatabaseConnectionError("Database is not connected")
        
        if not self.graph.has_node(node_id):
            return []
        
        if direction not in ["incoming", "outgoing", "both"]:
            raise ValidationError("Direction must be 'incoming', 'outgoing', or 'both'")
        
        results = []
        
        # Iterate through all edges connected to the node
        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.edges[node_id, neighbor]
            
            # Determine direction
            start_node = edge_data.get("start_node_id", node_id)
            end_node = edge_data.get("end_node_id", neighbor)
            
            # Filter by direction
            if direction == "outgoing" and start_node != node_id:
                continue
            elif direction == "incoming" and end_node != node_id:
                continue
            
            # Filter by relationship type
            if relationship_type and edge_data.get("type") != relationship_type:
                continue
            
            # Build result
            result = {
                **edge_data,
                "start_node_id": start_node,
                "end_node_id": end_node
            }
            results.append(result)
        
        logger.debug(f"Retrieved {len(results)} relationships for node {node_id}")
        return results
    
    async def delete_relationship(self, relationship_id: str) -> bool:
        """
        Delete a relationship.
        
        Args:
            relationship_id: The ID of the relationship to delete
            
        Returns:
            bool: True if deletion successful, False if relationship not found
        """
        if not self._connected:
            raise DatabaseConnectionError("Database is not connected")
        
        # Find the edge with the given relationship ID
        for u, v, edge_data in self.graph.edges(data=True):
            if edge_data.get("rel_id") == relationship_id:
                self.graph.remove_edge(u, v)
                
                # Auto-save if enabled
                if self.auto_save:
                    await self._save_graph()
                
                logger.debug(f"Deleted relationship {relationship_id}")
                return True
        
        logger.warning(f"Relationship {relationship_id} not found for deletion")
        return False
    
    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a raw query (limited implementation for NetworkX).
        
        Args:
            query: Query string (basic operations only)
            parameters: Optional query parameters
            
        Returns:
            Any: Query results
            
        Note:
            This is a simplified implementation. NetworkX doesn't have a query language.
        """
        if not self._connected:
            raise DatabaseConnectionError("Database is not connected")
        
        # This is a basic implementation for demonstration
        # In practice, you might want to implement a simple query parser
        
        if query.lower().startswith("count nodes"):
            return {"count": self.graph.number_of_nodes()}
        elif query.lower().startswith("count edges"):
            return {"count": self.graph.number_of_edges()}
        elif query.lower().startswith("list nodes"):
            return {"nodes": list(self.graph.nodes())}
        elif query.lower().startswith("list edges"):
            return {"edges": list(self.graph.edges())}
        else:
            raise ValidationError(f"Unsupported query: {query}")
    
    async def clear_all_data(self) -> None:
        """
        Clear all data from the graph.
        
        Warning:
            This operation is irreversible.
        """
        if not self._connected:
            raise DatabaseConnectionError("Database is not connected")
        
        self.graph.clear()
        self._nodes_by_label.clear()
        self._relationship_counter = 0
        
        # Auto-save if enabled
        if self.auto_save:
            await self._save_graph()
        
        logger.warning("Cleared all data from NetworkX database")
    
    # File persistence methods
    async def _save_graph(self) -> None:
        """
        Save the graph to JSON file.
        """
        try:
            # Create backup if file exists
            if self.data_file.exists() and self.backup_count > 0:
                await self._create_backup()
            
            # Convert graph to JSON data
            data = {
                "graph": json_graph.node_link_data(self.graph, edges="links"),
                "metadata": {
                    "nodes_by_label": {k: list(v) for k, v in self._nodes_by_label.items()},
                    "relationship_counter": self._relationship_counter,
                    "node_count": self.graph.number_of_nodes(),
                    "edge_count": self.graph.number_of_edges()
                }
            }
            
            # Write to temporary file first, then move (atomic operation)
            temp_file = self.data_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Atomic move
            temp_file.replace(self.data_file)
            
            logger.debug(f"Saved graph to {self.data_file}")
            
        except Exception as e:
            # Clean up temp file if it exists
            temp_file = self.data_file.with_suffix('.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
            logger.error(f"Failed to save graph: {e}")
            raise DatabaseConnectionError(f"Graph save failed: {e}")
    
    async def _load_graph(self) -> None:
        """
        Load the graph from JSON file.
        """
        if not self.data_file.exists():
            logger.info(f"Data file {self.data_file} doesn't exist, starting with empty graph")
            return
        
        # Check if file is empty
        if self.data_file.stat().st_size == 0:
            logger.info(f"Data file {self.data_file} is empty, starting with empty graph")
            return
        
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
            
            # Load graph
            graph_data = data.get("graph", {})
            
            # Validate graph data structure before loading
            if not isinstance(graph_data, dict) or "nodes" not in graph_data:
                logger.warning(f"Invalid graph structure in {self.data_file}. Expected 'nodes' field. Starting with empty graph.")
                self.graph = nx.Graph()
                self._nodes_by_label = {}
                self._relationship_counter = 0
                return
            
            # Validate that nodes is a list
            if not isinstance(graph_data.get("nodes"), list):
                logger.warning(f"Invalid nodes data in {self.data_file}. Expected list. Starting with empty graph.")
                self.graph = nx.Graph()
                self._nodes_by_label = {}
                self._relationship_counter = 0
                return
            
            # Validate that links is a list (if present)
            if "links" in graph_data and not isinstance(graph_data.get("links"), list):
                logger.warning(f"Invalid links data in {self.data_file}. Expected list. Starting with empty graph.")
                self.graph = nx.Graph()
                self._nodes_by_label = {}
                self._relationship_counter = 0
                return
            
            self.graph = json_graph.node_link_graph(graph_data, edges="links")
            
            # Load metadata (handle case where metadata might be null)
            metadata = data.get("metadata", {})
            if metadata is None:
                metadata = {}
            self._nodes_by_label = {
                k: set(v) for k, v in metadata.get("nodes_by_label", {}).items()
            }
            self._relationship_counter = metadata.get("relationship_counter", 0)
            
            logger.info(f"Loaded graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
            
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in data file {self.data_file}: {e}. Starting with empty graph.")
            # Start with empty graph instead of failing
            self.graph = nx.Graph()
            self._nodes_by_label = {}
            self._relationship_counter = 0
        except Exception as e:
            logger.error(f"Failed to load graph: {e}")
            raise DatabaseConnectionError(f"Graph load failed: {e}")
    
    async def _create_backup(self) -> None:
        """
        Create a backup of the current data file.
        """
        try:
            # Rotate existing backups
            for i in range(self.backup_count - 1, 0, -1):
                old_backup = self.data_file.with_suffix(f'.bak{i}')
                new_backup = self.data_file.with_suffix(f'.bak{i+1}')
                if old_backup.exists():
                    if new_backup.exists():
                        new_backup.unlink()
                    old_backup.rename(new_backup)
            
            # Create new backup
            backup_file = self.data_file.with_suffix('.bak1')
            if backup_file.exists():
                backup_file.unlink()
            self.data_file.rename(backup_file)
            
            logger.debug(f"Created backup: {backup_file}")
            
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current graph.
        
        Returns:
            Dict[str, Any]: Graph statistics
        """
        return {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "nodes_by_label": {k: len(v) for k, v in self._nodes_by_label.items()},
            "is_connected": nx.is_connected(self.graph) if self.graph.number_of_nodes() > 0 else True,
            "average_degree": sum(dict(self.graph.degree()).values()) / max(1, self.graph.number_of_nodes())
        } 