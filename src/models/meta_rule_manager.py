"""
MetaRuleManager for the graph database MCP server.

This module implements the core orchestrator for the self-improving AI system.
The MetaRuleManager manages the creation, updating, and aggregation of meta-rules
based on learnt experiences.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set
from collections import defaultdict, Counter

from .rule import Rule, RuleCategory, RuleType
from .learnt import Learnt, ErrorType, SeverityLevel


class MetaRuleManager:
    """
    Core manager for the meta-rule system.
    
    This class orchestrates the self-improving AI system by:
    - Creating and maintaining the special "Learnt" meta-rule
    - Aggregating knowledge from learnt experiences
    - Managing relationships between meta-rules and learnt nodes
    - Providing intelligent aggregation algorithms
    """
    
    DEFAULT_META_RULE_NAME = "Learnt Knowledge Aggregator"
    DEFAULT_META_RULE_CONTENT = "This meta-rule aggregates validated solutions from learnt experiences to help avoid common problems and improve AI performance."
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the MetaRuleManager.
        
        Args:
            logger: Optional logger instance for debugging and monitoring
        """
        self.logger = logger or logging.getLogger(__name__)
        self._meta_rule: Optional[Rule] = None
        self._tracked_learnt_nodes: Set[str] = set()
        self._aggregation_stats: Dict[str, Any] = {}
        
    @property
    def meta_rule(self) -> Optional[Rule]:
        """Get the current meta-rule instance."""
        return self._meta_rule
    
    @property
    def tracked_learnt_count(self) -> int:
        """Get the number of learnt nodes currently tracked."""
        return len(self._tracked_learnt_nodes)
    
    def initialize_meta_rule(
        self,
        rule_name: Optional[str] = None,
        initial_content: Optional[str] = None,
        **kwargs
    ) -> Rule:
        """
        Create or initialize the meta-rule.
        
        Args:
            rule_name: Optional custom name for the meta-rule
            initial_content: Optional initial content for the meta-rule
            **kwargs: Additional attributes for the meta-rule
            
        Returns:
            Rule: The initialized meta-rule instance
        """
        if self._meta_rule is not None:
            self.logger.warning("Meta-rule already exists. Replacing with new instance.")
        
        rule_name = rule_name or self.DEFAULT_META_RULE_NAME
        initial_content = initial_content or self.DEFAULT_META_RULE_CONTENT
        
        self._meta_rule = Rule.create_meta_rule(
            rule_name=rule_name,
            content=initial_content,
            **kwargs
        )
        
        self.logger.info(f"Initialized meta-rule: {self._meta_rule.rule_id}")
        
        return self._meta_rule
    
    def ensure_meta_rule_exists(self) -> Rule:
        """
        Ensure a meta-rule exists, creating one if necessary.
        
        Returns:
            Rule: The meta-rule instance
        """
        if self._meta_rule is None:
            return self.initialize_meta_rule()
        return self._meta_rule
    
    def add_learnt_experience(self, learnt: Learnt) -> bool:
        """
        Add a learnt experience to the meta-rule aggregation.
        
        Args:
            learnt: The learnt experience to incorporate
            
        Returns:
            bool: True if successfully added, False otherwise
        """
        try:
            # Ensure meta-rule exists
            meta_rule = self.ensure_meta_rule_exists()
            
            # Skip if already processed
            if learnt.learnt_id in self._tracked_learnt_nodes:
                self.logger.debug(f"Learnt {learnt.learnt_id} already processed")
                return False
            
            # Only process validated solutions
            if learnt.verification_status != "validated":
                self.logger.debug(f"Skipping non-validated learnt {learnt.learnt_id}")
                return False
            
            # Set up callback for meta-rule updates
            learnt.set_meta_rule_update_callback(self._on_learnt_update)
            
            # Trigger the learnt node to contribute to meta-rule
            if learnt.trigger_meta_rule_update():
                # Add learnt ID to meta-rule sources
                meta_rule.add_source_learnt_id(learnt.learnt_id)
                
                # Track this learnt node
                self._tracked_learnt_nodes.add(learnt.learnt_id)
                
                # Update the meta-rule content with aggregated knowledge
                self._update_meta_rule_content()
                
                self.logger.info(f"Successfully added learnt {learnt.learnt_id} to meta-rule")
                return True
            
            else:
                self.logger.warning(f"Failed to trigger meta-rule update for learnt {learnt.learnt_id}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error adding learnt experience {learnt.learnt_id}: {e}")
            return False
    
    def _on_learnt_update(self, learnt: Learnt) -> None:
        """
        Callback triggered when a learnt node updates the meta-rule.
        
        Args:
            learnt: The learnt node that triggered the update
        """
        self.logger.debug(f"Meta-rule update triggered by learnt {learnt.learnt_id}")
        
        # Update aggregation stats
        self._update_aggregation_stats(learnt)
    
    def _update_aggregation_stats(self, learnt: Learnt) -> None:
        """
        Update internal statistics about the aggregation.
        
        Args:
            learnt: The learnt experience to analyze
        """
        if not self._aggregation_stats:
            self._aggregation_stats = {
                "error_types": Counter(),
                "severity_levels": Counter(),
                "total_learnt": 0,
                "last_updated": None,
                "common_patterns": []
            }
        
        self._aggregation_stats["error_types"][learnt.type_of_error] += 1
        self._aggregation_stats["severity_levels"][learnt.original_severity] += 1
        self._aggregation_stats["total_learnt"] += 1
        self._aggregation_stats["last_updated"] = datetime.utcnow().isoformat()
    
    def _update_meta_rule_content(self) -> None:
        """
        Update the meta-rule content based on all tracked learnt experiences.
        
        This is the core aggregation algorithm that combines multiple learnt
        experiences into actionable guidance.
        """
        if not self._meta_rule or not self._tracked_learnt_nodes:
            return
        
        # Get aggregation statistics
        stats = self._aggregation_stats
        
        # Build comprehensive meta-rule content
        content_parts = [
            "# AI Learning Aggregator - Validated Solutions",
            "",
            "This meta-rule contains aggregated knowledge from validated AI learning experiences.",
            f"Total learnt experiences processed: {len(self._tracked_learnt_nodes)}",
            f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "## Key Learning Patterns:",
            ""
        ]
        
        # Add error type insights
        if stats.get("error_types"):
            content_parts.append("### Common Error Types:")
            for error_type, count in stats["error_types"].most_common():
                percentage = (count / stats["total_learnt"]) * 100
                content_parts.append(f"- {error_type}: {count} occurrences ({percentage:.1f}%)")
            content_parts.append("")
        
        # Add severity insights
        if stats.get("severity_levels"):
            content_parts.append("### Severity Distribution:")
            for severity, count in stats["severity_levels"].most_common():
                percentage = (count / stats["total_learnt"]) * 100
                content_parts.append(f"- {severity}: {count} occurrences ({percentage:.1f}%)")
            content_parts.append("")
        
        # Add actionable guidance
        content_parts.extend([
            "## Actionable Guidance:",
            "",
            "Based on the aggregated learning experiences, focus on:",
            "1. Preventing the most common error types listed above",
            "2. Implementing validated solutions for recurring problems",
            "3. Following patterns that have proven successful",
            "",
            "## Meta-Learning Principles:",
            "",
            "- Always validate solutions before implementing",
            "- Learn from both successful and failed approaches",
            "- Continuously update knowledge based on new experiences",
            "- Focus on error prevention rather than just error correction",
            "",
            f"*This content is automatically generated and updated. Source learnt experiences: {len(self._tracked_learnt_nodes)}*"
        ])
        
        # Update the meta-rule content
        new_content = "\n".join(content_parts)
        self._meta_rule.update_content(new_content)
        
        self.logger.info(f"Updated meta-rule content with {len(self._tracked_learnt_nodes)} learnt experiences")
    
    def get_aggregation_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current aggregation state.
        
        Returns:
            Dict[str, Any]: Summary information about the meta-rule aggregation
        """
        meta_rule = self._meta_rule
        
        summary = {
            "meta_rule_exists": meta_rule is not None,
            "meta_rule_id": meta_rule.rule_id if meta_rule else None,
            "meta_rule_name": meta_rule.rule_name if meta_rule else None,
            "tracked_learnt_count": len(self._tracked_learnt_nodes),
            "tracked_learnt_ids": list(self._tracked_learnt_nodes),
            "aggregation_stats": self._aggregation_stats.copy(),
            "last_updated": meta_rule.last_updated.isoformat() if meta_rule and meta_rule.last_updated else None
        }
        
        return summary
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """
        Generate insights from the aggregated learning data.
        
        Returns:
            Dict[str, Any]: Learning insights and recommendations
        """
        stats = self._aggregation_stats
        
        if not stats or stats.get("total_learnt", 0) == 0:
            return {"message": "No learning data available yet"}
        
        insights = {
            "total_experiences": stats.get("total_learnt", 0),
            "most_common_error": None,
            "most_severe_issues": None,
            "learning_velocity": None,
            "recommendations": []
        }
        
        # Identify most common error type
        if stats.get("error_types"):
            most_common = stats["error_types"].most_common(1)[0]
            insights["most_common_error"] = {
                "type": most_common[0],
                "count": most_common[1],
                "percentage": (most_common[1] / stats["total_learnt"]) * 100
            }
        
        # Identify severity patterns
        if stats.get("severity_levels"):
            critical_count = stats["severity_levels"].get("critical", 0)
            major_count = stats["severity_levels"].get("major", 0)
            
            insights["most_severe_issues"] = {
                "critical": critical_count,
                "major": major_count,
                "high_severity_percentage": ((critical_count + major_count) / stats["total_learnt"]) * 100
            }
        
        # Generate recommendations
        recommendations = []
        
        if insights["most_common_error"]:
            error_type = insights["most_common_error"]["type"]
            recommendations.append(f"Focus on preventing {error_type} errors - they represent {insights['most_common_error']['percentage']:.1f}% of all issues")
        
        if insights["most_severe_issues"]:
            high_severity_pct = insights["most_severe_issues"]["high_severity_percentage"]
            if high_severity_pct > 30:
                recommendations.append(f"High severity issues account for {high_severity_pct:.1f}% - prioritize prevention strategies")
        
        if stats["total_learnt"] > 10:
            recommendations.append("Consider implementing proactive error detection based on learned patterns")
        
        insights["recommendations"] = recommendations
        
        return insights
    
    def export_meta_rule_knowledge(self) -> Dict[str, Any]:
        """
        Export the complete meta-rule knowledge for backup or transfer.
        
        Returns:
            Dict[str, Any]: Complete exportable meta-rule data
        """
        meta_rule = self._meta_rule
        
        export_data = {
            "meta_rule": meta_rule.to_dict() if meta_rule else None,
            "tracked_learnt_ids": list(self._tracked_learnt_nodes),
            "aggregation_stats": self._aggregation_stats.copy(),
            "export_timestamp": datetime.utcnow().isoformat(),
            "manager_version": "1.0.0"
        }
        
        return export_data
    
    def import_meta_rule_knowledge(self, import_data: Dict[str, Any]) -> bool:
        """
        Import meta-rule knowledge from exported data.
        
        Args:
            import_data: Previously exported meta-rule data
            
        Returns:
            bool: True if successfully imported, False otherwise
        """
        try:
            # Import meta-rule
            if import_data.get("meta_rule"):
                self._meta_rule = Rule.from_dict(import_data["meta_rule"])
                self.logger.info(f"Imported meta-rule: {self._meta_rule.rule_id}")
            
            # Import tracked learnt IDs
            if import_data.get("tracked_learnt_ids"):
                self._tracked_learnt_nodes = set(import_data["tracked_learnt_ids"])
                self.logger.info(f"Imported {len(self._tracked_learnt_nodes)} tracked learnt IDs")
            
            # Import aggregation stats
            if import_data.get("aggregation_stats"):
                self._aggregation_stats = import_data["aggregation_stats"].copy()
                # Restore Counter objects
                if "error_types" in self._aggregation_stats:
                    self._aggregation_stats["error_types"] = Counter(self._aggregation_stats["error_types"])
                if "severity_levels" in self._aggregation_stats:
                    self._aggregation_stats["severity_levels"] = Counter(self._aggregation_stats["severity_levels"])
            
            self.logger.info("Successfully imported meta-rule knowledge")
            return True
            
        except Exception as e:
            self.logger.error(f"Error importing meta-rule knowledge: {e}")
            return False
    
    def reset_meta_rule(self) -> None:
        """
        Reset the meta-rule system to initial state.
        
        This clears all tracked data and creates a fresh meta-rule.
        """
        self.logger.info("Resetting meta-rule system")
        
        self._meta_rule = None
        self._tracked_learnt_nodes.clear()
        self._aggregation_stats.clear()
        
        # Reinitialize with default meta-rule
        self.initialize_meta_rule()
    
    def remove_learnt_experience(self, learnt_id: str) -> bool:
        """
        Remove a learnt experience from the meta-rule aggregation.
        
        Args:
            learnt_id: ID of the learnt experience to remove
            
        Returns:
            bool: True if successfully removed, False if not found
        """
        if learnt_id not in self._tracked_learnt_nodes:
            return False
        
        try:
            # Remove from tracked set
            self._tracked_learnt_nodes.remove(learnt_id)
            
            # Remove from meta-rule sources
            if self._meta_rule:
                self._meta_rule.remove_source_learnt_id(learnt_id)
            
            # Regenerate meta-rule content without this learnt experience
            # Note: This is a simplified approach. In production, you might want
            # to store individual contributions for more precise removal.
            self._update_meta_rule_content()
            
            self.logger.info(f"Removed learnt experience {learnt_id} from meta-rule")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing learnt experience {learnt_id}: {e}")
            return False
    
    def get_meta_rule_effectiveness(self) -> Dict[str, Any]:
        """
        Analyze the effectiveness of the current meta-rule.
        
        Returns:
            Dict[str, Any]: Effectiveness metrics and analysis
        """
        if not self._meta_rule or not self._tracked_learnt_nodes:
            return {"effectiveness": "unknown", "reason": "Insufficient data"}
        
        stats = self._aggregation_stats
        total_learnt = stats.get("total_learnt", 0)
        
        # Calculate basic effectiveness metrics
        effectiveness = {
            "data_coverage": {
                "total_experiences": total_learnt,
                "tracked_nodes": len(self._tracked_learnt_nodes),
                "coverage_ratio": len(self._tracked_learnt_nodes) / max(total_learnt, 1)
            },
            "content_quality": {
                "content_length": len(self._meta_rule.content),
                "last_updated": self._meta_rule.last_updated.isoformat() if self._meta_rule.last_updated else None,
                "source_diversity": len(set(stats.get("error_types", {}).keys()))
            },
            "learning_patterns": {
                "error_diversity": len(stats.get("error_types", {})),
                "severity_distribution": dict(stats.get("severity_levels", {})),
                "dominant_error_type": stats.get("error_types", Counter()).most_common(1)[0] if stats.get("error_types") else None
            }
        }
        
        # Determine overall effectiveness level
        if total_learnt == 0:
            effectiveness["overall_rating"] = "no_data"
        elif total_learnt < 5:
            effectiveness["overall_rating"] = "insufficient_data"
        elif total_learnt < 15:
            effectiveness["overall_rating"] = "developing"
        else:
            effectiveness["overall_rating"] = "mature"
        
        return effectiveness
    
    def __str__(self) -> str:
        """String representation of the MetaRuleManager."""
        meta_rule_id = self._meta_rule.rule_id if self._meta_rule else "None"
        return f"MetaRuleManager(meta_rule_id={meta_rule_id}, tracked_learnt={len(self._tracked_learnt_nodes)})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"MetaRuleManager(meta_rule_exists={self._meta_rule is not None}, "
            f"tracked_count={len(self._tracked_learnt_nodes)}, "
            f"total_learnt={self._aggregation_stats.get('total_learnt', 0)})"
        ) 