"""
Learnt model for the graph database MCP server.

This module defines the Learnt data model that captures validated solutions
to problems and supports meta-rule contribution tracking.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class ErrorType(str, Enum):
    """Types of errors that can be learned from."""
    INCORRECT_ACTION = "IncorrectAction"
    MISUNDERSTANDING = "Misunderstanding" 
    UNMET_USER_GOAL = "UnmetUserGoal"
    INVALID_RESPONSE = "InvalidResponse"
    INCOMPLETE_SOLUTION = "IncompleteSolution"
    WRONG_ASSUMPTION = "WrongAssumption"
    MISSING_CONTEXT = "MissingContext"
    OTHER = "Other"


class SeverityLevel(str, Enum):
    """Severity levels for problems."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    LOW = "low"


class Learnt(BaseModel):
    """
    Learnt model for capturing validated solutions to problems.
    
    This model stores information about problems encountered and their
    validated solutions, supporting the meta-rule aggregation system.
    """
    
    # Core PRD attributes
    learnt_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the learnt solution"
    )
    
    timestamp_recorded: datetime = Field(
        default_factory=datetime.utcnow,
        description="ISO timestamp when the learning was recorded"
    )
    
    type_of_error: ErrorType = Field(
        ...,
        description="Type of error that was encountered"
    )
    
    problem_summary: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Concise AI-generated problem summary"
    )
    
    problematic_input_segment: str = Field(
        ...,
        min_length=1,
        description="User input part that caused the problem"
    )
    
    problematic_ai_output_segment: str = Field(
        ...,
        min_length=1,
        description="Incorrect AI output that caused the issue"
    )
    
    inferred_original_cause: str = Field(
        ...,
        min_length=1,
        description="AI's self-diagnosis of the problem root cause"
    )
    
    original_severity: SeverityLevel = Field(
        ...,
        description="Severity level of the original problem"
    )
    
    validated_solution_description: str = Field(
        ...,
        min_length=1,
        description="Detailed description of the proven solution"
    )
    
    solution_implemented_notes: Optional[str] = Field(
        default=None,
        description="Optional implementation details and notes"
    )
    
    related_rule_ids: List[str] = Field(
        default_factory=list,
        description="List of Rule node IDs that were updated/created from this learning"
    )
    
    # Meta-rule integration attributes
    contributed_to_meta_rule: bool = Field(
        default=False,
        description="Whether this learnt node has been incorporated into the meta-rule"
    )
    
    meta_rule_contribution: Optional[str] = Field(
        default=None,
        description="Extracted knowledge from this learning for meta-rule aggregation"
    )
    
    # Additional metadata
    created_by: Optional[str] = Field(
        default=None,
        description="Who or what created this learning record"
    )
    
    verification_status: str = Field(
        default="validated",
        description="Status of solution verification (validated, pending, rejected)"
    )
    
    tags: List[str] = Field(
        default_factory=list,
        description="Additional tags for categorization and search"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the learning"
    )
    
    # Callback for meta-rule updates  
    meta_rule_update_callback: Optional[Callable] = Field(
        default=None,
        exclude=True,
        description="Callback function to trigger meta-rule updates"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "type_of_error": "IncorrectAction",
                "problem_summary": "AI suggested using deprecated React lifecycle method",
                "problematic_input_segment": "How do I fetch data in React?",
                "problematic_ai_output_segment": "Use componentWillMount() to fetch data",
                "inferred_original_cause": "Outdated React knowledge from training data",
                "original_severity": "major",
                "validated_solution_description": "Use useEffect() hook with empty dependency array for data fetching in functional components",
                "solution_implemented_notes": "Updated React best practices rule to emphasize hooks over lifecycle methods",
                "related_rule_ids": ["rule-abc-123"]
            }
        }
    
    @field_validator("problem_summary")
    @classmethod
    def validate_problem_summary(cls, v):
        """Validate problem summary format."""
        if not v.strip():
            raise ValueError("Problem summary cannot be empty")
        return v.strip()
    
    @field_validator("problematic_input_segment")
    @classmethod
    def validate_problematic_input(cls, v):
        """Validate problematic input segment."""
        if not v.strip():
            raise ValueError("Problematic input segment cannot be empty")
        return v.strip()
    
    @field_validator("problematic_ai_output_segment")
    @classmethod
    def validate_problematic_output(cls, v):
        """Validate problematic AI output segment."""
        if not v.strip():
            raise ValueError("Problematic AI output segment cannot be empty")
        return v.strip()
    
    @field_validator("validated_solution_description")
    @classmethod
    def validate_solution_description(cls, v):
        """Validate solution description."""
        if not v.strip():
            raise ValueError("Validated solution description cannot be empty")
        return v.strip()
    
    @model_validator(mode='after')
    def validate_meta_rule_contribution(self):
        """Validate meta-rule contribution consistency."""
        if self.contributed_to_meta_rule and not self.meta_rule_contribution:
            # Auto-generate contribution if marked as contributed but no contribution text
            self.meta_rule_contribution = self._generate_meta_rule_contribution()
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the learnt solution to a dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the learnt solution
        """
        data = self.dict(exclude={"meta_rule_update_callback"})
        
        # Convert datetime to ISO format string
        if data.get("timestamp_recorded"):
            data["timestamp_recorded"] = data["timestamp_recorded"].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Learnt":
        """
        Create a Learnt instance from a dictionary.
        
        Args:
            data: Dictionary containing learnt solution data
            
        Returns:
            Learnt: New Learnt instance
        """
        # Convert ISO string back to datetime object
        if "timestamp_recorded" in data and isinstance(data["timestamp_recorded"], str):
            data["timestamp_recorded"] = datetime.fromisoformat(data["timestamp_recorded"])
        
        return cls(**data)
    
    def set_meta_rule_update_callback(self, callback: Callable) -> None:
        """
        Set the callback function for meta-rule updates.
        
        Args:
            callback: Function to call when meta-rule updates are needed
        """
        self.meta_rule_update_callback = callback
    
    def trigger_meta_rule_update(self) -> bool:
        """
        Signal that a new learnt node should update the meta-rule.
        
        This method is called when this learnt solution should contribute
        to the meta-rule knowledge aggregation.
        
        Returns:
            bool: True if update was triggered successfully, False otherwise
        """
        try:
            # Generate contribution if not already set
            if not self.meta_rule_contribution:
                self.meta_rule_contribution = self._generate_meta_rule_contribution()
            
            # Mark as contributed
            self.contributed_to_meta_rule = True
            
            # Call the callback if set
            if self.meta_rule_update_callback:
                self.meta_rule_update_callback(self)
                return True
            
            # If no callback is set, just mark as ready for contribution
            return True
            
        except Exception as e:
            # Log error but don't fail the operation
            # In production, this would use proper logging
            print(f"Error triggering meta-rule update: {e}")
            return False
    
    def _generate_meta_rule_contribution(self) -> str:
        """
        Generate a meta-rule contribution summary from this learning.
        
        Returns:
            str: Formatted contribution text for meta-rule aggregation
        """
        return (
            f"To avoid {self.type_of_error.lower()}: {self.problem_summary}. "
            f"Solution: {self.validated_solution_description[:200]}{'...' if len(self.validated_solution_description) > 200 else ''}"
        )
    
    def add_related_rule_id(self, rule_id: str) -> None:
        """
        Add a rule ID to the related rules list.
        
        Args:
            rule_id: ID of the rule that was updated/created from this learning
        """
        if rule_id not in self.related_rule_ids:
            self.related_rule_ids.append(rule_id)
    
    def remove_related_rule_id(self, rule_id: str) -> bool:
        """
        Remove a rule ID from the related rules list.
        
        Args:
            rule_id: ID of the rule to remove
            
        Returns:
            bool: True if removed, False if not found
        """
        if rule_id in self.related_rule_ids:
            self.related_rule_ids.remove(rule_id)
            return True
        return False
    
    def update_verification_status(self, status: str) -> None:
        """
        Update the verification status of this learning.
        
        Args:
            status: New verification status (validated, pending, rejected)
        """
        if status not in ["validated", "pending", "rejected"]:
            raise ValueError("Status must be one of: validated, pending, rejected")
        
        self.verification_status = status
        
        # If status changes to validated, it might be ready for meta-rule contribution
        if status == "validated" and not self.contributed_to_meta_rule:
            # Auto-trigger meta-rule update for newly validated solutions
            self.trigger_meta_rule_update()
    
    def get_learning_summary(self) -> Dict[str, str]:
        """
        Get a concise summary of this learning for display purposes.
        
        Returns:
            Dict[str, str]: Summary information
        """
        return {
            "id": self.learnt_id,
            "timestamp": self.timestamp_recorded.isoformat(),
            "error_type": self.type_of_error,
            "severity": self.original_severity,
            "problem": self.problem_summary,
            "solution": self.validated_solution_description[:100] + "..." if len(self.validated_solution_description) > 100 else self.validated_solution_description,
            "meta_rule_ready": str(self.contributed_to_meta_rule)
        }
    
    @classmethod
    def create_from_error(
        cls,
        error_type: str,
        problem_summary: str,
        problematic_input: str,
        problematic_output: str,
        root_cause: str,
        severity: str,
        solution: str,
        implementation_notes: Optional[str] = None,
        **kwargs
    ) -> "Learnt":
        """
        Create a new Learnt instance from error information.
        
        Args:
            error_type: Type of error encountered
            problem_summary: Summary of the problem
            problematic_input: User input that caused the problem
            problematic_output: AI output that was problematic
            root_cause: Inferred cause of the problem
            severity: Severity level of the problem
            solution: Validated solution description
            implementation_notes: Optional implementation details
            **kwargs: Additional attributes
            
        Returns:
            Learnt: New Learnt instance
        """
        return cls(
            type_of_error=ErrorType(error_type),
            problem_summary=problem_summary,
            problematic_input_segment=problematic_input,
            problematic_ai_output_segment=problematic_output,
            inferred_original_cause=root_cause,
            original_severity=SeverityLevel(severity),
            validated_solution_description=solution,
            solution_implemented_notes=implementation_notes,
            **kwargs
        )
    
    def __str__(self) -> str:
        """String representation of the learnt solution."""
        return f"Learning: {self.type_of_error} - {self.problem_summary[:50]}..."
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"Learnt(id={self.learnt_id}, error_type={self.type_of_error}, "
            f"severity={self.original_severity}, contributed={self.contributed_to_meta_rule})"
        ) 