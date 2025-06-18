#!/usr/bin/env python3
"""
Test suite for Learning Management Tools.

This module contains comprehensive tests for the learning_tools module,
covering all core functions, error handling, and edge cases.
"""

import pytest
import asyncio
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# Import the functions to test
from src.tools.learning_tools import (
    record_validated_solution,
    get_learnt_solutions,
    get_solution_details,
    search_learnt_solutions,
    get_solutions_by_error_type,
    get_solutions_by_severity,
    get_recent_solutions,
    get_solutions_statistics,
    update_solution_verification_status,
    validate_database_connection,
    record_multiple_solutions
)

from src.models.learnt import Learnt, ErrorType, SeverityLevel
from src.database import DatabaseConnectionError, NodeNotFoundError, ValidationError


# ================================
# Test Fixtures
# ================================

@pytest.fixture
def sample_solution_data():
    """Sample solution data for testing."""
    return {
        "type_of_error": "IncorrectAction",
        "problem_summary": "AI suggested deprecated React lifecycle method",
        "problematic_input_segment": "How do I fetch data in React?",
        "problematic_ai_output_segment": "Use componentWillMount() to fetch data",
        "inferred_original_cause": "Outdated React knowledge from training data",
        "original_severity": "major",
        "validated_solution_description": "Use useEffect() hook with empty dependency array for data fetching",
        "solution_implemented_notes": "Updated React best practices rule",
        "related_rule_ids": ["rule-123"],
        "created_by": "test_user",
        "tags": ["react", "hooks"],
        "metadata": {"test": True}
    }


@pytest.fixture
def sample_learnt_node():
    """Sample learnt node data for testing."""
    return {
        "learnt_id": "test-learnt-123",
        "timestamp_recorded": datetime.utcnow().isoformat(),
        "type_of_error": "IncorrectAction",
        "problem_summary": "AI suggested deprecated React lifecycle method",
        "problematic_input_segment": "How do I fetch data in React?",
        "problematic_ai_output_segment": "Use componentWillMount() to fetch data",
        "inferred_original_cause": "Outdated React knowledge from training data",
        "original_severity": "major",
        "validated_solution_description": "Use useEffect() hook with empty dependency array",
        "solution_implemented_notes": "Updated React best practices rule",
        "related_rule_ids": ["rule-123"],
        "created_by": "test_user",
        "tags": ["react", "hooks"],
        "metadata": {"test": True},
        "contributed_to_meta_rule": False,
        "meta_rule_contribution": None,
        "verification_status": "validated"
    }


@pytest.fixture
def mock_database():
    """Mock database for testing."""
    db = AsyncMock()
    db.is_connected = True
    db.connect = AsyncMock()
    db.disconnect = AsyncMock()
    db.create_node = AsyncMock(return_value="test-learnt-123")
    db.get_node = AsyncMock()
    db.update_node = AsyncMock(return_value=True)
    db.get_nodes_by_label = AsyncMock(return_value=[])
    db.get_relationships = AsyncMock(return_value=[])
    db.health_check = AsyncMock(return_value=True)
    return db


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


# ================================
# Test Classes
# ================================

class TestRecordValidatedSolution:
    """Test cases for record_validated_solution function."""
    
    @pytest.mark.asyncio
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_record_solution_success(self, mock_get_db, mock_database, sample_solution_data):
        """Test successful solution recording."""
        mock_get_db.return_value = mock_database
        
        result = await record_validated_solution(**sample_solution_data)
        
        assert result == "test-learnt-123"
        mock_database.create_node.assert_called_once()
        mock_database.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_record_solution_with_minimal_data(self, mock_get_db, mock_database):
        """Test recording solution with only required fields."""
        mock_get_db.return_value = mock_database
        
        minimal_data = {
            "type_of_error": "Misunderstanding",
            "problem_summary": "Simple problem",
            "problematic_input_segment": "User input",
            "problematic_ai_output_segment": "AI output",
            "inferred_original_cause": "Root cause",
            "original_severity": "low",
            "validated_solution_description": "Solution description"
        }
        
        result = await record_validated_solution(**minimal_data)
        
        assert result == "test-learnt-123"
        mock_database.create_node.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_solution_missing_required_field(self):
        """Test validation error for missing required field."""
        with pytest.raises(TypeError):
            await record_validated_solution(
                problem_summary="Test problem",
                problematic_input_segment="Input",
                problematic_ai_output_segment="Output",
                inferred_original_cause="Cause",
                original_severity="low",
                validated_solution_description="Solution"
            )
    
    @pytest.mark.asyncio
    async def test_record_solution_invalid_error_type(self, sample_solution_data):
        """Test validation error for invalid error type."""
        sample_solution_data["type_of_error"] = "InvalidErrorType"
        
        with pytest.raises(ValueError, match="Invalid type_of_error"):
            await record_validated_solution(**sample_solution_data)
    
    @pytest.mark.asyncio
    async def test_record_solution_invalid_severity(self, sample_solution_data):
        """Test validation error for invalid severity."""
        sample_solution_data["original_severity"] = "invalid_severity"
        
        with pytest.raises(ValueError, match="Invalid original_severity"):
            await record_validated_solution(**sample_solution_data)
    
    @pytest.mark.asyncio
    async def test_record_solution_problem_summary_too_long(self, sample_solution_data):
        """Test validation error for problem summary too long."""
        sample_solution_data["problem_summary"] = "x" * 501
        
        with pytest.raises(ValueError, match="problem_summary must be 500 characters or less"):
            await record_validated_solution(**sample_solution_data)
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_record_solution_database_error(self, mock_get_db, sample_solution_data):
        """Test database connection error handling."""
        mock_get_db.side_effect = DatabaseConnectionError("Database not available")
        
        with pytest.raises(DatabaseConnectionError):
            await record_validated_solution(**sample_solution_data)


class TestGetLearntSolutions:
    """Test cases for get_learnt_solutions function."""
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_get_all_solutions(self, mock_get_db, mock_database, sample_learnt_node):
        """Test retrieving all solutions without filters."""
        mock_get_db.return_value = mock_database
        mock_database.get_nodes_by_label.return_value = [sample_learnt_node]
        
        result = await get_learnt_solutions()
        
        assert len(result) == 1
        assert result[0]["learnt_id"] == "test-learnt-123"
        mock_database.get_nodes_by_label.assert_called_once_with("Learnt", filters={}, limit=None)
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_get_solutions_with_error_type_filter(self, mock_get_db, mock_database, sample_learnt_node):
        """Test retrieving solutions filtered by error type."""
        mock_get_db.return_value = mock_database
        mock_database.get_nodes_by_label.return_value = [sample_learnt_node]
        
        result = await get_learnt_solutions(error_type="IncorrectAction")
        
        assert len(result) == 1
        mock_database.get_nodes_by_label.assert_called_once_with(
            "Learnt", 
            filters={"type_of_error": "IncorrectAction"}, 
            limit=None
        )
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_get_solutions_with_severity_filter(self, mock_get_db, mock_database, sample_learnt_node):
        """Test retrieving solutions filtered by severity."""
        mock_get_db.return_value = mock_database
        mock_database.get_nodes_by_label.return_value = [sample_learnt_node]
        
        result = await get_learnt_solutions(severity="major")
        
        assert len(result) == 1
        mock_database.get_nodes_by_label.assert_called_once_with(
            "Learnt", 
            filters={"original_severity": "major"}, 
            limit=None
        )
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_get_solutions_with_related_rule_filter(self, mock_get_db, mock_database, sample_learnt_node):
        """Test retrieving solutions filtered by related rule ID."""
        mock_get_db.return_value = mock_database
        mock_database.get_nodes_by_label.return_value = [sample_learnt_node]
        
        result = await get_learnt_solutions(related_rule_id="rule-123")
        
        assert len(result) == 1
        # Should still call without related_rule filter since it's handled in memory
        mock_database.get_nodes_by_label.assert_called_once_with("Learnt", filters={}, limit=None)
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_get_solutions_with_limit(self, mock_get_db, mock_database, sample_learnt_node):
        """Test retrieving solutions with limit."""
        mock_get_db.return_value = mock_database
        mock_database.get_nodes_by_label.return_value = [sample_learnt_node]
        
        result = await get_learnt_solutions(limit=5)
        
        assert len(result) == 1
        mock_database.get_nodes_by_label.assert_called_once_with("Learnt", filters={}, limit=5)
    
    @pytest.mark.asyncio
    async def test_get_solutions_invalid_error_type(self):
        """Test validation error for invalid error type filter."""
        with pytest.raises(ValueError, match="Invalid error_type"):
            await get_learnt_solutions(error_type="InvalidType")
    
    @pytest.mark.asyncio
    async def test_get_solutions_invalid_severity(self):
        """Test validation error for invalid severity filter."""
        with pytest.raises(ValueError, match="Invalid severity"):
            await get_learnt_solutions(severity="invalid")
    
    @pytest.mark.asyncio
    async def test_get_solutions_invalid_limit(self):
        """Test validation error for invalid limit."""
        with pytest.raises(ValueError, match="limit must be a positive integer"):
            await get_learnt_solutions(limit=-1)


class TestGetSolutionDetails:
    """Test cases for get_solution_details function."""
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_get_solution_details_success(self, mock_get_db, mock_database, sample_learnt_node):
        """Test successful retrieval of solution details."""
        mock_get_db.return_value = mock_database
        mock_database.get_node.return_value = sample_learnt_node
        mock_database.get_relationships.return_value = []
        
        result = await get_solution_details("test-learnt-123")
        
        assert result["learnt_id"] == "test-learnt-123"
        assert "relationships" in result
        assert "relationship_count" in result
        assert "learning_summary" in result
        mock_database.get_node.assert_called_once_with("test-learnt-123")
        mock_database.get_relationships.assert_called_once_with("test-learnt-123")
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_get_solution_details_not_found(self, mock_get_db, mock_database):
        """Test error when solution not found."""
        mock_get_db.return_value = mock_database
        mock_database.get_node.return_value = None
        
        with pytest.raises(NodeNotFoundError, match="Learnt solution with ID 'nonexistent' not found"):
            await get_solution_details("nonexistent")
    
    @pytest.mark.asyncio
    async def test_get_solution_details_empty_id(self):
        """Test validation error for empty ID."""
        with pytest.raises(ValueError, match="learnt_id is required and cannot be empty"):
            await get_solution_details("")
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_get_solution_details_with_relationships(self, mock_get_db, mock_database, sample_learnt_node):
        """Test solution details with relationships."""
        mock_get_db.return_value = mock_database
        mock_database.get_node.return_value = sample_learnt_node
        mock_database.get_relationships.return_value = [
            {"type": "RELATES_TO", "target": "rule-123"}
        ]
        
        result = await get_solution_details("test-learnt-123")
        
        assert result["relationship_count"] == 1
        assert len(result["relationships"]) == 1


class TestSearchLearntSolutions:
    """Test cases for search_learnt_solutions function."""
    
    @patch('src.tools.learning_tools.get_learnt_solutions')
    @pytest.mark.asyncio
    async def test_search_solutions_success(self, mock_get_solutions, sample_learnt_node):
        """Test successful search for solutions."""
        mock_get_solutions.return_value = [sample_learnt_node]
        
        result = await search_learnt_solutions("React")
        
        assert len(result) == 1
        assert result[0]["learnt_id"] == "test-learnt-123"
    
    @patch('src.tools.learning_tools.get_learnt_solutions')
    @pytest.mark.asyncio
    async def test_search_solutions_no_matches(self, mock_get_solutions):
        """Test search with no matches."""
        mock_get_solutions.return_value = []
        
        result = await search_learnt_solutions("nonexistent")
        
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_search_solutions_empty_term(self):
        """Test validation error for empty search term."""
        with pytest.raises(ValueError, match="search_term is required and cannot be empty"):
            await search_learnt_solutions("")
    
    @patch('src.tools.learning_tools.get_learnt_solutions')
    @pytest.mark.asyncio
    async def test_search_solutions_with_limit(self, mock_get_solutions, sample_learnt_node):
        """Test search with limit."""
        mock_get_solutions.return_value = [sample_learnt_node, sample_learnt_node]
        
        result = await search_learnt_solutions("React", limit=1)
        
        assert len(result) == 1


class TestGetSolutionsByErrorType:
    """Test cases for get_solutions_by_error_type function."""
    
    @patch('src.tools.learning_tools.get_learnt_solutions')
    @pytest.mark.asyncio
    async def test_get_solutions_by_error_type(self, mock_get_solutions, sample_learnt_node):
        """Test retrieving solutions by error type."""
        mock_get_solutions.return_value = [sample_learnt_node]
        
        result = await get_solutions_by_error_type("IncorrectAction")
        
        assert len(result) == 1
        mock_get_solutions.assert_called_once_with(error_type="IncorrectAction")


class TestGetSolutionsBySeverity:
    """Test cases for get_solutions_by_severity function."""
    
    @patch('src.tools.learning_tools.get_learnt_solutions')
    @pytest.mark.asyncio
    async def test_get_solutions_by_severity(self, mock_get_solutions, sample_learnt_node):
        """Test retrieving solutions by severity."""
        mock_get_solutions.return_value = [sample_learnt_node]
        
        result = await get_solutions_by_severity("major")
        
        assert len(result) == 1
        mock_get_solutions.assert_called_once_with(severity="major")


class TestGetRecentSolutions:
    """Test cases for get_recent_solutions function."""
    
    @patch('src.tools.learning_tools.get_learnt_solutions')
    @pytest.mark.asyncio
    async def test_get_recent_solutions(self, mock_get_solutions, sample_learnt_node):
        """Test retrieving recent solutions."""
        # Set timestamp to recent
        sample_learnt_node["timestamp_recorded"] = datetime.utcnow().isoformat()
        mock_get_solutions.return_value = [sample_learnt_node]
        
        result = await get_recent_solutions(days=7)
        
        assert len(result) == 1
    
    @patch('src.tools.learning_tools.get_learnt_solutions')
    @pytest.mark.asyncio
    async def test_get_recent_solutions_old_data(self, mock_get_solutions):
        """Test filtering out old solutions."""
        old_solution = {
            "learnt_id": "old-solution",
            "timestamp_recorded": (datetime.utcnow() - timedelta(days=30)).isoformat()
        }
        mock_get_solutions.return_value = [old_solution]
        
        result = await get_recent_solutions(days=7)
        
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_get_recent_solutions_invalid_days(self):
        """Test validation error for invalid days parameter."""
        with pytest.raises(ValueError, match="days must be a positive integer"):
            await get_recent_solutions(days=-1)


class TestGetSolutionsStatistics:
    """Test cases for get_solutions_statistics function."""
    
    @patch('src.tools.learning_tools.get_learnt_solutions')
    @pytest.mark.asyncio
    async def test_get_solutions_statistics(self, mock_get_solutions, sample_learnt_node):
        """Test retrieving solution statistics."""
        mock_get_solutions.return_value = [sample_learnt_node]
        
        result = await get_solutions_statistics()
        
        assert result["total_solutions"] == 1
        assert "by_error_type" in result
        assert "by_severity" in result
        assert "by_verification_status" in result
        assert result["by_error_type"]["IncorrectAction"] == 1
        assert result["by_severity"]["major"] == 1


class TestUpdateSolutionVerificationStatus:
    """Test cases for update_solution_verification_status function."""
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_update_verification_status_success(self, mock_get_db, mock_database, sample_learnt_node):
        """Test successful verification status update."""
        mock_get_db.return_value = mock_database
        mock_database.get_node.return_value = sample_learnt_node
        mock_database.update_node.return_value = True
        
        result = await update_solution_verification_status("test-learnt-123", "pending")
        
        assert result["verification_status"] == "pending"
        mock_database.update_node.assert_called_once_with("test-learnt-123", {"verification_status": "pending"})
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_update_verification_status_not_found(self, mock_get_db, mock_database):
        """Test error when solution not found."""
        mock_get_db.return_value = mock_database
        mock_database.get_node.return_value = None
        
        with pytest.raises(NodeNotFoundError):
            await update_solution_verification_status("nonexistent", "pending")
    
    @pytest.mark.asyncio
    async def test_update_verification_status_invalid_status(self):
        """Test validation error for invalid status."""
        with pytest.raises(ValueError, match="Invalid verification_status"):
            await update_solution_verification_status("test-id", "invalid_status")


class TestValidateDatabaseConnection:
    """Test cases for validate_database_connection function."""
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_validate_connection_success(self, mock_get_db, mock_database):
        """Test successful database connection validation."""
        mock_get_db.return_value = mock_database
        mock_database.health_check.return_value = True
        
        result = await validate_database_connection()
        
        assert result is True
        mock_database.health_check.assert_called_once()
        mock_database.disconnect.assert_called_once()
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_validate_connection_failure(self, mock_get_db):
        """Test database connection validation failure."""
        mock_get_db.side_effect = DatabaseConnectionError("Connection failed")
        
        with pytest.raises(DatabaseConnectionError):
            await validate_database_connection()


class TestRecordMultipleSolutions:
    """Test cases for record_multiple_solutions function."""
    
    @patch('src.tools.learning_tools.record_validated_solution')
    @pytest.mark.asyncio
    async def test_record_multiple_solutions_success(self, mock_record, sample_solution_data):
        """Test successful recording of multiple solutions."""
        mock_record.side_effect = ["id1", "id2"]
        
        solutions_data = [sample_solution_data, sample_solution_data]
        result = await record_multiple_solutions(solutions_data)
        
        assert result == ["id1", "id2"]
        assert mock_record.call_count == 2
    
    @pytest.mark.asyncio
    async def test_record_multiple_solutions_empty_list(self):
        """Test validation error for empty solutions list."""
        with pytest.raises(ValueError, match="solutions_data must be a non-empty list"):
            await record_multiple_solutions([])
    
    @patch('src.tools.learning_tools.record_validated_solution')
    @pytest.mark.asyncio
    async def test_record_multiple_solutions_partial_failure(self, mock_record, sample_solution_data):
        """Test handling of partial failures in batch recording."""
        mock_record.side_effect = ["id1", ValueError("Invalid data")]
        
        solutions_data = [sample_solution_data, sample_solution_data]
        
        with pytest.raises(ValidationError, match="Failed to create some solutions"):
            await record_multiple_solutions(solutions_data)


# ================================
# Integration Tests
# ================================

class TestLearningToolsIntegration:
    """Integration tests for learning tools."""
    
    @patch.dict(os.environ, {"GRAPH_DB_TYPE": "networkx"})
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_full_workflow_integration(self, mock_get_db, mock_database, sample_solution_data):
        """Test complete workflow from recording to retrieval."""
        mock_get_db.return_value = mock_database
        
        # Mock database responses
        mock_database.create_node.return_value = "test-learnt-123"
        mock_database.get_nodes_by_label.return_value = [{
            **sample_solution_data,
            "learnt_id": "test-learnt-123",
            "timestamp_recorded": datetime.utcnow().isoformat()
        }]
        
        # Record solution
        learnt_id = await record_validated_solution(**sample_solution_data)
        assert learnt_id == "test-learnt-123"
        
        # Retrieve solutions
        solutions = await get_learnt_solutions()
        assert len(solutions) == 1
        assert solutions[0]["learnt_id"] == "test-learnt-123"


# ================================
# Performance Tests
# ================================

class TestLearningToolsPerformance:
    """Performance tests for learning tools."""
    
    @patch('src.tools.learning_tools.get_database')
    @pytest.mark.asyncio
    async def test_batch_recording_performance(self, mock_get_db, mock_database, sample_solution_data):
        """Test performance of batch solution recording."""
        mock_get_db.return_value = mock_database
        mock_database.create_node.side_effect = [f"id-{i}" for i in range(100)]
        
        # Create 100 solutions
        solutions_data = [sample_solution_data.copy() for _ in range(100)]
        
        import time
        start_time = time.time()
        result = await record_multiple_solutions(solutions_data)
        end_time = time.time()
        
        assert len(result) == 100
        # Should complete within reasonable time (adjust threshold as needed)
        assert (end_time - start_time) < 10.0  # 10 seconds threshold 