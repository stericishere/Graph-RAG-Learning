#!/usr/bin/env python3
"""
Comprehensive Test Suite for Rule Management Tools.
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import Mock, AsyncMock, patch

# Add src to path
sys.path.insert(0, '.')

from src.tools.rule_tools import (
    create_rule, update_rule, delete_rule, get_all_rules, get_rule_details,
    search_rules, validate_database_connection
)
from src.database import DatabaseConnectionError, NodeNotFoundError, ValidationError


@pytest.fixture
def sample_rule_data():
    """Sample rule data for testing."""
    return {
        "rule_name": "React Performance Optimization",
        "content": "Always use React.memo() for components that receive complex props",
        "category": "frontend",
        "rule_type": "best_practice",
        "priority": 8,
        "tags": ["react", "performance"],
        "created_by": "test_user",
        "metadata": {"version": "1.0"}
    }


@pytest.fixture
def mock_database():
    """Mock database instance for testing."""
    db = AsyncMock()
    db.is_connected = True
    db.connect = AsyncMock()
    db.disconnect = AsyncMock()
    db.health_check = AsyncMock(return_value=True)
    db.create_node = AsyncMock(return_value="test-rule-id")
    db.get_node = AsyncMock()
    db.update_node = AsyncMock(return_value=True)
    db.delete_node = AsyncMock(return_value=True)
    db.get_nodes_by_label = AsyncMock(return_value=[])
    db.get_relationships = AsyncMock(return_value=[])
    return db


class TestCreateRule:
    """Test rule creation functionality."""
    
    @pytest.mark.asyncio
    async def test_create_rule_success(self, sample_rule_data, mock_database):
        """Test successful rule creation."""
        with patch('src.tools.rule_tools.get_database', return_value=mock_database), \
             patch('src.tools.rule_tools.Rule') as mock_rule_class:
            
            mock_rule = Mock()
            mock_rule.rule_id = "test-rule-id"
            mock_rule.to_dict.return_value = sample_rule_data
            mock_rule_class.return_value = mock_rule
            
            result = await create_rule(**sample_rule_data)
            
            assert result == "test-rule-id"
            mock_database.create_node.assert_called_once()
            mock_database.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_rule_empty_name(self):
        """Test rule creation with empty name fails."""
        with pytest.raises(ValueError, match="rule_name is required"):
            await create_rule("", "content", "frontend", "best_practice")


class TestUpdateRule:
    """Test rule update functionality."""
    
    @pytest.mark.asyncio
    async def test_update_rule_success(self, mock_database):
        """Test successful rule update."""
        existing_data = {
            "rule_id": "test-rule-id",
            "rule_name": "Old Name",
            "content": "Old content",
            "category": "general",
            "rule_type": "best_practice",
            "priority": 5,
            "created_at": "2024-01-01T00:00:00"
        }
        
        updates = {"rule_name": "New Name", "priority": 8}
        mock_database.get_node.return_value = existing_data
        
        with patch('src.tools.rule_tools.get_database', return_value=mock_database), \
             patch('src.tools.rule_tools.Rule') as mock_rule_class:
            
            mock_rule = Mock()
            updated_data = {**existing_data, **updates}
            mock_rule.to_dict.return_value = updated_data
            mock_rule_class.from_dict.return_value = mock_rule
            
            result = await update_rule("test-rule-id", updates)
            
            assert result == updated_data
            mock_database.update_node.assert_called_once()


class TestDeleteRule:
    """Test rule deletion functionality."""
    
    @pytest.mark.asyncio
    async def test_delete_rule_success(self, mock_database):
        """Test successful rule deletion."""
        mock_database.get_node.return_value = {"rule_id": "test-rule-id"}
        
        with patch('src.tools.rule_tools.get_database', return_value=mock_database):
            result = await delete_rule("test-rule-id")
            
            assert result is True
            mock_database.delete_node.assert_called_once_with("test-rule-id")


class TestGetAllRules:
    """Test rule retrieval functionality."""
    
    @pytest.mark.asyncio
    async def test_get_all_rules_success(self, mock_database):
        """Test getting all rules."""
        sample_rules = [
            {
                "rule_id": "rule-1",
                "rule_name": "Rule 1",
                "priority": 8,
                "created_at": "2024-01-01T00:00:00",
                "is_meta_rule": False
            }
        ]
        
        mock_database.get_nodes_by_label.return_value = sample_rules
        
        with patch('src.tools.rule_tools.get_database', return_value=mock_database):
            result = await get_all_rules()
            
            assert len(result) == 1
            assert result[0]["rule_id"] == "rule-1"


class TestGetRuleDetails:
    """Test rule details retrieval functionality."""
    
    @pytest.mark.asyncio
    async def test_get_rule_details_success(self, mock_database):
        """Test successful rule details retrieval."""
        rule_data = {
            "rule_id": "test-rule-id",
            "rule_name": "Test Rule",
            "is_meta_rule": False
        }
        
        relationships = [{"id": "rel-1", "type": "IMPROVES"}]
        
        mock_database.get_node.return_value = rule_data
        mock_database.get_relationships.return_value = relationships
        
        with patch('src.tools.rule_tools.get_database', return_value=mock_database):
            result = await get_rule_details("test-rule-id")
            
            assert result["rule_id"] == "test-rule-id"
            assert result["relationships"] == relationships
            assert result["relationship_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
