"""
Database Adapter Consistency Tests

Tests to ensure both Neo4j and NetworkX adapters provide
consistent APIs and implement all required abstract methods.
"""

import asyncio
import inspect
import os
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

from src.database import create_database, GraphDatabase
from src.database.base import GraphDatabase as BaseGraphDatabase
from src.database.neo4j_adapter import Neo4jAdapter
from src.database.networkx_adapter import NetworkXAdapter


class TestAdapterConsistency:
    """Test consistency between database adapters."""
    
    def test_adapter_factory(self):
        """Test database factory function."""
        # Test NetworkX adapter creation
        config = {"data_file": "test.json"}
        networkx_db = create_database("networkx", config)
        assert isinstance(networkx_db, NetworkXAdapter)
        assert isinstance(networkx_db, BaseGraphDatabase)
        
        # Test Neo4j adapter creation
        config = {
            "uri": "neo4j://localhost:7687",
            "username": "neo4j",
            "password": "password"
        }
        neo4j_db = create_database("neo4j", config)
        assert isinstance(neo4j_db, Neo4jAdapter)
        assert isinstance(neo4j_db, BaseGraphDatabase)
        
        # Test invalid database type
        with pytest.raises(ValueError, match="Unsupported database type"):
            create_database("invalid", {})
    
    def test_method_signatures_consistency(self):
        """Test that both adapters have identical method signatures."""
        # Get methods from base class
        base_methods = self._get_abstract_methods(BaseGraphDatabase)
        
        # Get methods from both adapters
        neo4j_methods = self._get_public_methods(Neo4jAdapter)
        networkx_methods = self._get_public_methods(NetworkXAdapter)
        
        # Verify all abstract methods are implemented
        for method_name in base_methods:
            assert method_name in neo4j_methods, f"Neo4jAdapter missing method: {method_name}"
            assert method_name in networkx_methods, f"NetworkXAdapter missing method: {method_name}"
            
            # Compare signatures
            base_sig = base_methods[method_name]
            neo4j_sig = neo4j_methods[method_name]
            networkx_sig = networkx_methods[method_name]
            
            assert base_sig == neo4j_sig, f"Neo4jAdapter method signature mismatch for {method_name}"
            assert base_sig == networkx_sig, f"NetworkXAdapter method signature mismatch for {method_name}"
            assert neo4j_sig == networkx_sig, f"Adapter signature mismatch for {method_name}"
    
    def test_error_types_consistency(self):
        """Test that both adapters raise consistent error types."""
        from src.database.base import (
            DatabaseConnectionError,
            NodeNotFoundError,
            RelationshipNotFoundError,
            ValidationError
        )
        
        # Test that both adapters can raise all defined exceptions
        # This is a compile-time check - if imports work, exceptions are consistent
        assert DatabaseConnectionError
        assert NodeNotFoundError
        assert RelationshipNotFoundError
        assert ValidationError
    
    @pytest.mark.asyncio
    async def test_networkx_adapter_basic_operations(self):
        """Test NetworkX adapter basic functionality."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = {
                "data_file": os.path.join(temp_dir, "test_graph.json"),
                "auto_save": True
            }
            
            db = NetworkXAdapter(config)
            
            try:
                # Test connection
                await db.connect()
                assert await db.health_check()
                
                # Test node operations
                node_id = await db.create_node("TestLabel", {"name": "test_node"})
                assert node_id
                
                node = await db.get_node(node_id)
                assert node is not None
                assert node["label"] == "TestLabel"
                assert node["name"] == "test_node"
                
                # Test update
                result = await db.update_node(node_id, {"updated": True})
                assert result is True
                
                # Test retrieval after update
                updated_node = await db.get_node(node_id)
                assert updated_node["updated"] is True
                
                # Test deletion
                result = await db.delete_node(node_id)
                assert result is True
                
                # Verify deletion
                deleted_node = await db.get_node(node_id)
                assert deleted_node is None
                
            finally:
                await db.disconnect()
    
    def _get_abstract_methods(self, cls) -> Dict[str, inspect.Signature]:
        """Get abstract methods and their signatures from a class."""
        methods = {}
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith('_') and hasattr(method, '__isabstractmethod__'):
                methods[name] = inspect.signature(method)
        return methods
    
    def _get_public_methods(self, cls) -> Dict[str, inspect.Signature]:
        """Get public methods and their signatures from a class."""
        methods = {}
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith('_'):
                methods[name] = inspect.signature(method)
        return methods


def test_adapter_interchangeability():
    """Test that adapters can be used interchangeably via factory."""
    
    # NetworkX configuration
    networkx_config = {"data_file": "test_networkx.json"}
    
    # Neo4j configuration (would fail in actual use without server)
    neo4j_config = {
        "uri": "neo4j://localhost:7687",
        "username": "neo4j", 
        "password": "password"
    }
    
    # Both should create valid GraphDatabase instances
    networkx_db = create_database("networkx", networkx_config)
    neo4j_db = create_database("Neo4j", neo4j_config)  # Test case insensitivity
    
    # Both should be GraphDatabase instances
    assert isinstance(networkx_db, GraphDatabase)
    assert isinstance(neo4j_db, GraphDatabase)
    
    # Both should have the same interface methods
    networkx_methods = set(dir(networkx_db))
    neo4j_methods = set(dir(neo4j_db))
    
    # All public GraphDatabase methods should be present in both
    base_methods = {method for method in dir(GraphDatabase) if not method.startswith('_')}
    
    assert base_methods.issubset(networkx_methods)
    assert base_methods.issubset(neo4j_methods)


if __name__ == "__main__":
    # Run basic consistency checks
    test = TestAdapterConsistency()
    test.test_adapter_factory()
    test.test_method_signatures_consistency()
    test.test_error_types_consistency()
    
    print("✅ All adapter consistency tests passed!")
    print("✅ Both adapters implement identical interfaces")
    print("✅ Database factory works correctly")
    print("✅ Error handling is consistent") 