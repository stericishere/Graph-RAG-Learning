#!/usr/bin/env python3
"""
Learning Management Tools for Final Minimal Lean Graph Database MCP.

This module provides comprehensive learning management functionality including
recording validated solutions, retrieving learnt experiences, and detailed
solution analysis with support for both Neo4j and NetworkX database backends.
"""

import os
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Import database components
from ..database import GraphDatabase, DatabaseConnectionError, NodeNotFoundError, ValidationError
from ..models.learnt import Learnt, ErrorType, SeverityLevel
from ..config import get_database


# ================================
# Core Learning Management Functions
# ================================

async def record_validated_solution(
    type_of_error: str,
    problem_summary: str,
    problematic_input_segment: str,
    problematic_ai_output_segment: str,
    inferred_original_cause: str,
    original_severity: str,
    validated_solution_description: str,
    solution_implemented_notes: Optional[str] = None,
    related_rule_ids: Optional[List[str]] = None,
    created_by: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """
    Record a validated solution to a problem in the graph database.
    
    Args:
        type_of_error: Type of error encountered (must be valid ErrorType)
        problem_summary: Concise problem summary (1-500 characters)
        problematic_input_segment: User input that caused the problem
        problematic_ai_output_segment: Incorrect AI output that caused the issue
        inferred_original_cause: AI's self-diagnosis of the root cause
        original_severity: Severity level (critical, major, minor, low)
        validated_solution_description: Detailed description of the proven solution
        solution_implemented_notes: Optional implementation details
        related_rule_ids: Optional list of related rule IDs
        created_by: Optional creator identifier
        tags: Optional list of tags for categorization
        metadata: Optional additional metadata
        **kwargs: Additional arguments (ignored for flexibility)
        
    Returns:
        str: The ID of the created learnt solution
        
    Raises:
        ValidationError: If solution data is invalid
        DatabaseConnectionError: If database is not accessible
        ValueError: If required parameters are missing or invalid
    """
    # Input validation for required parameters
    if not type_of_error or not type_of_error.strip():
        raise ValueError("type_of_error is required and cannot be empty")
    
    if not problem_summary or not problem_summary.strip():
        raise ValueError("problem_summary is required and cannot be empty")
    
    if not problematic_input_segment or not problematic_input_segment.strip():
        raise ValueError("problematic_input_segment is required and cannot be empty")
    
    if not problematic_ai_output_segment or not problematic_ai_output_segment.strip():
        raise ValueError("problematic_ai_output_segment is required and cannot be empty")
    
    if not inferred_original_cause or not inferred_original_cause.strip():
        raise ValueError("inferred_original_cause is required and cannot be empty")
    
    if not original_severity or not original_severity.strip():
        raise ValueError("original_severity is required and cannot be empty")
    
    if not validated_solution_description or not validated_solution_description.strip():
        raise ValueError("validated_solution_description is required and cannot be empty")
    
    # Validate error type
    try:
        error_type_enum = ErrorType(type_of_error)
    except ValueError:
        valid_error_types = [et.value for et in ErrorType]
        raise ValueError(f"Invalid type_of_error '{type_of_error}'. Valid options: {valid_error_types}")
    
    # Validate severity level
    try:
        severity_enum = SeverityLevel(original_severity.lower())
    except ValueError:
        valid_severities = [sl.value for sl in SeverityLevel]
        raise ValueError(f"Invalid original_severity '{original_severity}'. Valid options: {valid_severities}")
    
    # Validate problem summary length
    if len(problem_summary.strip()) > 500:
        raise ValueError("problem_summary must be 500 characters or less")
    
    # Create Learnt model instance
    try:
        learnt = Learnt(
            type_of_error=error_type_enum,
            problem_summary=problem_summary.strip(),
            problematic_input_segment=problematic_input_segment.strip(),
            problematic_ai_output_segment=problematic_ai_output_segment.strip(),
            inferred_original_cause=inferred_original_cause.strip(),
            original_severity=severity_enum,
            validated_solution_description=validated_solution_description.strip(),
            solution_implemented_notes=solution_implemented_notes,
            related_rule_ids=related_rule_ids or [],
            created_by=created_by,
            tags=tags or [],
            metadata=metadata or {}
        )
    except Exception as e:
        raise ValidationError(f"Failed to create learnt model: {str(e)}")
    
    # Store in database
    db = await get_database()
    
    try:
        # Convert learnt to properties for database storage
        properties = learnt.to_dict()
        
        # Create node in database
        node_id = await db.create_node(
            label="Learnt",
            properties=properties,
            node_id=learnt.learnt_id
        )
        
        return node_id
        
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to record validated solution in database: {str(e)}")
    
    finally:
        await db.disconnect()


async def get_learnt_solutions(
    error_type: Optional[str] = None,
    severity: Optional[str] = None,
    related_rule_id: Optional[str] = None,
    verification_status: Optional[str] = None,
    limit: Optional[int] = None,
    include_meta_contributions: bool = True
) -> List[Dict[str, Any]]:
    """
    Retrieve learnt solutions with optional filtering.
    
    Args:
        error_type: Optional error type filter (IncorrectAction, Misunderstanding, etc.)
        severity: Optional severity filter (critical, major, minor, low)
        related_rule_id: Optional filter by related rule ID
        verification_status: Optional verification status filter (validated, pending, rejected)
        limit: Optional limit on number of results
        include_meta_contributions: Whether to include meta-rule contributions in results
        
    Returns:
        List[Dict[str, Any]]: List of learnt solution data dictionaries
        
    Raises:
        DatabaseConnectionError: If database is not accessible
        ValueError: If filter parameters are invalid
    """
    # Validate filters
    filters = {}
    
    if error_type:
        try:
            error_type_enum = ErrorType(error_type)
            filters["type_of_error"] = error_type_enum.value
        except ValueError:
            valid_error_types = [et.value for et in ErrorType]
            raise ValueError(f"Invalid error_type '{error_type}'. Valid options: {valid_error_types}")
    
    if severity:
        try:
            severity_enum = SeverityLevel(severity.lower())
            filters["original_severity"] = severity_enum.value
        except ValueError:
            valid_severities = [sl.value for sl in SeverityLevel]
            raise ValueError(f"Invalid severity '{severity}'. Valid options: {valid_severities}")
    
    if verification_status:
        valid_statuses = ["validated", "pending", "rejected"]
        if verification_status not in valid_statuses:
            raise ValueError(f"Invalid verification_status '{verification_status}'. Valid options: {valid_statuses}")
        filters["verification_status"] = verification_status
    
    if limit is not None and (not isinstance(limit, int) or limit <= 0):
        raise ValueError("limit must be a positive integer")
    
    db = await get_database()
    
    try:
        # Get all learnt solutions with filters
        learnt_solutions = await db.get_nodes_by_label("Learnt", filters=filters, limit=limit)
        
        # Filter by related_rule_id if specified (this requires checking the list field)
        if related_rule_id:
            filtered_solutions = []
            for solution in learnt_solutions:
                related_rules = solution.get("related_rule_ids", [])
                if related_rule_id in related_rules:
                    filtered_solutions.append(solution)
            learnt_solutions = filtered_solutions
        
        # Filter out meta-rule contributions if requested
        if not include_meta_contributions:
            learnt_solutions = [
                solution for solution in learnt_solutions 
                if not solution.get("contributed_to_meta_rule", False)
            ]
        
        # Sort by timestamp (most recent first) then by severity
        def sort_key(solution):
            timestamp = solution.get("timestamp_recorded", "")
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except:
                    timestamp = datetime.min
            
            severity = solution.get("original_severity", "low")
            severity_order = {"critical": 4, "major": 3, "minor": 2, "low": 1}
            severity_score = severity_order.get(severity, 1)
            
            return (-timestamp.timestamp() if isinstance(timestamp, datetime) else 0, -severity_score)
        
        learnt_solutions.sort(key=sort_key)
        
        return learnt_solutions
        
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to retrieve learnt solutions: {str(e)}")
    
    finally:
        await db.disconnect()


async def get_solution_details(learnt_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific learnt solution.
    
    Args:
        learnt_id: The ID of the learnt solution to retrieve
        
    Returns:
        Dict[str, Any]: Complete learnt solution data including metadata and relationships
        
    Raises:
        NodeNotFoundError: If learnt solution doesn't exist
        DatabaseConnectionError: If database is not accessible
        ValueError: If learnt_id is invalid
    """
    # Input validation
    if not learnt_id or not learnt_id.strip():
        raise ValueError("learnt_id is required and cannot be empty")
    
    db = await get_database()
    
    try:
        # Get learnt solution data
        learnt_data = await db.get_node(learnt_id)
        if not learnt_data:
            raise NodeNotFoundError(f"Learnt solution with ID '{learnt_id}' not found")
        
        # Get relationships for additional context
        relationships = await db.get_relationships(learnt_id)
        
        # Enhance learnt data with relationship info
        enhanced_data = {
            **learnt_data,
            "relationships": relationships,
            "relationship_count": len(relationships)
        }
        
        # Add computed fields
        timestamp_recorded = learnt_data.get("timestamp_recorded")
        if timestamp_recorded:
            if isinstance(timestamp_recorded, str):
                try:
                    timestamp_recorded = datetime.fromisoformat(timestamp_recorded)
                except:
                    timestamp_recorded = None
            
            if timestamp_recorded:
                enhanced_data["days_since_recorded"] = (datetime.utcnow() - timestamp_recorded).days
        
        # Add analysis of related rules
        related_rule_ids = learnt_data.get("related_rule_ids", [])
        enhanced_data["related_rule_count"] = len(related_rule_ids)
        
        # Add meta-rule contribution status
        if learnt_data.get("contributed_to_meta_rule", False):
            enhanced_data["meta_rule_contribution_status"] = "contributed"
            enhanced_data["meta_rule_contribution_summary"] = learnt_data.get("meta_rule_contribution", "")
        else:
            enhanced_data["meta_rule_contribution_status"] = "pending"
        
        # Add severity analysis
        severity = learnt_data.get("original_severity", "low")
        severity_scores = {"critical": 100, "major": 75, "minor": 50, "low": 25}
        enhanced_data["severity_score"] = severity_scores.get(severity, 25)
        
        # Add learning summary
        enhanced_data["learning_summary"] = {
            "problem_type": learnt_data.get("type_of_error", ""),
            "severity": severity,
            "solution_verified": learnt_data.get("verification_status", "") == "validated",
            "has_implementation_notes": bool(learnt_data.get("solution_implemented_notes")),
            "tag_count": len(learnt_data.get("tags", []))
        }
        
        return enhanced_data
        
    except NodeNotFoundError:
        raise
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to retrieve solution details: {str(e)}")
    
    finally:
        await db.disconnect()


# ================================
# Additional Utility Functions
# ================================

async def search_learnt_solutions(
    search_term: str,
    search_fields: Optional[List[str]] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Search for learnt solutions containing specific terms.
    
    Args:
        search_term: Term to search for
        search_fields: Fields to search in (default: ["problem_summary", "validated_solution_description", "tags"])
        limit: Optional limit on number of results
        
    Returns:
        List[Dict[str, Any]]: List of matching learnt solutions
        
    Raises:
        DatabaseConnectionError: If database is not accessible
        ValueError: If search parameters are invalid
    """
    if not search_term or not search_term.strip():
        raise ValueError("search_term is required and cannot be empty")
    
    if search_fields is None:
        search_fields = ["problem_summary", "validated_solution_description", "tags", "inferred_original_cause"]
    
    if limit is not None and (not isinstance(limit, int) or limit <= 0):
        raise ValueError("limit must be a positive integer")
    
    # Get all learnt solutions and filter in memory
    all_solutions = await get_learnt_solutions(limit=None)
    
    search_term_lower = search_term.lower().strip()
    matching_solutions = []
    
    for solution in all_solutions:
        # Check each specified field
        for field in search_fields:
            field_value = solution.get(field, "")
            
            # Handle different field types
            if isinstance(field_value, str):
                if search_term_lower in field_value.lower():
                    matching_solutions.append(solution)
                    break
            elif isinstance(field_value, list):
                # For tags and other list fields
                if any(search_term_lower in str(item).lower() for item in field_value):
                    matching_solutions.append(solution)
                    break
    
    # Apply limit if specified
    if limit:
        matching_solutions = matching_solutions[:limit]
    
    return matching_solutions


async def get_solutions_by_error_type(error_type: str) -> List[Dict[str, Any]]:
    """
    Get all learnt solutions for a specific error type.
    
    Args:
        error_type: The error type to filter by
        
    Returns:
        List[Dict[str, Any]]: List of solutions for the error type
        
    Raises:
        DatabaseConnectionError: If database is not accessible
        ValueError: If error_type is invalid
    """
    return await get_learnt_solutions(error_type=error_type)


async def get_solutions_by_severity(severity: str) -> List[Dict[str, Any]]:
    """
    Get all learnt solutions for a specific severity level.
    
    Args:
        severity: The severity level to filter by
        
    Returns:
        List[Dict[str, Any]]: List of solutions for the severity level
        
    Raises:
        DatabaseConnectionError: If database is not accessible
        ValueError: If severity is invalid
    """
    return await get_learnt_solutions(severity=severity)


async def get_recent_solutions(days: int = 7, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get recently recorded learnt solutions.
    
    Args:
        days: Number of days to look back (default: 7)
        limit: Optional limit on number of results
        
    Returns:
        List[Dict[str, Any]]: List of recent solutions
        
    Raises:
        DatabaseConnectionError: If database is not accessible
        ValueError: If days parameter is invalid
    """
    if not isinstance(days, int) or days <= 0:
        raise ValueError("days must be a positive integer")
    
    # Get all solutions and filter by date
    all_solutions = await get_learnt_solutions(limit=None)
    
    cutoff_date = datetime.utcnow().timestamp() - (days * 24 * 60 * 60)
    recent_solutions = []
    
    for solution in all_solutions:
        timestamp = solution.get("timestamp_recorded", "")
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
                if timestamp.timestamp() >= cutoff_date:
                    recent_solutions.append(solution)
            except:
                continue
    
    # Apply limit if specified
    if limit:
        recent_solutions = recent_solutions[:limit]
    
    return recent_solutions


async def get_solutions_statistics() -> Dict[str, Any]:
    """
    Get statistics about learnt solutions in the database.
    
    Returns:
        Dict[str, Any]: Statistics including counts by error type, severity, etc.
        
    Raises:
        DatabaseConnectionError: If database is not accessible
    """
    all_solutions = await get_learnt_solutions(limit=None)
    
    stats = {
        "total_solutions": len(all_solutions),
        "by_error_type": {},
        "by_severity": {},
        "by_verification_status": {},
        "meta_rule_contributions": 0,
        "recent_solutions_7_days": 0,
        "recent_solutions_30_days": 0
    }
    
    cutoff_7_days = datetime.utcnow().timestamp() - (7 * 24 * 60 * 60)
    cutoff_30_days = datetime.utcnow().timestamp() - (30 * 24 * 60 * 60)
    
    for solution in all_solutions:
        # Count by error type
        error_type = solution.get("type_of_error", "Other")
        stats["by_error_type"][error_type] = stats["by_error_type"].get(error_type, 0) + 1
        
        # Count by severity
        severity = solution.get("original_severity", "low")
        stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1
        
        # Count by verification status
        verification = solution.get("verification_status", "validated")
        stats["by_verification_status"][verification] = stats["by_verification_status"].get(verification, 0) + 1
        
        # Count meta-rule contributions
        if solution.get("contributed_to_meta_rule", False):
            stats["meta_rule_contributions"] += 1
        
        # Count recent solutions
        timestamp = solution.get("timestamp_recorded", "")
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
                timestamp_val = timestamp.timestamp()
                
                if timestamp_val >= cutoff_7_days:
                    stats["recent_solutions_7_days"] += 1
                
                if timestamp_val >= cutoff_30_days:
                    stats["recent_solutions_30_days"] += 1
            except:
                continue
    
    return stats


async def update_solution_verification_status(
    learnt_id: str,
    verification_status: str
) -> Dict[str, Any]:
    """
    Update the verification status of a learnt solution.
    
    Args:
        learnt_id: The ID of the learnt solution to update
        verification_status: New verification status (validated, pending, rejected)
        
    Returns:
        Dict[str, Any]: Updated learnt solution data
        
    Raises:
        NodeNotFoundError: If learnt solution doesn't exist
        ValidationError: If verification status is invalid
        DatabaseConnectionError: If database is not accessible
        ValueError: If parameters are invalid
    """
    # Input validation
    if not learnt_id or not learnt_id.strip():
        raise ValueError("learnt_id is required and cannot be empty")
    
    valid_statuses = ["validated", "pending", "rejected"]
    if verification_status not in valid_statuses:
        raise ValueError(f"Invalid verification_status '{verification_status}'. Valid options: {valid_statuses}")
    
    db = await get_database()
    
    try:
        # Get existing learnt solution
        existing_data = await db.get_node(learnt_id)
        if not existing_data:
            raise NodeNotFoundError(f"Learnt solution with ID '{learnt_id}' not found")
        
        # Update verification status
        updates = {"verification_status": verification_status}
        
        # Update in database
        success = await db.update_node(learnt_id, updates)
        if not success:
            raise NodeNotFoundError(f"Failed to update learnt solution with ID '{learnt_id}'")
        
        # Return updated data
        updated_data = {**existing_data, **updates}
        return updated_data
        
    except (NodeNotFoundError, ValidationError):
        raise
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to update verification status: {str(e)}")
    
    finally:
        await db.disconnect()


async def validate_database_connection() -> bool:
    """
    Validate that the database connection is working.
    
    Returns:
        bool: True if database is accessible and healthy
        
    Raises:
        DatabaseConnectionError: If database is not accessible
    """
    try:
        db = await get_database()
        health_check = await db.health_check()
        await db.disconnect()
        return health_check
    except Exception as e:
        raise DatabaseConnectionError(f"Database connection validation failed: {str(e)}")


# ================================
# Batch Operations
# ================================

async def record_multiple_solutions(solutions_data: List[Dict[str, Any]]) -> List[str]:
    """
    Record multiple validated solutions in a single operation.
    
    Args:
        solutions_data: List of solution data dictionaries
        
    Returns:
        List[str]: List of created learnt solution IDs
        
    Raises:
        ValidationError: If any solution data is invalid
        DatabaseConnectionError: If database is not accessible
    """
    if not solutions_data or not isinstance(solutions_data, list):
        raise ValueError("solutions_data must be a non-empty list")
    
    created_ids = []
    errors = []
    
    for i, solution_data in enumerate(solutions_data):
        try:
            # Extract required fields
            type_of_error = solution_data.get("type_of_error")
            problem_summary = solution_data.get("problem_summary")
            problematic_input_segment = solution_data.get("problematic_input_segment")
            problematic_ai_output_segment = solution_data.get("problematic_ai_output_segment")
            inferred_original_cause = solution_data.get("inferred_original_cause")
            original_severity = solution_data.get("original_severity")
            validated_solution_description = solution_data.get("validated_solution_description")
            
            # Extract optional fields
            solution_implemented_notes = solution_data.get("solution_implemented_notes")
            related_rule_ids = solution_data.get("related_rule_ids")
            created_by = solution_data.get("created_by")
            tags = solution_data.get("tags")
            metadata = solution_data.get("metadata")
            
            # Record solution
            solution_id = await record_validated_solution(
                type_of_error=type_of_error,
                problem_summary=problem_summary,
                problematic_input_segment=problematic_input_segment,
                problematic_ai_output_segment=problematic_ai_output_segment,
                inferred_original_cause=inferred_original_cause,
                original_severity=original_severity,
                validated_solution_description=validated_solution_description,
                solution_implemented_notes=solution_implemented_notes,
                related_rule_ids=related_rule_ids,
                created_by=created_by,
                tags=tags,
                metadata=metadata
            )
            
            created_ids.append(solution_id)
            
        except Exception as e:
            errors.append(f"Solution {i}: {str(e)}")
    
    if errors:
        # Note: We don't clean up created solutions here as they might be valid
        # and the error could be in a later solution
        raise ValidationError(f"Failed to create some solutions: {'; '.join(errors)}")
    
    return created_ids


# ================================
# Export Functions
# ================================

__all__ = [
    # Core CRUD operations
    "record_validated_solution",
    "get_learnt_solutions",
    "get_solution_details",
    
    # Search and filtering
    "search_learnt_solutions",
    "get_solutions_by_error_type",
    "get_solutions_by_severity",
    "get_recent_solutions",
    
    # Statistics and analysis
    "get_solutions_statistics",
    
    # Updates
    "update_solution_verification_status",
    
    # Utilities
    "validate_database_connection",
    "record_multiple_solutions"
] 