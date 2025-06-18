#!/usr/bin/env python3
"""
Rule Management Tools for Final Minimal Lean Graph Database MCP.

This module provides comprehensive rule management functionality including
create, read, update, delete operations with support for both Neo4j and NetworkX
database backends.
"""

import os
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Import database components
from ..database import GraphDatabase, DatabaseConnectionError, NodeNotFoundError, ValidationError
from ..models.rule import Rule, RuleCategory, RuleType
from ..config import get_database


# ================================
# Core Rule Management Functions
# ================================

async def create_rule(
    rule_name: str, 
    content: str, 
    category: str, 
    rule_type: str,
    priority: int = 5,
    tags: Optional[List[str]] = None,
    created_by: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Create a new rule in the graph database.
    
    Args:
        rule_name: Human-readable name for the rule
        content: The actual rule content or guidance
        category: Rule category (frontend, backend, database, etc.)
        rule_type: Type of rule (best_practice, anti_pattern, etc.)
        priority: Priority level (1=lowest, 10=highest), default 5
        tags: Optional list of tags for organization
        created_by: Optional creator identifier
        metadata: Optional additional metadata
        
    Returns:
        str: The ID of the created rule
        
    Raises:
        ValidationError: If rule data is invalid
        DatabaseConnectionError: If database is not accessible
        ValueError: If required parameters are missing or invalid
    """
    # Input validation
    if not rule_name or not rule_name.strip():
        raise ValueError("rule_name is required and cannot be empty")
    
    if not content or not content.strip():
        raise ValueError("content is required and cannot be empty")
    
    # Validate category
    try:
        category_enum = RuleCategory(category.lower())
    except ValueError:
        valid_categories = [cat.value for cat in RuleCategory]
        raise ValueError(f"Invalid category '{category}'. Valid options: {valid_categories}")
    
    # Validate rule_type
    try:
        rule_type_enum = RuleType(rule_type.lower())
    except ValueError:
        valid_types = [rt.value for rt in RuleType]
        raise ValueError(f"Invalid rule_type '{rule_type}'. Valid options: {valid_types}")
    
    # Validate priority
    if not isinstance(priority, int) or priority < 1 or priority > 10:
        raise ValueError("priority must be an integer between 1 and 10")
    
    # Create Rule model instance
    try:
        rule = Rule(
            rule_name=rule_name.strip(),
            content=content.strip(),
            category=category_enum,
            rule_type=rule_type_enum,
            priority=priority,
            tags=tags or [],
            created_by=created_by,
            metadata=metadata or {}
        )
    except Exception as e:
        raise ValidationError(f"Failed to create rule model: {str(e)}")
    
    # Store in database
    db = await get_database()
    
    try:
        # Convert rule to properties for database storage
        properties = rule.to_dict()
        
        # Create node in database
        node_id = await db.create_node(
            label="Rule",
            properties=properties,
            node_id=rule.rule_id
        )
        
        return node_id
        
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to create rule in database: {str(e)}")
    
    finally:
        await db.disconnect()


async def update_rule(rule_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing rule with new information.
    
    Args:
        rule_id: The ID of the rule to update
        updates: Dictionary of fields to update
        
    Returns:
        Dict[str, Any]: Updated rule data
        
    Raises:
        NodeNotFoundError: If rule doesn't exist
        ValidationError: If update data is invalid
        DatabaseConnectionError: If database is not accessible
        ValueError: If rule_id is invalid or updates are empty
    """
    # Input validation
    if not rule_id or not rule_id.strip():
        raise ValueError("rule_id is required and cannot be empty")
    
    if not updates or not isinstance(updates, dict):
        raise ValueError("updates must be a non-empty dictionary")
    
    # Remove read-only fields from updates
    read_only_fields = {"rule_id", "created_at", "is_meta_rule"}
    for field in read_only_fields:
        if field in updates:
            del updates[field]
    
    if not updates:
        raise ValueError("No valid fields to update after filtering read-only fields")
    
    db = await get_database()
    
    try:
        # Get existing rule
        existing_data = await db.get_node(rule_id)
        if not existing_data:
            raise NodeNotFoundError(f"Rule with ID '{rule_id}' not found")
        
        # Create updated Rule instance for validation
        try:
            # Merge existing data with updates
            updated_data = {**existing_data, **updates}
            
            # Convert datetime strings back to datetime objects if needed
            if "created_at" in updated_data and isinstance(updated_data["created_at"], str):
                updated_data["created_at"] = datetime.fromisoformat(updated_data["created_at"])
            
            if "last_updated" in updated_data and isinstance(updated_data["last_updated"], str):
                updated_data["last_updated"] = datetime.fromisoformat(updated_data["last_updated"])
            
            # Validate with Rule model
            updated_rule = Rule.from_dict(updated_data)
            
        except Exception as e:
            raise ValidationError(f"Invalid update data: {str(e)}")
        
        # Update in database
        success = await db.update_node(rule_id, updated_rule.to_dict())
        if not success:
            raise NodeNotFoundError(f"Failed to update rule with ID '{rule_id}'")
        
        # Return updated rule data
        return updated_rule.to_dict()
        
    except (NodeNotFoundError, ValidationError):
        raise
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to update rule: {str(e)}")
    
    finally:
        await db.disconnect()


async def delete_rule(rule_id: str) -> bool:
    """
    Delete a rule from the graph database.
    
    Args:
        rule_id: The ID of the rule to delete
        
    Returns:
        bool: True if deletion successful, False if rule not found
        
    Raises:
        DatabaseConnectionError: If database is not accessible
        ValueError: If rule_id is invalid
    """
    # Input validation
    if not rule_id or not rule_id.strip():
        raise ValueError("rule_id is required and cannot be empty")
    
    db = await get_database()
    
    try:
        # Check if rule exists first
        existing_rule = await db.get_node(rule_id)
        if not existing_rule:
            return False
        
        # Delete the rule node (this also deletes connected relationships)
        success = await db.delete_node(rule_id)
        return success
        
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to delete rule: {str(e)}")
    
    finally:
        await db.disconnect()


async def get_all_rules(
    category: Optional[str] = None, 
    rule_type: Optional[str] = None,
    limit: Optional[int] = None,
    include_meta_rules: bool = True
) -> List[Dict[str, Any]]:
    """
    Retrieve all rules, optionally filtered by category and/or type.
    
    Args:
        category: Optional category filter (frontend, backend, etc.)
        rule_type: Optional type filter (best_practice, anti_pattern, etc.)
        limit: Optional limit on number of results
        include_meta_rules: Whether to include meta-rules in results
        
    Returns:
        List[Dict[str, Any]]: List of rule data dictionaries
        
    Raises:
        DatabaseConnectionError: If database is not accessible
        ValueError: If filter parameters are invalid
    """
    # Validate filters
    filters = {}
    
    if category:
        try:
            category_enum = RuleCategory(category.lower())
            filters["category"] = category_enum.value
        except ValueError:
            valid_categories = [cat.value for cat in RuleCategory]
            raise ValueError(f"Invalid category '{category}'. Valid options: {valid_categories}")
    
    if rule_type:
        try:
            rule_type_enum = RuleType(rule_type.lower())
            filters["rule_type"] = rule_type_enum.value
        except ValueError:
            valid_types = [rt.value for rt in RuleType]
            raise ValueError(f"Invalid rule_type '{rule_type}'. Valid options: {valid_types}")
    
    if limit is not None and (not isinstance(limit, int) or limit <= 0):
        raise ValueError("limit must be a positive integer")
    
    db = await get_database()
    
    try:
        # Get all rules with filters
        rules = await db.get_nodes_by_label("Rule", filters=filters, limit=limit)
        
        # Filter out meta-rules if requested
        if not include_meta_rules:
            rules = [rule for rule in rules if not rule.get("is_meta_rule", False)]
        
        # Sort by priority (descending) then by created_at (descending)
        def sort_key(rule):
            priority = rule.get("priority", 5)
            created_at = rule.get("created_at", "")
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except:
                    created_at = datetime.min
            return (-priority, -created_at.timestamp() if isinstance(created_at, datetime) else 0)
        
        rules.sort(key=sort_key)
        
        return rules
        
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to retrieve rules: {str(e)}")
    
    finally:
        await db.disconnect()


async def get_rule_details(rule_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific rule.
    
    Args:
        rule_id: The ID of the rule to retrieve
        
    Returns:
        Dict[str, Any]: Complete rule data including metadata and relationships
        
    Raises:
        NodeNotFoundError: If rule doesn't exist
        DatabaseConnectionError: If database is not accessible
        ValueError: If rule_id is invalid
    """
    # Input validation
    if not rule_id or not rule_id.strip():
        raise ValueError("rule_id is required and cannot be empty")
    
    db = await get_database()
    
    try:
        # Get rule data
        rule_data = await db.get_node(rule_id)
        if not rule_data:
            raise NodeNotFoundError(f"Rule with ID '{rule_id}' not found")
        
        # Get relationships for additional context
        relationships = await db.get_relationships(rule_id)
        
        # Enhance rule data with relationship info
        enhanced_data = {
            **rule_data,
            "relationships": relationships,
            "relationship_count": len(relationships)
        }
        
        # Add computed fields for meta-rules
        if rule_data.get("is_meta_rule", False):
            source_learnt_ids = rule_data.get("source_learnt_ids", [])
            enhanced_data["source_learnt_count"] = len(source_learnt_ids)
            
            # Get last update info
            last_updated = rule_data.get("last_updated")
            if last_updated:
                if isinstance(last_updated, str):
                    try:
                        last_updated = datetime.fromisoformat(last_updated)
                    except:
                        last_updated = None
                
                if last_updated:
                    enhanced_data["days_since_last_update"] = (datetime.utcnow() - last_updated).days
        
        return enhanced_data
        
    except NodeNotFoundError:
        raise
    except Exception as e:
        raise DatabaseConnectionError(f"Failed to retrieve rule details: {str(e)}")
    
    finally:
        await db.disconnect()


# ================================
# Additional Utility Functions
# ================================

async def search_rules(
    search_term: str,
    search_fields: Optional[List[str]] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Search for rules containing specific terms.
    
    Args:
        search_term: Term to search for
        search_fields: Fields to search in (default: ["rule_name", "content", "tags"])
        limit: Optional limit on number of results
        
    Returns:
        List[Dict[str, Any]]: List of matching rules
        
    Raises:
        DatabaseConnectionError: If database is not accessible
        ValueError: If search parameters are invalid
    """
    if not search_term or not search_term.strip():
        raise ValueError("search_term is required and cannot be empty")
    
    if search_fields is None:
        search_fields = ["rule_name", "content", "tags"]
    
    if limit is not None and (not isinstance(limit, int) or limit <= 0):
        raise ValueError("limit must be a positive integer")
    
    # Get all rules and filter in memory (for simplicity)
    # In production, this could be optimized with database-specific search
    all_rules = await get_all_rules(limit=None)
    
    search_term_lower = search_term.lower().strip()
    matching_rules = []
    
    for rule in all_rules:
        # Check each specified field
        for field in search_fields:
            field_value = rule.get(field, "")
            
            # Handle different field types
            if isinstance(field_value, str):
                if search_term_lower in field_value.lower():
                    matching_rules.append(rule)
                    break
            elif isinstance(field_value, list):
                # For tags and other list fields
                if any(search_term_lower in str(item).lower() for item in field_value):
                    matching_rules.append(rule)
                    break
    
    # Apply limit if specified
    if limit:
        matching_rules = matching_rules[:limit]
    
    return matching_rules


async def get_rules_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Get all rules in a specific category.
    
    Args:
        category: The category to filter by
        
    Returns:
        List[Dict[str, Any]]: List of rules in the category
        
    Raises:
        DatabaseConnectionError: If database is not accessible
        ValueError: If category is invalid
    """
    return await get_all_rules(category=category)


async def get_rules_by_type(rule_type: str) -> List[Dict[str, Any]]:
    """
    Get all rules of a specific type.
    
    Args:
        rule_type: The type to filter by
        
    Returns:
        List[Dict[str, Any]]: List of rules of the specified type
        
    Raises:
        DatabaseConnectionError: If database is not accessible
        ValueError: If rule_type is invalid
    """
    return await get_all_rules(rule_type=rule_type)


async def get_meta_rules() -> List[Dict[str, Any]]:
    """
    Get all meta-rules (rules that aggregate learnt experiences).
    
    Returns:
        List[Dict[str, Any]]: List of meta-rules
        
    Raises:
        DatabaseConnectionError: If database is not accessible
    """
    all_rules = await get_all_rules()
    return [rule for rule in all_rules if rule.get("is_meta_rule", False)]


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

async def create_multiple_rules(rules_data: List[Dict[str, Any]]) -> List[str]:
    """
    Create multiple rules in a single operation.
    
    Args:
        rules_data: List of rule data dictionaries
        
    Returns:
        List[str]: List of created rule IDs
        
    Raises:
        ValidationError: If any rule data is invalid
        DatabaseConnectionError: If database is not accessible
    """
    if not rules_data or not isinstance(rules_data, list):
        raise ValueError("rules_data must be a non-empty list")
    
    created_ids = []
    errors = []
    
    for i, rule_data in enumerate(rules_data):
        try:
            # Extract required fields
            rule_name = rule_data.get("rule_name")
            content = rule_data.get("content")
            category = rule_data.get("category", "general")
            rule_type = rule_data.get("rule_type", "best_practice")
            
            # Extract optional fields
            priority = rule_data.get("priority", 5)
            tags = rule_data.get("tags")
            created_by = rule_data.get("created_by")
            metadata = rule_data.get("metadata")
            
            # Create rule
            rule_id = await create_rule(
                rule_name=rule_name,
                content=content,
                category=category,
                rule_type=rule_type,
                priority=priority,
                tags=tags,
                created_by=created_by,
                metadata=metadata
            )
            
            created_ids.append(rule_id)
            
        except Exception as e:
            errors.append(f"Rule {i}: {str(e)}")
    
    if errors:
        # If there were errors, we should clean up created rules
        # and raise an exception with details
        for rule_id in created_ids:
            try:
                await delete_rule(rule_id)
            except:
                pass  # Best effort cleanup
        
        raise ValidationError(f"Failed to create some rules: {'; '.join(errors)}")
    
    return created_ids


# ================================
# Export Functions
# ================================

__all__ = [
    # Core CRUD operations
    "create_rule",
    "update_rule", 
    "delete_rule",
    "get_all_rules",
    "get_rule_details",
    
    # Search and filtering
    "search_rules",
    "get_rules_by_category",
    "get_rules_by_type",
    "get_meta_rules",
    
    # Utilities
    "validate_database_connection",
    "create_multiple_rules"
] 