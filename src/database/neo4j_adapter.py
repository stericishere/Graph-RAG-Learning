"""
Neo4j Database Adapter

This module implements the GraphDatabase interface for Neo4j using the official
Neo4j Python driver with async support.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from neo4j import AsyncGraphDatabase, AsyncDriver, RoutingControl
from neo4j.exceptions import Neo4jError, DriverError

from .base import (
    GraphDatabase,
    DatabaseConnectionError,
    NodeNotFoundError,
    RelationshipNotFoundError,
    ValidationError
)

logger = logging.getLogger(__name__)


class Neo4jAdapter(GraphDatabase):
    """
    Neo4j implementation of the GraphDatabase interface.
    
    This adapter uses the official Neo4j Python driver to provide
    graph database operations for Rules and Learnt nodes.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Neo4j adapter.
        
        Args:
            config: Configuration dictionary containing:
                - uri: Neo4j connection URI (e.g., "neo4j://localhost:7687")
                - username: Database username
                - password: Database password
                - database: Target database name (optional, defaults to "neo4j")
        """
        super().__init__(config)
        self.driver: Optional[AsyncDriver] = None
        self.database = config.get("database", "neo4j")
        
        # Validate required configuration
        required_fields = ["uri", "username", "password"]
        for field in required_fields:
            if field not in config:
                raise ValidationError(f"Missing required configuration field: {field}")
    
    async def connect(self) -> None:
        """
        Establish connection to Neo4j database.
        
        Raises:
            DatabaseConnectionError: If connection fails
        """
        try:
            self.driver = AsyncGraphDatabase.driver(
                self.config["uri"],
                auth=(self.config["username"], self.config["password"]),
                max_connection_pool_size=self.config.get("max_connection_pool_size", 10),
                connection_acquisition_timeout=self.config.get("connection_timeout", 30)
            )
            
            # Verify connectivity
            await self.driver.verify_connectivity()
            self._connected = True
            logger.info("Successfully connected to Neo4j database")
            
        except (Neo4jError, DriverError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise DatabaseConnectionError(f"Neo4j connection failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error connecting to Neo4j: {e}")
            raise DatabaseConnectionError(f"Unexpected connection error: {e}")
    
    async def disconnect(self) -> None:
        """
        Close the Neo4j connection.
        """
        if self.driver:
            await self.driver.close()
            self._connected = False
            logger.info("Disconnected from Neo4j database")
    
    async def health_check(self) -> bool:
        """
        Check if the database is healthy and responsive.
        
        Returns:
            bool: True if database is healthy, False otherwise
        """
        if not self.driver or not self._connected:
            return False
        
        try:
            # Simple query to test connectivity
            await self.driver.execute_query(
                "RETURN 1 as health_check",
                database_=self.database,
                routing_=RoutingControl.READ
            )
            return True
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
        Create a new node in Neo4j.
        
        Args:
            label: Node label (e.g., "Rule", "Learnt")
            properties: Node properties
            node_id: Optional custom node ID
            
        Returns:
            str: The ID of the created node
            
        Raises:
            ValidationError: If properties are invalid
            DatabaseConnectionError: If database is not connected
        """
        if not self._connected:
            raise DatabaseConnectionError("Database is not connected")
        
        self.validate_node_properties(properties)
        
        # Generate node ID if not provided
        if node_id is None:
            node_id = self.generate_node_id()
        
        # Add node_id to properties
        properties_with_id = {**properties, "node_id": node_id}
        
        try:
            query = f"""
            CREATE (n:{label} $properties)
            RETURN n.node_id as node_id
            """
            
            record = await self.driver.execute_query(
                query,
                properties=properties_with_id,
                database_=self.database,
                routing_=RoutingControl.WRITE,
                result_transformer_=lambda r: r.single(strict=True)
            )
            
            logger.debug(f"Created {label} node with ID: {node_id}")
            return record["node_id"]
            
        except (Neo4jError, DriverError) as e:
            logger.error(f"Failed to create node: {e}")
            raise DatabaseConnectionError(f"Node creation failed: {e}")
    
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
        
        try:
            query = """
            MATCH (n {node_id: $node_id})
            RETURN n, labels(n) as labels, id(n) as internal_id
            """
            
            records, _, _ = await self.driver.execute_query(
                query,
                node_id=node_id,
                database_=self.database,
                routing_=RoutingControl.READ
            )
            
            if not records:
                return None
            
            record = records[0]
            node = record["n"]
            
            # Build result dictionary
            result = {
                "node_id": node_id,
                "labels": record["labels"],
                "internal_id": record["internal_id"],
                **dict(node)
            }
            
            return result
            
        except (Neo4jError, DriverError) as e:
            logger.error(f"Failed to get node {node_id}: {e}")
            raise DatabaseConnectionError(f"Node retrieval failed: {e}")
    
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
        
        self.validate_node_properties(properties)
        
        try:
            # Create SET clauses for each property
            set_clauses = []
            params = {"node_id": node_id}
            
            for key, value in properties.items():
                param_name = f"prop_{key}"
                set_clauses.append(f"n.{key} = ${param_name}")
                params[param_name] = value
            
            query = f"""
            MATCH (n {{node_id: $node_id}})
            SET {', '.join(set_clauses)}
            RETURN n.node_id as updated_id
            """
            
            records, _, _ = await self.driver.execute_query(
                query,
                **params,
                database_=self.database,
                routing_=RoutingControl.WRITE
            )
            
            if records:
                logger.debug(f"Updated node {node_id}")
                return True
            else:
                logger.warning(f"Node {node_id} not found for update")
                return False
                
        except (Neo4jError, DriverError) as e:
            logger.error(f"Failed to update node {node_id}: {e}")
            raise DatabaseConnectionError(f"Node update failed: {e}")
    
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
        
        try:
            query = """
            MATCH (n {node_id: $node_id})
            DETACH DELETE n
            RETURN count(n) as deleted_count
            """
            
            record = await self.driver.execute_query(
                query,
                node_id=node_id,
                database_=self.database,
                routing_=RoutingControl.WRITE,
                result_transformer_=lambda r: r.single(strict=True)
            )
            
            deleted_count = record["deleted_count"]
            if deleted_count > 0:
                logger.debug(f"Deleted node {node_id}")
                return True
            else:
                logger.warning(f"Node {node_id} not found for deletion")
                return False
                
        except (Neo4jError, DriverError) as e:
            logger.error(f"Failed to delete node {node_id}: {e}")
            raise DatabaseConnectionError(f"Node deletion failed: {e}")
    
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
        
        try:
            # Build WHERE clause for filters
            where_clauses = []
            params = {}
            
            if filters:
                for key, value in filters.items():
                    param_name = f"filter_{key}"
                    where_clauses.append(f"n.{key} = ${param_name}")
                    params[param_name] = value
            
            where_clause = ""
            if where_clauses:
                where_clause = "WHERE " + " AND ".join(where_clauses)
            
            limit_clause = ""
            if limit:
                limit_clause = f"LIMIT {limit}"
            
            query = f"""
            MATCH (n:{label})
            {where_clause}
            RETURN n, labels(n) as labels, id(n) as internal_id
            ORDER BY n.node_id
            {limit_clause}
            """
            
            records, _, _ = await self.driver.execute_query(
                query,
                **params,
                database_=self.database,
                routing_=RoutingControl.READ
            )
            
            results = []
            for record in records:
                node = record["n"]
                result = {
                    "node_id": node.get("node_id"),
                    "labels": record["labels"],
                    "internal_id": record["internal_id"],
                    **dict(node)
                }
                results.append(result)
            
            logger.debug(f"Retrieved {len(results)} nodes with label {label}")
            return results
            
        except (Neo4jError, DriverError) as e:
            logger.error(f"Failed to get nodes by label {label}: {e}")
            raise DatabaseConnectionError(f"Node query failed: {e}")
    
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
        
        self.validate_relationship_type(relationship_type)
        
        if properties is None:
            properties = {}
        
        # Generate relationship ID
        rel_id = str(uuid4())
        properties_with_id = {**properties, "rel_id": rel_id}
        
        try:
            query = f"""
            MATCH (start {{node_id: $start_node_id}}), (end {{node_id: $end_node_id}})
            CREATE (start)-[r:{relationship_type} $properties]->(end)
            RETURN r.rel_id as rel_id
            """
            
            record = await self.driver.execute_query(
                query,
                start_node_id=start_node_id,
                end_node_id=end_node_id,
                properties=properties_with_id,
                database_=self.database,
                routing_=RoutingControl.WRITE,
                result_transformer_=lambda r: r.single(strict=True)
            )
            
            logger.debug(f"Created {relationship_type} relationship: {rel_id}")
            return record["rel_id"]
            
        except (Neo4jError, DriverError) as e:
            if "start" in str(e).lower() or "end" in str(e).lower():
                raise NodeNotFoundError(f"One or both nodes not found: {start_node_id}, {end_node_id}")
            logger.error(f"Failed to create relationship: {e}")
            raise DatabaseConnectionError(f"Relationship creation failed: {e}")
    
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
        
        if direction not in ["incoming", "outgoing", "both"]:
            raise ValidationError("Direction must be 'incoming', 'outgoing', or 'both'")
        
        try:
            # Build relationship pattern based on direction
            if direction == "incoming":
                rel_pattern = f"(other)-[r{':' + relationship_type if relationship_type else ''}]->(n)"
            elif direction == "outgoing":
                rel_pattern = f"(n)-[r{':' + relationship_type if relationship_type else ''}]->(other)"
            else:  # both
                rel_pattern = f"(n)-[r{':' + relationship_type if relationship_type else ''}]-(other)"
            
            query = f"""
            MATCH {rel_pattern}
            WHERE n.node_id = $node_id
            RETURN r, type(r) as rel_type, id(r) as internal_id,
                   startNode(r).node_id as start_node_id,
                   endNode(r).node_id as end_node_id
            """
            
            records, _, _ = await self.driver.execute_query(
                query,
                node_id=node_id,
                database_=self.database,
                routing_=RoutingControl.READ
            )
            
            results = []
            for record in records:
                rel = record["r"]
                result = {
                    "rel_id": rel.get("rel_id"),
                    "type": record["rel_type"],
                    "internal_id": record["internal_id"],
                    "start_node_id": record["start_node_id"],
                    "end_node_id": record["end_node_id"],
                    **dict(rel)
                }
                results.append(result)
            
            logger.debug(f"Retrieved {len(results)} relationships for node {node_id}")
            return results
            
        except (Neo4jError, DriverError) as e:
            logger.error(f"Failed to get relationships for node {node_id}: {e}")
            raise DatabaseConnectionError(f"Relationship query failed: {e}")
    
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
        
        try:
            query = """
            MATCH ()-[r {rel_id: $rel_id}]-()
            DELETE r
            RETURN count(r) as deleted_count
            """
            
            record = await self.driver.execute_query(
                query,
                rel_id=relationship_id,
                database_=self.database,
                routing_=RoutingControl.WRITE,
                result_transformer_=lambda r: r.single(strict=True)
            )
            
            deleted_count = record["deleted_count"]
            if deleted_count > 0:
                logger.debug(f"Deleted relationship {relationship_id}")
                return True
            else:
                logger.warning(f"Relationship {relationship_id} not found for deletion")
                return False
                
        except (Neo4jError, DriverError) as e:
            logger.error(f"Failed to delete relationship {relationship_id}: {e}")
            raise DatabaseConnectionError(f"Relationship deletion failed: {e}")
    
    async def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a raw Cypher query.
        
        Args:
            query: The Cypher query string
            parameters: Optional query parameters
            
        Returns:
            Any: Query results
        """
        if not self._connected:
            raise DatabaseConnectionError("Database is not connected")
        
        try:
            records, summary, keys = await self.driver.execute_query(
                query,
                parameters or {},
                database_=self.database,
                routing_=RoutingControl.WRITE
            )
            
            return {
                "records": [dict(record) for record in records],
                "summary": summary,
                "keys": keys
            }
            
        except (Neo4jError, DriverError) as e:
            logger.error(f"Failed to execute query: {e}")
            raise DatabaseConnectionError(f"Query execution failed: {e}")
    
    async def clear_all_data(self) -> None:
        """
        Clear all data from the database.
        
        Warning:
            This operation is irreversible.
        """
        if not self._connected:
            raise DatabaseConnectionError("Database is not connected")
        
        try:
            # Delete all nodes and relationships
            await self.driver.execute_query(
                "MATCH (n) DETACH DELETE n",
                database_=self.database,
                routing_=RoutingControl.WRITE
            )
            
            logger.warning("Cleared all data from Neo4j database")
            
        except (Neo4jError, DriverError) as e:
            logger.error(f"Failed to clear database: {e}")
            raise DatabaseConnectionError(f"Database clear failed: {e}") 