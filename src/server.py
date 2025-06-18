#!/usr/bin/env python3
"""
MCP Server for Final Minimal Lean Graph Database.

This FastAPI server exposes the Rule and Learning Management Tools via REST API
endpoints with comprehensive error handling, CORS support, and automatic
API documentation.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from contextlib import asynccontextmanager

# Import our tools
from .tools.rule_tools import (
    create_rule, update_rule, delete_rule, get_all_rules, get_rule_details,
    search_rules, get_rules_by_category, get_rules_by_type, get_meta_rules,
    validate_database_connection as validate_rule_db_connection,
    create_multiple_rules
)
from .tools.learning_tools import (
    record_validated_solution, get_learnt_solutions, get_solution_details,
    search_learnt_solutions, get_solutions_by_error_type, get_solutions_by_severity,
    get_recent_solutions, get_solutions_statistics, update_solution_verification_status,
    validate_database_connection as validate_learning_db_connection,
    record_multiple_solutions
)

# Import database and model components for type checking
from .database import DatabaseConnectionError, NodeNotFoundError, ValidationError
from .models.rule import RuleCategory, RuleType
from .models.learnt import ErrorType, SeverityLevel

# Import centralized configuration
from .config import config, server_config, get_environment_info

# Logging is configured by the config module
logger = logging.getLogger(__name__)


# ================================
# Pydantic Models for API
# ================================

class RuleCreate(BaseModel):
    """Request model for creating a new rule."""
    rule_name: str = Field(..., min_length=1, max_length=200, description="Human-readable name for the rule")
    content: str = Field(..., min_length=1, description="The actual rule content or guidance")
    category: str = Field(..., description="Rule category (frontend, backend, database, etc.)")
    rule_type: str = Field(..., description="Type of rule (best_practice, anti_pattern, etc.)")
    priority: int = Field(default=5, ge=1, le=10, description="Priority level (1=lowest, 10=highest)")
    tags: Optional[List[str]] = Field(default=None, description="Optional list of tags for organization")
    created_by: Optional[str] = Field(default=None, description="Optional creator identifier")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional additional metadata")

    @validator('category')
    def validate_category(cls, v):
        valid_categories = [cat.value for cat in RuleCategory]
        if v.lower() not in valid_categories:
            raise ValueError(f"Invalid category. Valid options: {valid_categories}")
        return v.lower()

    @validator('rule_type')
    def validate_rule_type(cls, v):
        valid_types = [rt.value for rt in RuleType]
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid rule_type. Valid options: {valid_types}")
        return v.lower()


class RuleUpdate(BaseModel):
    """Request model for updating a rule."""
    rule_name: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = None
    rule_type: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator('category')
    def validate_category(cls, v):
        if v is not None:
            valid_categories = [cat.value for cat in RuleCategory]
            if v.lower() not in valid_categories:
                raise ValueError(f"Invalid category. Valid options: {valid_categories}")
            return v.lower()
        return v

    @validator('rule_type')
    def validate_rule_type(cls, v):
        if v is not None:
            valid_types = [rt.value for rt in RuleType]
            if v.lower() not in valid_types:
                raise ValueError(f"Invalid rule_type. Valid options: {valid_types}")
            return v.lower()
        return v


class SolutionCreate(BaseModel):
    """Request model for recording a validated solution."""
    type_of_error: str = Field(..., description="Type of error encountered")
    problem_summary: str = Field(..., min_length=1, max_length=500, description="Concise problem summary")
    problematic_input_segment: str = Field(..., min_length=1, description="User input that caused the problem")
    problematic_ai_output_segment: str = Field(..., min_length=1, description="Incorrect AI output")
    inferred_original_cause: str = Field(..., min_length=1, description="AI's self-diagnosis of the root cause")
    original_severity: str = Field(..., description="Severity level (critical, major, minor, low)")
    validated_solution_description: str = Field(..., min_length=1, description="Detailed description of the proven solution")
    solution_implemented_notes: Optional[str] = Field(None, description="Optional implementation details")
    related_rule_ids: Optional[List[str]] = Field(default=None, description="Optional list of related rule IDs")
    created_by: Optional[str] = Field(default=None, description="Optional creator identifier")
    tags: Optional[List[str]] = Field(default=None, description="Optional list of tags for categorization")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional additional metadata")

    @validator('type_of_error')
    def validate_error_type(cls, v):
        valid_error_types = [et.value for et in ErrorType]
        if v not in valid_error_types:
            raise ValueError(f"Invalid type_of_error. Valid options: {valid_error_types}")
        return v

    @validator('original_severity')
    def validate_severity(cls, v):
        valid_severities = [sl.value for sl in SeverityLevel]
        if v.lower() not in valid_severities:
            raise ValueError(f"Invalid original_severity. Valid options: {valid_severities}")
        return v.lower()


class VerificationStatusUpdate(BaseModel):
    """Request model for updating solution verification status."""
    verification_status: str = Field(..., description="New verification status")

    @validator('verification_status')
    def validate_status(cls, v):
        valid_statuses = ["validated", "pending", "rejected", "needs_review"]
        if v.lower() not in valid_statuses:
            raise ValueError(f"Invalid verification_status. Valid options: {valid_statuses}")
        return v.lower()


class APIResponse(BaseModel):
    """Standard API response format."""
    success: bool = Field(..., description="Whether the operation was successful")
    data: Optional[Any] = Field(None, description="Response data")
    message: Optional[str] = Field(None, description="Response message")
    error: Optional[str] = Field(None, description="Error message if operation failed")


# ================================
# FastAPI Application Setup
# ================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Graph Database MCP Server...")
    
    # Validate database connections on startup
    try:
        rule_db_ok = await validate_rule_db_connection()
        learning_db_ok = await validate_learning_db_connection()
        
        if rule_db_ok and learning_db_ok:
            logger.info("Database connections validated successfully")
        else:
            logger.warning("Database connection validation failed")
            
    except Exception as e:
        logger.error(f"Database validation error: {e}")
    
    yield
    
    logger.info("Shutting down Graph Database MCP Server...")


# Initialize FastAPI app
app = FastAPI(
    title="Graph Database MCP Server",
    description="MCP Server for Final Minimal Lean Graph Database - Rule and Learning Management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS from centralized configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=server_config.cors_origins,
    allow_credentials=server_config.cors_credentials,
    allow_methods=server_config.cors_methods,
    allow_headers=server_config.cors_headers,
)


# ================================
# Exception Handlers
# ================================

@app.exception_handler(DatabaseConnectionError)
async def database_connection_exception_handler(request, exc):
    """Handle database connection errors."""
    logger.error(f"Database connection error: {exc}")
    return JSONResponse(
        status_code=503,
        content=APIResponse(
            success=False,
            error="Database connection error",
            message=str(exc)
        ).dict()
    )


@app.exception_handler(NodeNotFoundError)
async def node_not_found_exception_handler(request, exc):
    """Handle node not found errors."""
    logger.warning(f"Node not found: {exc}")
    return JSONResponse(
        status_code=404,
        content=APIResponse(
            success=False,
            error="Resource not found",
            message=str(exc)
        ).dict()
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """Handle validation errors."""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=400,
        content=APIResponse(
            success=False,
            error="Validation error",
            message=str(exc)
        ).dict()
    )


@app.exception_handler(ValueError)
async def value_error_exception_handler(request, exc):
    """Handle value errors."""
    logger.warning(f"Value error: {exc}")
    return JSONResponse(
        status_code=400,
        content=APIResponse(
            success=False,
            error="Invalid input",
            message=str(exc)
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle all other exceptions."""
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content=APIResponse(
            success=False,
            error="Internal server error",
            message="An unexpected error occurred"
        ).dict()
    )


# ================================
# Dependency Functions
# ================================

async def get_database_status() -> Dict[str, bool]:
    """Check database connectivity status."""
    try:
        rule_db_ok = await validate_rule_db_connection()
        learning_db_ok = await validate_learning_db_connection()
        return {
            "rule_database": rule_db_ok,
            "learning_database": learning_db_ok,
            "overall": rule_db_ok and learning_db_ok
        }
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        return {
            "rule_database": False,
            "learning_database": False,
            "overall": False
        }


# ================================
# Health Check Endpoints
# ================================

@app.get("/", response_model=APIResponse, tags=["Health"])
async def root():
    """Root endpoint - health check."""
    return APIResponse(
        success=True,
        data={"service": "Graph Database MCP Server", "status": "running"},
        message="Service is healthy"
    )


@app.get("/health", response_model=APIResponse, tags=["Health"])
async def health_check(db_status: Dict[str, bool] = Depends(get_database_status)):
    """Comprehensive health check including database connectivity."""
    return APIResponse(
        success=db_status["overall"],
        data={
            "service": "Graph Database MCP Server",
            "timestamp": datetime.utcnow().isoformat(),
            "database_status": db_status
        },
        message="Health check completed"
    )


@app.get("/environment", response_model=APIResponse, tags=["Health"])
async def get_environment():
    """Get environment configuration and status information."""
    return APIResponse(
        success=True,
        data=get_environment_info(),
        message="Environment information retrieved successfully"
    )


# ================================
# Rule Management Endpoints
# ================================

@app.post("/rules", response_model=APIResponse, tags=["Rules"])
async def create_rule_endpoint(rule_data: RuleCreate):
    """Create a new rule."""
    try:
        rule_id = await create_rule(
            rule_name=rule_data.rule_name,
            content=rule_data.content,
            category=rule_data.category,
            rule_type=rule_data.rule_type,
            priority=rule_data.priority,
            tags=rule_data.tags,
            created_by=rule_data.created_by,
            metadata=rule_data.metadata
        )
        
        return APIResponse(
            success=True,
            data={"rule_id": rule_id},
            message="Rule created successfully"
        )
        
    except DatabaseConnectionError:
        # Let the global exception handler deal with this
        raise
    except Exception as e:
        logger.error(f"Failed to create rule: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/rules", response_model=APIResponse, tags=["Rules"])
async def get_rules_endpoint(
    category: Optional[str] = Query(None, description="Filter by category"),
    rule_type: Optional[str] = Query(None, description="Filter by rule type"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of rules to return"),
    include_meta_rules: bool = Query(True, description="Include meta rules in results")
):
    """Get all rules with optional filtering."""
    try:
        rules = await get_all_rules(
            category=category,
            rule_type=rule_type,
            limit=limit,
            include_meta_rules=include_meta_rules
        )
        
        return APIResponse(
            success=True,
            data={"rules": rules, "count": len(rules)},
            message=f"Retrieved {len(rules)} rules"
        )
        
    except Exception as e:
        logger.error(f"Failed to get rules: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/rules/meta", response_model=APIResponse, tags=["Rules"])
async def get_meta_rules_endpoint():
    """Get all meta rules."""
    try:
        meta_rules = await get_meta_rules()
        
        return APIResponse(
            success=True,
            data={"meta_rules": meta_rules, "count": len(meta_rules)},
            message=f"Retrieved {len(meta_rules)} meta rules"
        )
        
    except Exception as e:
        logger.error(f"Failed to get meta rules: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/rules/{rule_id}", response_model=APIResponse, tags=["Rules"])
async def get_rule_endpoint(rule_id: str = Path(..., description="Rule ID")):
    """Get detailed information about a specific rule."""
    try:
        rule = await get_rule_details(rule_id)
        
        return APIResponse(
            success=True,
            data=rule,
            message="Rule retrieved successfully"
        )
        
    except NodeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Rule with ID '{rule_id}' not found")
    except Exception as e:
        logger.error(f"Failed to get rule {rule_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/rules/{rule_id}", response_model=APIResponse, tags=["Rules"])
async def update_rule_endpoint(
    rule_id: str = Path(..., description="Rule ID"),
    updates: RuleUpdate = ...
):
    """Update an existing rule."""
    try:
        # Convert to dict and remove None values
        update_dict = {k: v for k, v in updates.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No valid updates provided")
        
        updated_rule = await update_rule(rule_id, update_dict)
        
        return APIResponse(
            success=True,
            data=updated_rule,
            message="Rule updated successfully"
        )
        
    except NodeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Rule with ID '{rule_id}' not found")
    except Exception as e:
        logger.error(f"Failed to update rule {rule_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/rules/{rule_id}", response_model=APIResponse, tags=["Rules"])
async def delete_rule_endpoint(rule_id: str = Path(..., description="Rule ID")):
    """Delete a rule."""
    try:
        success = await delete_rule(rule_id)
        
        if success:
            return APIResponse(
                success=True,
                data={"deleted": True},
                message="Rule deleted successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete rule")
            
    except NodeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Rule with ID '{rule_id}' not found")
    except Exception as e:
        logger.error(f"Failed to delete rule {rule_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/rules/search/{search_term}", response_model=APIResponse, tags=["Rules"])
async def search_rules_endpoint(
    search_term: str = Path(..., description="Search term"),
    search_fields: Optional[List[str]] = Query(None, description="Fields to search in"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results")
):
    """Search rules by term."""
    try:
        rules = await search_rules(
            search_term=search_term,
            search_fields=search_fields,
            limit=limit
        )
        
        return APIResponse(
            success=True,
            data={"rules": rules, "count": len(rules)},
            message=f"Found {len(rules)} matching rules"
        )
        
    except Exception as e:
        logger.error(f"Failed to search rules: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/rules/category/{category}", response_model=APIResponse, tags=["Rules"])
async def get_rules_by_category_endpoint(category: str = Path(..., description="Rule category")):
    """Get rules by category."""
    try:
        rules = await get_rules_by_category(category)
        
        return APIResponse(
            success=True,
            data={"rules": rules, "count": len(rules)},
            message=f"Retrieved {len(rules)} rules in category '{category}'"
        )
        
    except Exception as e:
        logger.error(f"Failed to get rules by category: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/rules/type/{rule_type}", response_model=APIResponse, tags=["Rules"])
async def get_rules_by_type_endpoint(rule_type: str = Path(..., description="Rule type")):
    """Get rules by type."""
    try:
        rules = await get_rules_by_type(rule_type)
        
        return APIResponse(
            success=True,
            data={"rules": rules, "count": len(rules)},
            message=f"Retrieved {len(rules)} rules of type '{rule_type}'"
        )
        
    except Exception as e:
        logger.error(f"Failed to get rules by type: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/rules/batch", response_model=APIResponse, tags=["Rules"])
async def create_multiple_rules_endpoint(rules_data: List[RuleCreate]):
    """Create multiple rules in batch."""
    try:
        # Convert Pydantic models to dicts
        rules_dict_list = [rule.dict() for rule in rules_data]
        
        rule_ids = await create_multiple_rules(rules_dict_list)
        
        return APIResponse(
            success=True,
            data={"rule_ids": rule_ids, "count": len(rule_ids)},
            message=f"Created {len(rule_ids)} rules successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to create multiple rules: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ================================
# Learning Management Endpoints
# ================================

@app.post("/solutions", response_model=APIResponse, tags=["Learning"])
async def record_solution_endpoint(solution_data: SolutionCreate):
    """Record a validated solution."""
    try:
        solution_id = await record_validated_solution(
            type_of_error=solution_data.type_of_error,
            problem_summary=solution_data.problem_summary,
            problematic_input_segment=solution_data.problematic_input_segment,
            problematic_ai_output_segment=solution_data.problematic_ai_output_segment,
            inferred_original_cause=solution_data.inferred_original_cause,
            original_severity=solution_data.original_severity,
            validated_solution_description=solution_data.validated_solution_description,
            solution_implemented_notes=solution_data.solution_implemented_notes,
            related_rule_ids=solution_data.related_rule_ids,
            created_by=solution_data.created_by,
            tags=solution_data.tags,
            metadata=solution_data.metadata
        )
        
        return APIResponse(
            success=True,
            data={"solution_id": solution_id},
            message="Solution recorded successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to record solution: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/solutions", response_model=APIResponse, tags=["Learning"])
async def get_solutions_endpoint(
    error_type: Optional[str] = Query(None, description="Filter by error type"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    related_rule_id: Optional[str] = Query(None, description="Filter by related rule ID"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of solutions to return"),
    include_meta_contributions: bool = Query(True, description="Include meta rule contributions")
):
    """Get all learnt solutions with optional filtering."""
    try:
        solutions = await get_learnt_solutions(
            error_type=error_type,
            severity=severity,
            related_rule_id=related_rule_id,
            verification_status=verification_status,
            limit=limit,
            include_meta_contributions=include_meta_contributions
        )
        
        return APIResponse(
            success=True,
            data={"solutions": solutions, "count": len(solutions)},
            message=f"Retrieved {len(solutions)} solutions"
        )
        
    except Exception as e:
        logger.error(f"Failed to get solutions: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/solutions/search/{search_term}", response_model=APIResponse, tags=["Learning"])
async def search_solutions_endpoint(
    search_term: str = Path(..., description="Search term"),
    search_fields: Optional[List[str]] = Query(None, description="Fields to search in"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results")
):
    """Search solutions by term."""
    try:
        solutions = await search_learnt_solutions(
            search_term=search_term,
            search_fields=search_fields,
            limit=limit
        )
        
        return APIResponse(
            success=True,
            data={"solutions": solutions, "count": len(solutions)},
            message=f"Found {len(solutions)} matching solutions"
        )
        
    except Exception as e:
        logger.error(f"Failed to search solutions: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/solutions/error-type/{error_type}", response_model=APIResponse, tags=["Learning"])
async def get_solutions_by_error_type_endpoint(error_type: str = Path(..., description="Error type")):
    """Get solutions by error type."""
    try:
        solutions = await get_solutions_by_error_type(error_type)
        
        return APIResponse(
            success=True,
            data={"solutions": solutions, "count": len(solutions)},
            message=f"Retrieved {len(solutions)} solutions for error type '{error_type}'"
        )
        
    except Exception as e:
        logger.error(f"Failed to get solutions by error type: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/solutions/severity/{severity}", response_model=APIResponse, tags=["Learning"])
async def get_solutions_by_severity_endpoint(severity: str = Path(..., description="Severity level")):
    """Get solutions by severity level."""
    try:
        solutions = await get_solutions_by_severity(severity)
        
        return APIResponse(
            success=True,
            data={"solutions": solutions, "count": len(solutions)},
            message=f"Retrieved {len(solutions)} solutions with severity '{severity}'"
        )
        
    except Exception as e:
        logger.error(f"Failed to get solutions by severity: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/solutions/recent", response_model=APIResponse, tags=["Learning"])
async def get_recent_solutions_endpoint(
    days: int = Query(7, ge=1, description="Number of days to look back"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of solutions")
):
    """Get recent solutions."""
    try:
        solutions = await get_recent_solutions(days=days, limit=limit)
        
        return APIResponse(
            success=True,
            data={"solutions": solutions, "count": len(solutions)},
            message=f"Retrieved {len(solutions)} solutions from the last {days} days"
        )
        
    except Exception as e:
        logger.error(f"Failed to get recent solutions: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/solutions/statistics", response_model=APIResponse, tags=["Learning"])
async def get_solutions_statistics_endpoint():
    """Get solutions statistics."""
    try:
        stats = await get_solutions_statistics()
        
        return APIResponse(
            success=True,
            data=stats,
            message="Statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to get solutions statistics: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/solutions/{solution_id}", response_model=APIResponse, tags=["Learning"])
async def get_solution_endpoint(solution_id: str = Path(..., description="Solution ID")):
    """Get detailed information about a specific solution."""
    try:
        solution = await get_solution_details(solution_id)
        
        return APIResponse(
            success=True,
            data=solution,
            message="Solution retrieved successfully"
        )
        
    except NodeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Solution with ID '{solution_id}' not found")
    except Exception as e:
        logger.error(f"Failed to get solution {solution_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/solutions/{solution_id}/verification", response_model=APIResponse, tags=["Learning"])
async def update_solution_verification_endpoint(
    solution_id: str = Path(..., description="Solution ID"),
    status_update: VerificationStatusUpdate = ...
):
    """Update solution verification status."""
    try:
        updated_solution = await update_solution_verification_status(
            solution_id, status_update.verification_status
        )
        
        return APIResponse(
            success=True,
            data=updated_solution,
            message="Verification status updated successfully"
        )
        
    except NodeNotFoundError:
        raise HTTPException(status_code=404, detail=f"Solution with ID '{solution_id}' not found")
    except Exception as e:
        logger.error(f"Failed to update solution verification: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/solutions/batch", response_model=APIResponse, tags=["Learning"])
async def record_multiple_solutions_endpoint(solutions_data: List[SolutionCreate]):
    """Record multiple solutions in batch."""
    try:
        # Convert Pydantic models to dicts
        solutions_dict_list = [solution.dict() for solution in solutions_data]
        
        solution_ids = await record_multiple_solutions(solutions_dict_list)
        
        return APIResponse(
            success=True,
            data={"solution_ids": solution_ids, "count": len(solution_ids)},
            message=f"Recorded {len(solution_ids)} solutions successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to record multiple solutions: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ================================
# Utility Endpoints
# ================================

@app.get("/enums/rule-categories", response_model=APIResponse, tags=["Utilities"])
async def get_rule_categories():
    """Get all valid rule categories."""
    categories = [cat.value for cat in RuleCategory]
    return APIResponse(
        success=True,
        data={"categories": categories},
        message="Rule categories retrieved successfully"
    )


@app.get("/enums/rule-types", response_model=APIResponse, tags=["Utilities"])
async def get_rule_types():
    """Get all valid rule types."""
    types = [rt.value for rt in RuleType]
    return APIResponse(
        success=True,
        data={"types": types},
        message="Rule types retrieved successfully"
    )


@app.get("/enums/error-types", response_model=APIResponse, tags=["Utilities"])
async def get_error_types():
    """Get all valid error types."""
    error_types = [et.value for et in ErrorType]
    return APIResponse(
        success=True,
        data={"error_types": error_types},
        message="Error types retrieved successfully"
    )


@app.get("/enums/severity-levels", response_model=APIResponse, tags=["Utilities"])
async def get_severity_levels():
    """Get all valid severity levels."""
    severities = [sl.value for sl in SeverityLevel]
    return APIResponse(
        success=True,
        data={"severity_levels": severities},
        message="Severity levels retrieved successfully"
    )


# ================================
# Development Server
# ================================

if __name__ == "__main__":
    import uvicorn
    
    # Get configuration from environment
    host = os.getenv("SERVER_HOST", "127.0.0.1")
    port = int(os.getenv("SERVER_PORT", "8000"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port} (debug={debug})")
    
    uvicorn.run(
        "src.server:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    ) 