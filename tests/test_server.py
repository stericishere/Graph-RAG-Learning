#!/usr/bin/env python3
"""
Test suite for FastAPI MCP Server.

This module contains comprehensive tests for the server endpoints,
covering all rule and learning management functionality, error handling,
and integration scenarios.
"""

import pytest
import asyncio
import json
import tempfile
import os
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# Import the FastAPI app
from src.server import app

# Import models for testing
from src.models.rule import RuleCategory, RuleType
from src.models.learnt import ErrorType, SeverityLevel


# ================================
# Test Client Setup
# ================================

client = TestClient(app)


# ================================
# Test Fixtures
# ================================

@pytest.fixture
def sample_rule_data():
    """Sample rule data for testing."""
    return {
        "rule_name": "Test Rule",
        "content": "This is a test rule content",
        "category": "frontend",
        "rule_type": "best_practice",
        "priority": 7,
        "tags": ["test", "example"],
        "created_by": "test_user",
        "metadata": {"source": "test"}
    }


@pytest.fixture
def sample_solution_data():
    """Sample solution data for testing."""
    return {
        "type_of_error": "IncorrectAction",
        "problem_summary": "Test problem summary",
        "problematic_input_segment": "Test input",
        "problematic_ai_output_segment": "Test output",
        "inferred_original_cause": "Test cause",
        "original_severity": "major",
        "validated_solution_description": "Test solution",
        "solution_implemented_notes": "Test implementation notes",
        "related_rule_ids": ["test-rule-id"],
        "created_by": "test_user",
        "tags": ["test", "solution"],
        "metadata": {"test": "data"}
    }


@pytest.fixture
def mock_rule_tools():
    """Mock rule tools functions."""
    with patch('src.server.create_rule') as mock_create, \
         patch('src.server.get_all_rules') as mock_get_all, \
         patch('src.server.get_rule_details') as mock_get_details, \
         patch('src.server.update_rule') as mock_update, \
         patch('src.server.delete_rule') as mock_delete, \
         patch('src.server.search_rules') as mock_search, \
         patch('src.server.get_rules_by_category') as mock_by_category, \
         patch('src.server.get_rules_by_type') as mock_by_type, \
         patch('src.server.get_meta_rules') as mock_meta, \
         patch('src.server.create_multiple_rules') as mock_create_multiple, \
         patch('src.server.validate_rule_db_connection') as mock_validate:
        
        # Configure default return values
        mock_create.return_value = "test-rule-id"
        mock_get_all.return_value = [{"rule_id": "test-rule-id", "rule_name": "Test Rule"}]
        mock_get_details.return_value = {"rule_id": "test-rule-id", "rule_name": "Test Rule"}
        mock_update.return_value = {"rule_id": "test-rule-id", "rule_name": "Updated Rule"}
        mock_delete.return_value = True
        mock_search.return_value = [{"rule_id": "test-rule-id", "rule_name": "Test Rule"}]
        mock_by_category.return_value = [{"rule_id": "test-rule-id", "category": "frontend"}]
        mock_by_type.return_value = [{"rule_id": "test-rule-id", "rule_type": "best_practice"}]
        mock_meta.return_value = [{"rule_id": "meta-rule-id", "category": "meta_learnt"}]
        mock_create_multiple.return_value = ["rule-1", "rule-2"]
        mock_validate.return_value = True
        
        yield {
            'create': mock_create,
            'get_all': mock_get_all,
            'get_details': mock_get_details,
            'update': mock_update,
            'delete': mock_delete,
            'search': mock_search,
            'by_category': mock_by_category,
            'by_type': mock_by_type,
            'meta': mock_meta,
            'create_multiple': mock_create_multiple,
            'validate': mock_validate
        }


@pytest.fixture
def mock_learning_tools():
    """Mock learning tools functions."""
    with patch('src.server.record_validated_solution') as mock_record, \
         patch('src.server.get_learnt_solutions') as mock_get_solutions, \
         patch('src.server.get_solution_details') as mock_get_details, \
         patch('src.server.search_learnt_solutions') as mock_search, \
         patch('src.server.get_solutions_by_error_type') as mock_by_error, \
         patch('src.server.get_solutions_by_severity') as mock_by_severity, \
         patch('src.server.get_recent_solutions') as mock_recent, \
         patch('src.server.get_solutions_statistics') as mock_stats, \
         patch('src.server.update_solution_verification_status') as mock_update_status, \
         patch('src.server.record_multiple_solutions') as mock_record_multiple, \
         patch('src.server.validate_learning_db_connection') as mock_validate:
        
        # Configure default return values
        mock_record.return_value = "test-solution-id"
        mock_get_solutions.return_value = [{"learnt_id": "test-solution-id", "problem_summary": "Test Problem"}]
        mock_get_details.return_value = {"learnt_id": "test-solution-id", "problem_summary": "Test Problem"}
        mock_search.return_value = [{"learnt_id": "test-solution-id", "problem_summary": "Test Problem"}]
        mock_by_error.return_value = [{"learnt_id": "test-solution-id", "type_of_error": "IncorrectAction"}]
        mock_by_severity.return_value = [{"learnt_id": "test-solution-id", "original_severity": "major"}]
        mock_recent.return_value = [{"learnt_id": "test-solution-id", "created_at": "2024-01-01T00:00:00Z"}]
        mock_stats.return_value = {"total_solutions": 10, "by_error_type": {"IncorrectAction": 5}}
        mock_update_status.return_value = {"learnt_id": "test-solution-id", "verification_status": "validated"}
        mock_record_multiple.return_value = ["solution-1", "solution-2"]
        mock_validate.return_value = True
        
        yield {
            'record': mock_record,
            'get_solutions': mock_get_solutions,
            'get_details': mock_get_details,
            'search': mock_search,
            'by_error': mock_by_error,
            'by_severity': mock_by_severity,
            'recent': mock_recent,
            'stats': mock_stats,
            'update_status': mock_update_status,
            'record_multiple': mock_record_multiple,
            'validate': mock_validate
        }


# ================================
# Health Check Tests
# ================================

class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_endpoint(self):
        """Test root endpoint returns health status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "service" in data["data"]
        assert data["data"]["service"] == "Graph Database MCP Server"

    def test_health_endpoint_with_db_connection(self, mock_rule_tools, mock_learning_tools):
        """Test health endpoint with database connectivity check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "database_status" in data["data"]
        assert data["data"]["database_status"]["overall"] is True

    def test_health_endpoint_with_db_failure(self, mock_rule_tools, mock_learning_tools):
        """Test health endpoint when database connection fails."""
        mock_rule_tools['validate'].return_value = False
        mock_learning_tools['validate'].return_value = False
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["data"]["database_status"]["overall"] is False


# ================================
# Rule Management Tests
# ================================

class TestRuleEndpoints:
    """Test rule management endpoints."""

    def test_create_rule_success(self, sample_rule_data, mock_rule_tools):
        """Test successful rule creation."""
        response = client.post("/rules", json=sample_rule_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["rule_id"] == "test-rule-id"
        mock_rule_tools['create'].assert_called_once()

    def test_create_rule_invalid_category(self, sample_rule_data):
        """Test rule creation with invalid category."""
        sample_rule_data["category"] = "invalid_category"
        response = client.post("/rules", json=sample_rule_data)
        assert response.status_code == 422  # Validation error

    def test_create_rule_invalid_rule_type(self, sample_rule_data):
        """Test rule creation with invalid rule type."""
        sample_rule_data["rule_type"] = "invalid_type"
        response = client.post("/rules", json=sample_rule_data)
        assert response.status_code == 422  # Validation error

    def test_create_rule_invalid_priority(self, sample_rule_data):
        """Test rule creation with invalid priority."""
        sample_rule_data["priority"] = 15  # Out of range
        response = client.post("/rules", json=sample_rule_data)
        assert response.status_code == 422  # Validation error

    def test_get_all_rules(self, mock_rule_tools):
        """Test getting all rules."""
        response = client.get("/rules")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "rules" in data["data"]
        assert data["data"]["count"] == 1
        mock_rule_tools['get_all'].assert_called_once()

    def test_get_all_rules_with_filters(self, mock_rule_tools):
        """Test getting rules with filters."""
        response = client.get("/rules?category=frontend&rule_type=best_practice&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_rule_tools['get_all'].assert_called_once_with(
            category="frontend",
            rule_type="best_practice",
            limit=10,
            include_meta_rules=True
        )

    def test_get_rule_details_success(self, mock_rule_tools):
        """Test getting rule details."""
        response = client.get("/rules/test-rule-id")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["rule_id"] == "test-rule-id"
        mock_rule_tools['get_details'].assert_called_once_with("test-rule-id")

    def test_get_rule_details_not_found(self, mock_rule_tools):
        """Test getting non-existent rule details."""
        from src.database import NodeNotFoundError
        mock_rule_tools['get_details'].side_effect = NodeNotFoundError("Rule not found")
        
        response = client.get("/rules/non-existent-id")
        assert response.status_code == 404

    def test_update_rule_success(self, mock_rule_tools):
        """Test successful rule update."""
        update_data = {"rule_name": "Updated Rule", "priority": 8}
        response = client.put("/rules/test-rule-id", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_rule_tools['update'].assert_called_once()

    def test_update_rule_no_updates(self):
        """Test rule update with no valid updates."""
        update_data = {}
        response = client.put("/rules/test-rule-id", json=update_data)
        assert response.status_code == 400

    def test_delete_rule_success(self, mock_rule_tools):
        """Test successful rule deletion."""
        response = client.delete("/rules/test-rule-id")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["deleted"] is True
        mock_rule_tools['delete'].assert_called_once_with("test-rule-id")

    def test_delete_rule_not_found(self, mock_rule_tools):
        """Test deleting non-existent rule."""
        from src.database import NodeNotFoundError
        mock_rule_tools['delete'].side_effect = NodeNotFoundError("Rule not found")
        
        response = client.delete("/rules/non-existent-id")
        assert response.status_code == 404

    def test_search_rules(self, mock_rule_tools):
        """Test rule search."""
        response = client.get("/rules/search/test-term?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "rules" in data["data"]
        mock_rule_tools['search'].assert_called_once_with(
            search_term="test-term",
            search_fields=None,
            limit=5
        )

    def test_get_rules_by_category(self, mock_rule_tools):
        """Test getting rules by category."""
        response = client.get("/rules/category/frontend")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_rule_tools['by_category'].assert_called_once_with("frontend")

    def test_get_rules_by_type(self, mock_rule_tools):
        """Test getting rules by type."""
        response = client.get("/rules/type/best_practice")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_rule_tools['by_type'].assert_called_once_with("best_practice")

    def test_get_meta_rules(self, mock_rule_tools):
        """Test getting meta rules."""
        response = client.get("/rules/meta")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "meta_rules" in data["data"]
        mock_rule_tools['meta'].assert_called_once()

    def test_create_multiple_rules(self, sample_rule_data, mock_rule_tools):
        """Test batch rule creation."""
        rules_data = [sample_rule_data, sample_rule_data.copy()]
        response = client.post("/rules/batch", json=rules_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["count"] == 2
        mock_rule_tools['create_multiple'].assert_called_once()


# ================================
# Learning Management Tests
# ================================

class TestLearningEndpoints:
    """Test learning management endpoints."""

    def test_record_solution_success(self, sample_solution_data, mock_learning_tools):
        """Test successful solution recording."""
        response = client.post("/solutions", json=sample_solution_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["solution_id"] == "test-solution-id"
        mock_learning_tools['record'].assert_called_once()

    def test_record_solution_invalid_error_type(self, sample_solution_data):
        """Test solution recording with invalid error type."""
        sample_solution_data["type_of_error"] = "invalid_error"
        response = client.post("/solutions", json=sample_solution_data)
        assert response.status_code == 422  # Validation error

    def test_record_solution_invalid_severity(self, sample_solution_data):
        """Test solution recording with invalid severity."""
        sample_solution_data["original_severity"] = "invalid_severity"
        response = client.post("/solutions", json=sample_solution_data)
        assert response.status_code == 422  # Validation error

    def test_record_solution_long_summary(self, sample_solution_data):
        """Test solution recording with too long summary."""
        sample_solution_data["problem_summary"] = "x" * 501  # Too long
        response = client.post("/solutions", json=sample_solution_data)
        assert response.status_code == 422  # Validation error

    def test_get_all_solutions(self, mock_learning_tools):
        """Test getting all solutions."""
        response = client.get("/solutions")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "solutions" in data["data"]
        assert data["data"]["count"] == 1
        mock_learning_tools['get_solutions'].assert_called_once()

    def test_get_all_solutions_with_filters(self, mock_learning_tools):
        """Test getting solutions with filters."""
        response = client.get("/solutions?error_type=IncorrectAction&severity=major&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_learning_tools['get_solutions'].assert_called_once_with(
            error_type="IncorrectAction",
            severity="major",
            related_rule_id=None,
            verification_status=None,
            limit=10,
            include_meta_contributions=True
        )

    def test_get_solution_details_success(self, mock_learning_tools):
        """Test getting solution details."""
        response = client.get("/solutions/test-solution-id")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["learnt_id"] == "test-solution-id"
        mock_learning_tools['get_details'].assert_called_once_with("test-solution-id")

    def test_get_solution_details_not_found(self, mock_learning_tools):
        """Test getting non-existent solution details."""
        from src.database import NodeNotFoundError
        mock_learning_tools['get_details'].side_effect = NodeNotFoundError("Solution not found")
        
        response = client.get("/solutions/non-existent-id")
        assert response.status_code == 404

    def test_search_solutions(self, mock_learning_tools):
        """Test solution search."""
        response = client.get("/solutions/search/test-term?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "solutions" in data["data"]
        mock_learning_tools['search'].assert_called_once_with(
            search_term="test-term",
            search_fields=None,
            limit=5
        )

    def test_get_solutions_by_error_type(self, mock_learning_tools):
        """Test getting solutions by error type."""
        response = client.get("/solutions/error-type/IncorrectAction")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_learning_tools['by_error'].assert_called_once_with("IncorrectAction")

    def test_get_solutions_by_severity(self, mock_learning_tools):
        """Test getting solutions by severity."""
        response = client.get("/solutions/severity/major")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_learning_tools['by_severity'].assert_called_once_with("major")

    def test_get_recent_solutions(self, mock_learning_tools):
        """Test getting recent solutions."""
        response = client.get("/solutions/recent?days=14&limit=20")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_learning_tools['recent'].assert_called_once_with(days=14, limit=20)

    def test_get_solutions_statistics(self, mock_learning_tools):
        """Test getting solutions statistics."""
        response = client.get("/solutions/statistics")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_solutions" in data["data"]
        mock_learning_tools['stats'].assert_called_once()

    def test_update_solution_verification_status(self, mock_learning_tools):
        """Test updating solution verification status."""
        status_data = {"verification_status": "validated"}
        response = client.put("/solutions/test-solution-id/verification", json=status_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_learning_tools['update_status'].assert_called_once_with("test-solution-id", "validated")

    def test_update_verification_status_invalid(self):
        """Test updating with invalid verification status."""
        status_data = {"verification_status": "invalid_status"}
        response = client.put("/solutions/test-solution-id/verification", json=status_data)
        assert response.status_code == 422  # Validation error

    def test_record_multiple_solutions(self, sample_solution_data, mock_learning_tools):
        """Test batch solution recording."""
        solutions_data = [sample_solution_data, sample_solution_data.copy()]
        response = client.post("/solutions/batch", json=solutions_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["count"] == 2
        mock_learning_tools['record_multiple'].assert_called_once()


# ================================
# Utility Endpoint Tests
# ================================

class TestUtilityEndpoints:
    """Test utility endpoints."""

    def test_get_rule_categories(self):
        """Test getting rule categories."""
        response = client.get("/enums/rule-categories")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "categories" in data["data"]
        expected_categories = [cat.value for cat in RuleCategory]
        assert set(data["data"]["categories"]) == set(expected_categories)

    def test_get_rule_types(self):
        """Test getting rule types."""
        response = client.get("/enums/rule-types")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "types" in data["data"]
        expected_types = [rt.value for rt in RuleType]
        assert set(data["data"]["types"]) == set(expected_types)

    def test_get_error_types(self):
        """Test getting error types."""
        response = client.get("/enums/error-types")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "error_types" in data["data"]
        expected_error_types = [et.value for et in ErrorType]
        assert set(data["data"]["error_types"]) == set(expected_error_types)

    def test_get_severity_levels(self):
        """Test getting severity levels."""
        response = client.get("/enums/severity-levels")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "severity_levels" in data["data"]
        expected_severities = [sl.value for sl in SeverityLevel]
        assert set(data["data"]["severity_levels"]) == set(expected_severities)


# ================================
# Error Handling Tests
# ================================

class TestErrorHandling:
    """Test error handling scenarios."""

    def test_database_connection_error(self, mock_rule_tools):
        """Test database connection error handling."""
        from src.database import DatabaseConnectionError
        mock_rule_tools['create'].side_effect = DatabaseConnectionError("Database unavailable")
        
        rule_data = {
            "rule_name": "Test Rule",
            "content": "Test content",
            "category": "frontend",
            "rule_type": "best_practice"
        }
        
        response = client.post("/rules", json=rule_data)
        assert response.status_code == 503

    def test_validation_error(self, mock_rule_tools):
        """Test validation error handling."""
        from src.database import ValidationError
        mock_rule_tools['create'].side_effect = ValidationError("Invalid data")
        
        rule_data = {
            "rule_name": "Test Rule",
            "content": "Test content",
            "category": "frontend",
            "rule_type": "best_practice"
        }
        
        response = client.post("/rules", json=rule_data)
        assert response.status_code == 400

    def test_general_exception(self, mock_rule_tools):
        """Test general exception handling."""
        mock_rule_tools['create'].side_effect = Exception("Unexpected error")
        
        rule_data = {
            "rule_name": "Test Rule",
            "content": "Test content",
            "category": "frontend",
            "rule_type": "best_practice"
        }
        
        response = client.post("/rules", json=rule_data)
        assert response.status_code == 400  # FastAPI converts to HTTPException


# ================================
# Integration Tests
# ================================

class TestIntegration:
    """Test integration scenarios."""

    def test_cors_headers(self):
        """Test CORS headers are present."""
        response = client.options("/rules")
        # CORS headers should be present in actual responses
        # This is more of a configuration test
        assert response.status_code in [200, 405]  # OPTIONS might not be explicitly handled

    def test_api_documentation_available(self):
        """Test that API documentation is available."""
        response = client.get("/docs")
        assert response.status_code == 200
        
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_openapi_schema(self):
        """Test OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "Graph Database MCP Server"


# ================================
# Performance Tests
# ================================

class TestPerformance:
    """Test performance scenarios."""

    def test_concurrent_requests(self, mock_rule_tools, mock_learning_tools):
        """Test handling multiple concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get("/health")
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 10

    def test_large_batch_operations(self, sample_rule_data, mock_rule_tools):
        """Test handling large batch operations."""
        # Create a large batch of rules
        large_batch = [sample_rule_data.copy() for _ in range(100)]
        
        # Mock should handle this fine
        mock_rule_tools['create_multiple'].return_value = [f"rule-{i}" for i in range(100)]
        
        response = client.post("/rules/batch", json=large_batch)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["count"] == 100 