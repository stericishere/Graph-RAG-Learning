"""
Rule model for the graph database MCP server.

This module defines the Rule data model that supports both regular user rules
and special meta-rules that aggregate learnt experiences.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class RuleCategory(str, Enum):
    """Categories for organizing rules."""
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    SECURITY = "security"
    PERFORMANCE = "performance"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    GENERAL = "general"
    META_LEARNT = "meta_learnt"  # Special category for meta-rules


class RuleType(str, Enum):
    """Types of rules."""
    BEST_PRACTICE = "best_practice"
    ANTI_PATTERN = "anti_pattern"
    CONFIGURATION = "configuration"
    GUIDELINE = "guideline"
    META_AGGREGATION = "meta_aggregation"  # Special type for meta-rules


class Rule(BaseModel):
    """
    Rule model supporting both regular rules and meta-rules.
    
    Meta-rules are special rules that automatically aggregate knowledge
    from learnt experiences to help avoid future problems.
    """
    
    # Core attributes
    rule_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for the rule"
    )
    
    rule_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Human-readable name for the rule"
    )
    
    content: str = Field(
        ...,
        min_length=1,
        description="The actual rule content or guidance"
    )
    
    category: RuleCategory = Field(
        default=RuleCategory.GENERAL,
        description="Category for organizing rules"
    )
    
    rule_type: RuleType = Field(
        default=RuleType.BEST_PRACTICE,
        description="Type of rule (best practice, anti-pattern, etc.)"
    )
    
    # Meta-rule specific attributes
    is_meta_rule: bool = Field(
        default=False,
        description="True if this is a meta-rule that aggregates learnt experiences"
    )
    
    last_updated: Optional[datetime] = Field(
        default=None,
        description="When the meta-rule was last updated (meta-rules only)"
    )
    
    source_learnt_ids: List[str] = Field(
        default_factory=list,
        description="List of learnt node IDs that contributed to this meta-rule"
    )
    
    # Optional metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the rule was created"
    )
    
    created_by: Optional[str] = Field(
        default=None,
        description="Who or what created this rule"
    )
    
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Priority level (1=lowest, 10=highest)"
    )
    
    tags: List[str] = Field(
        default_factory=list,
        description="Additional tags for filtering and organization"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the rule"
    )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "rule_name": "React Performance Optimization",
                "content": "Always use React.memo() for components that receive complex props to prevent unnecessary re-renders",
                "category": "frontend",
                "rule_type": "best_practice",
                "is_meta_rule": False,
                "priority": 8,
                "tags": ["react", "performance", "optimization"]
            }
        }
    
    @field_validator("rule_name")
    @classmethod
    def validate_rule_name(cls, v):
        """Validate rule name format."""
        if not v.strip():
            raise ValueError("Rule name cannot be empty or whitespace only")
        return v.strip()
    
    @field_validator("content")
    @classmethod
    def validate_content(cls, v):
        """Validate rule content."""
        if not v.strip():
            raise ValueError("Rule content cannot be empty or whitespace only")
        return v.strip()
    
    @model_validator(mode='after')
    def validate_meta_rule_fields(self):
        """Validate meta-rule specific field combinations."""
        if self.is_meta_rule:
            # Meta-rules should have specific category and type
            if self.category != RuleCategory.META_LEARNT:
                self.category = RuleCategory.META_LEARNT
            
            if self.rule_type != RuleType.META_AGGREGATION:
                self.rule_type = RuleType.META_AGGREGATION
            
            # Set last_updated if not provided
            if not self.last_updated:
                self.last_updated = datetime.utcnow()
        
        else:
            # Regular rules shouldn't have meta-rule fields
            if self.category == RuleCategory.META_LEARNT:
                raise ValueError("Only meta-rules can have META_LEARNT category")
            
            if self.rule_type == RuleType.META_AGGREGATION:
                raise ValueError("Only meta-rules can have META_AGGREGATION type")
            
            if self.source_learnt_ids:
                raise ValueError("Only meta-rules can have source_learnt_ids")
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the rule to a dictionary representation.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the rule
        """
        data = self.dict()
        
        # Convert datetime objects to ISO format strings
        if data.get("created_at"):
            data["created_at"] = data["created_at"].isoformat()
        
        if data.get("last_updated"):
            data["last_updated"] = data["last_updated"].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        """
        Create a Rule instance from a dictionary.
        
        Args:
            data: Dictionary containing rule data
            
        Returns:
            Rule: New Rule instance
        """
        # Convert ISO strings back to datetime objects
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        
        if "last_updated" in data and isinstance(data["last_updated"], str):
            data["last_updated"] = datetime.fromisoformat(data["last_updated"])
        
        return cls(**data)
    
    def update_content(self, new_content: str) -> None:
        """
        Update the rule content and last_updated timestamp for meta-rules.
        
        Args:
            new_content: New content for the rule
        """
        self.content = new_content
        
        if self.is_meta_rule:
            self.last_updated = datetime.utcnow()
    
    def add_source_learnt_id(self, learnt_id: str) -> None:
        """
        Add a learnt node ID to the source list (meta-rules only).
        
        Args:
            learnt_id: ID of the learnt node that contributed to this meta-rule
            
        Raises:
            ValueError: If called on a non-meta-rule
        """
        if not self.is_meta_rule:
            raise ValueError("Only meta-rules can have source learnt IDs")
        
        if learnt_id not in self.source_learnt_ids:
            self.source_learnt_ids.append(learnt_id)
            self.last_updated = datetime.utcnow()
    
    def remove_source_learnt_id(self, learnt_id: str) -> bool:
        """
        Remove a learnt node ID from the source list (meta-rules only).
        
        Args:
            learnt_id: ID of the learnt node to remove
            
        Returns:
            bool: True if removed, False if not found
            
        Raises:
            ValueError: If called on a non-meta-rule
        """
        if not self.is_meta_rule:
            raise ValueError("Only meta-rules can have source learnt IDs")
        
        if learnt_id in self.source_learnt_ids:
            self.source_learnt_ids.remove(learnt_id)
            self.last_updated = datetime.utcnow()
            return True
        
        return False
    
    @classmethod
    def create_meta_rule(
        cls,
        rule_name: str,
        content: str,
        source_learnt_ids: Optional[List[str]] = None,
        **kwargs
    ) -> "Rule":
        """
        Create a new meta-rule with proper defaults.
        
        Args:
            rule_name: Name for the meta-rule
            content: Initial content for the meta-rule
            source_learnt_ids: Initial list of contributing learnt node IDs
            **kwargs: Additional rule attributes
            
        Returns:
            Rule: New meta-rule instance
        """
        return cls(
            rule_name=rule_name,
            content=content,
            is_meta_rule=True,
            category=RuleCategory.META_LEARNT,
            rule_type=RuleType.META_AGGREGATION,
            source_learnt_ids=source_learnt_ids or [],
            last_updated=datetime.utcnow(),
            **kwargs
        )
    
    def __str__(self) -> str:
        """String representation of the rule."""
        rule_type_str = "Meta-Rule" if self.is_meta_rule else "Rule"
        return f"{rule_type_str}: {self.rule_name} ({self.category})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"Rule(id={self.rule_id}, name='{self.rule_name}', "
            f"category={self.category}, is_meta_rule={self.is_meta_rule})"
        ) 