"""
Comprehensive integration tests for Rule, Learnt, and MetaRuleManager models.

This test suite validates the complete self-improving AI system functionality,
including model interactions, data validation, and meta-rule aggregation.
"""

import pytest
import tempfile
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.models import Rule, Learnt, MetaRuleManager
from src.models.rule import RuleCategory, RuleType
from src.models.learnt import ErrorType, SeverityLevel


class TestRuleModel:
    """Test suite for Rule model functionality."""
    
    def test_rule_creation_basic(self):
        """Test basic rule creation."""
        rule = Rule(
            rule_name="Test Rule",
            content="Test content for the rule"
        )
        
        assert rule.rule_name == "Test Rule"
        assert rule.content == "Test content for the rule"
        assert len(rule.rule_id) == 36  # UUID format
        assert rule.category == RuleCategory.GENERAL
        assert rule.rule_type == RuleType.BEST_PRACTICE
        assert not rule.is_meta_rule
        assert isinstance(rule.created_at, datetime)
    
    def test_meta_rule_creation(self):
        """Test meta-rule creation via factory method."""
        meta_rule = Rule.create_meta_rule(
            rule_name="Test Meta Rule",
            content="Meta rule content"
        )
        
        assert meta_rule.is_meta_rule
        assert meta_rule.category == RuleCategory.META_LEARNT
        assert meta_rule.rule_type == RuleType.META_AGGREGATION
        assert meta_rule.last_updated is not None
        assert meta_rule.source_learnt_ids == []
    
    def test_rule_validation(self):
        """Test rule validation constraints."""
        # Test empty rule name
        with pytest.raises(ValueError, match="Rule name cannot be empty"):
            Rule(rule_name="", content="Valid content")
        
        # Test empty content
        with pytest.raises(ValueError, match="Rule content cannot be empty"):
            Rule(rule_name="Valid name", content="")
        
        # Test whitespace only
        with pytest.raises(ValueError):
            Rule(rule_name="   ", content="Valid content")
    
    def test_rule_serialization(self):
        """Test rule to_dict and from_dict methods."""
        original_rule = Rule(
            rule_name="Serialization Test",
            content="Test content",
            priority=8,
            tags=["test", "serialization"]
        )
        
        # Test to_dict
        rule_dict = original_rule.to_dict()
        
        assert rule_dict["rule_name"] == "Serialization Test"
        assert rule_dict["content"] == "Test content"
        assert rule_dict["priority"] == 8
        assert "created_at" in rule_dict
        
        # Test from_dict
        restored_rule = Rule.from_dict(rule_dict)
        
        assert restored_rule.rule_name == original_rule.rule_name
        assert restored_rule.content == original_rule.content
        assert restored_rule.rule_id == original_rule.rule_id
        assert restored_rule.priority == original_rule.priority
    
    def test_meta_rule_source_management(self):
        """Test meta-rule source learnt ID management."""
        meta_rule = Rule.create_meta_rule("Test Meta", "Content")
        
        # Test adding source learnt IDs
        meta_rule.add_source_learnt_id("learnt-1")
        meta_rule.add_source_learnt_id("learnt-2")
        
        assert "learnt-1" in meta_rule.source_learnt_ids
        assert "learnt-2" in meta_rule.source_learnt_ids
        assert len(meta_rule.source_learnt_ids) == 2
        
        # Test removing source learnt IDs
        removed = meta_rule.remove_source_learnt_id("learnt-1")
        assert removed
        assert "learnt-1" not in meta_rule.source_learnt_ids
        assert len(meta_rule.source_learnt_ids) == 1
        
        # Test removing non-existent ID
        removed = meta_rule.remove_source_learnt_id("non-existent")
        assert not removed
    
    def test_regular_rule_meta_restrictions(self):
        """Test that regular rules cannot have meta-rule attributes."""
        regular_rule = Rule(rule_name="Regular", content="Content")
        
        # Regular rules shouldn't be able to manage source learnt IDs
        with pytest.raises(ValueError, match="Only meta-rules can have source learnt IDs"):
            regular_rule.add_source_learnt_id("learnt-1")
        
        with pytest.raises(ValueError, match="Only meta-rules can have source learnt IDs"):
            regular_rule.remove_source_learnt_id("learnt-1")


class TestLearntModel:
    """Test suite for Learnt model functionality."""
    
    def test_learnt_creation_basic(self):
        """Test basic learnt experience creation."""
        learnt = Learnt.create_from_error(
            error_type="IncorrectAction",
            problem_summary="AI made wrong suggestion",
            problematic_input="User asked for help",
            problematic_output="Bad advice given",
            root_cause="Outdated training data",
            severity="major",
            solution="Updated approach needed"
        )
        
        assert learnt.type_of_error == ErrorType.INCORRECT_ACTION
        assert learnt.problem_summary == "AI made wrong suggestion"
        assert learnt.original_severity == SeverityLevel.MAJOR
        assert len(learnt.learnt_id) == 36  # UUID format
        assert isinstance(learnt.timestamp_recorded, datetime)
        assert not learnt.contributed_to_meta_rule
        assert learnt.meta_rule_contribution is None
    
    def test_learnt_validation(self):
        """Test learnt experience validation."""
        # Test empty problem summary
        with pytest.raises(ValueError):
            Learnt.create_from_error(
                error_type="IncorrectAction",
                problem_summary="",
                problematic_input="Input",
                problematic_output="Output", 
                root_cause="Cause",
                severity="major",
                solution="Solution"
            )
    
    def test_learnt_meta_rule_trigger(self):
        """Test meta-rule update triggering."""
        learnt = Learnt.create_from_error(
            error_type="IncorrectAction",
            problem_summary="Test problem",
            problematic_input="Test input",
            problematic_output="Test output",
            root_cause="Test cause",
            severity="major",
            solution="Test solution"
        )
        
        # Test triggering meta-rule update
        result = learnt.trigger_meta_rule_update()
        
        assert result
        assert learnt.contributed_to_meta_rule
        assert learnt.meta_rule_contribution is not None
        assert "To avoid incorrectaction: Test problem" in learnt.meta_rule_contribution
    
    def test_learnt_serialization(self):
        """Test learnt serialization and deserialization."""
        original_learnt = Learnt.create_from_error(
            error_type="Misunderstanding",
            problem_summary="Serialization test",
            problematic_input="Input test",
            problematic_output="Output test",
            root_cause="Cause test",
            severity="critical",
            solution="Solution test"
        )
        
        # Test to_dict
        learnt_dict = original_learnt.to_dict()
        
        assert learnt_dict["problem_summary"] == "Serialization test"
        assert learnt_dict["type_of_error"] == "Misunderstanding"
        assert "timestamp_recorded" in learnt_dict
        
        # Test from_dict
        restored_learnt = Learnt.from_dict(learnt_dict)
        
        assert restored_learnt.problem_summary == original_learnt.problem_summary
        assert restored_learnt.learnt_id == original_learnt.learnt_id
        assert restored_learnt.type_of_error == original_learnt.type_of_error
    
    def test_learnt_callback_system(self):
        """Test callback system for meta-rule updates."""
        learnt = Learnt.create_from_error(
            error_type="IncorrectAction",
            problem_summary="Callback test",
            problematic_input="Input",
            problematic_output="Output",
            root_cause="Cause",
            severity="major",
            solution="Solution"
        )
        
        # Set up mock callback
        callback_mock = Mock()
        learnt.set_meta_rule_update_callback(callback_mock)
        
        # Trigger update
        result = learnt.trigger_meta_rule_update()
        
        assert result
        callback_mock.assert_called_once_with(learnt)
    
    def test_learnt_verification_status_updates(self):
        """Test verification status update functionality."""
        learnt = Learnt.create_from_error(
            error_type="IncorrectAction",
            problem_summary="Verification test",
            problematic_input="Input",
            problematic_output="Output",
            root_cause="Cause",
            severity="major",
            solution="Solution"
        )
        
        # Test status update
        learnt.update_verification_status("validated")
        assert learnt.verification_status == "validated"
        
        # Test invalid status
        with pytest.raises(ValueError, match="Status must be one of"):
            learnt.update_verification_status("invalid_status")


class TestMetaRuleManager:
    """Test suite for MetaRuleManager functionality."""
    
    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = MetaRuleManager()
        
        assert manager.meta_rule is None
        assert manager.tracked_learnt_count == 0
        assert isinstance(manager.logger, type(manager.logger))  # Logger type check
    
    def test_meta_rule_initialization(self):
        """Test meta-rule initialization by manager."""
        manager = MetaRuleManager()
        meta_rule = manager.initialize_meta_rule()
        
        assert meta_rule is not None
        assert meta_rule.is_meta_rule
        assert meta_rule.rule_name == manager.DEFAULT_META_RULE_NAME
        assert meta_rule.content == manager.DEFAULT_META_RULE_CONTENT
        assert manager.meta_rule == meta_rule
    
    def test_meta_rule_ensure_exists(self):
        """Test ensure meta-rule exists functionality."""
        manager = MetaRuleManager()
        
        # First call should create meta-rule
        meta_rule1 = manager.ensure_meta_rule_exists()
        assert meta_rule1 is not None
        
        # Second call should return same meta-rule
        meta_rule2 = manager.ensure_meta_rule_exists()
        assert meta_rule1 == meta_rule2
    
    def test_add_learnt_experience_success(self):
        """Test successful addition of learnt experience."""
        manager = MetaRuleManager()
        learnt = Learnt.create_from_error(
            error_type="IncorrectAction",
            problem_summary="Manager test problem",
            problematic_input="Input",
            problematic_output="Output",
            root_cause="Cause",
            severity="major",
            solution="Solution"
        )
        
        result = manager.add_learnt_experience(learnt)
        
        assert result
        assert manager.tracked_learnt_count == 1
        assert learnt.learnt_id in manager._tracked_learnt_nodes
        assert learnt.contributed_to_meta_rule
        
        # Check meta-rule was updated
        meta_rule = manager.meta_rule
        assert meta_rule is not None
        assert learnt.learnt_id in meta_rule.source_learnt_ids
    
    def test_add_learnt_experience_duplicate(self):
        """Test handling of duplicate learnt experiences."""
        manager = MetaRuleManager()
        learnt = Learnt.create_from_error(
            error_type="IncorrectAction",
            problem_summary="Duplicate test",
            problematic_input="Input",
            problematic_output="Output",
            root_cause="Cause",
            severity="major",
            solution="Solution"
        )
        
        # Add first time
        result1 = manager.add_learnt_experience(learnt)
        assert result1
        
        # Add second time (duplicate)
        result2 = manager.add_learnt_experience(learnt)
        assert not result2  # Should return False for duplicate
        
        # Count should still be 1
        assert manager.tracked_learnt_count == 1
    
    def test_add_non_validated_learnt(self):
        """Test that non-validated learnt experiences are skipped."""
        manager = MetaRuleManager()
        learnt = Learnt.create_from_error(
            error_type="IncorrectAction",
            problem_summary="Non-validated test",
            problematic_input="Input",
            problematic_output="Output",
            root_cause="Cause",
            severity="major",
            solution="Solution"
        )
        
        # Set to non-validated status
        learnt.verification_status = "pending"
        
        result = manager.add_learnt_experience(learnt)
        
        assert not result  # Should return False for non-validated
        assert manager.tracked_learnt_count == 0
    
    def test_aggregation_summary(self):
        """Test aggregation summary generation."""
        manager = MetaRuleManager()
        
        # Add multiple learnt experiences
        learnt1 = Learnt.create_from_error("IncorrectAction", "Problem 1", "I1", "O1", "C1", "major", "S1")
        learnt2 = Learnt.create_from_error("Misunderstanding", "Problem 2", "I2", "O2", "C2", "critical", "S2")
        
        manager.add_learnt_experience(learnt1)
        manager.add_learnt_experience(learnt2)
        
        summary = manager.get_aggregation_summary()
        
        assert summary["meta_rule_exists"]
        assert summary["tracked_learnt_count"] == 2
        assert len(summary["tracked_learnt_ids"]) == 2
        assert learnt1.learnt_id in summary["tracked_learnt_ids"]
        assert learnt2.learnt_id in summary["tracked_learnt_ids"]
        assert summary["aggregation_stats"]["total_learnt"] == 2
    
    def test_learning_insights(self):
        """Test learning insights generation."""
        manager = MetaRuleManager()
        
        # Add learnt experiences with different patterns
        learnt1 = Learnt.create_from_error("IncorrectAction", "Problem 1", "I1", "O1", "C1", "major", "S1")
        learnt2 = Learnt.create_from_error("IncorrectAction", "Problem 2", "I2", "O2", "C2", "critical", "S2")
        learnt3 = Learnt.create_from_error("Misunderstanding", "Problem 3", "I3", "O3", "C3", "minor", "S3")
        
        manager.add_learnt_experience(learnt1)
        manager.add_learnt_experience(learnt2) 
        manager.add_learnt_experience(learnt3)
        
        insights = manager.get_learning_insights()
        
        assert insights["total_experiences"] == 3
        assert insights["most_common_error"]["type"] == "IncorrectAction"
        assert insights["most_common_error"]["count"] == 2
        assert insights["most_common_error"]["percentage"] == pytest.approx(66.7, abs=0.1)
        assert len(insights["recommendations"]) > 0
    
    def test_meta_rule_content_update(self):
        """Test meta-rule content generation and updates."""
        manager = MetaRuleManager()
        
        # Add learnt experience
        learnt = Learnt.create_from_error(
            error_type="IncorrectAction",
            problem_summary="Content update test",
            problematic_input="Input",
            problematic_output="Output",
            root_cause="Cause",
            severity="major",
            solution="Solution"
        )
        
        manager.add_learnt_experience(learnt)
        
        meta_rule = manager.meta_rule
        content = meta_rule.content
        
        # Verify content contains expected sections
        assert "AI Learning Aggregator" in content
        assert "Total learnt experiences processed: 1" in content
        assert "Common Error Types:" in content
        assert "IncorrectAction: 1 occurrences" in content
        assert "Actionable Guidance:" in content
        assert "Meta-Learning Principles:" in content
    
    def test_export_import_knowledge(self):
        """Test knowledge export and import functionality."""
        manager = MetaRuleManager()
        
        # Add learnt experience
        learnt = Learnt.create_from_error("IncorrectAction", "Export test", "I", "O", "C", "major", "S")
        manager.add_learnt_experience(learnt)
        
        # Export knowledge
        export_data = manager.export_meta_rule_knowledge()
        
        assert export_data["meta_rule"] is not None
        assert len(export_data["tracked_learnt_ids"]) == 1
        assert export_data["aggregation_stats"]["total_learnt"] == 1
        assert "export_timestamp" in export_data
        
        # Create new manager and import
        new_manager = MetaRuleManager()
        result = new_manager.import_meta_rule_knowledge(export_data)
        
        assert result
        assert new_manager.tracked_learnt_count == 1
        assert new_manager.meta_rule is not None
        assert new_manager._aggregation_stats["total_learnt"] == 1
    
    def test_reset_meta_rule(self):
        """Test meta-rule system reset."""
        manager = MetaRuleManager()
        
        # Add data
        learnt = Learnt.create_from_error("IncorrectAction", "Reset test", "I", "O", "C", "major", "S")
        manager.add_learnt_experience(learnt)
        
        assert manager.tracked_learnt_count == 1
        
        # Reset
        manager.reset_meta_rule()
        
        assert manager.tracked_learnt_count == 0
        assert manager.meta_rule is not None  # Should create new meta-rule
        assert len(manager._aggregation_stats) == 0
    
    def test_remove_learnt_experience(self):
        """Test removal of learnt experiences."""
        manager = MetaRuleManager()
        
        learnt = Learnt.create_from_error("IncorrectAction", "Remove test", "I", "O", "C", "major", "S")
        manager.add_learnt_experience(learnt)
        
        assert manager.tracked_learnt_count == 1
        
        # Remove learnt experience
        result = manager.remove_learnt_experience(learnt.learnt_id)
        
        assert result
        assert manager.tracked_learnt_count == 0
        assert learnt.learnt_id not in manager.meta_rule.source_learnt_ids
        
        # Try removing non-existent
        result = manager.remove_learnt_experience("non-existent")
        assert not result


class TestModelIntegration:
    """Integration tests for model interactions."""
    
    def test_end_to_end_learning_workflow(self):
        """Test complete end-to-end learning workflow."""
        # Initialize system
        manager = MetaRuleManager()
        
        # Create multiple learning experiences
        experiences = [
            ("IncorrectAction", "AI suggested deprecated method", "How to handle state?", "Use setState", "Old React knowledge", "major", "Use useState hook"),
            ("Misunderstanding", "AI misunderstood user intent", "Can you help with auth?", "Here's a recipe", "Context confusion", "critical", "Ask clarifying questions"),
            ("IncorrectAction", "AI gave wrong library version", "Latest React version?", "React 16", "Outdated training", "minor", "Check latest docs"),
        ]
        
        learnt_experiences = []
        for error_type, problem, input_seg, output_seg, cause, severity, solution in experiences:
            learnt = Learnt.create_from_error(error_type, problem, input_seg, output_seg, cause, severity, solution)
            learnt_experiences.append(learnt)
            
            # Add to manager
            result = manager.add_learnt_experience(learnt)
            assert result
        
        # Verify complete integration
        assert manager.tracked_learnt_count == 3
        
        # Check meta-rule integration
        meta_rule = manager.meta_rule
        assert len(meta_rule.source_learnt_ids) == 3
        
        # Verify all learnt experiences contributed
        for learnt in learnt_experiences:
            assert learnt.contributed_to_meta_rule
            assert learnt.meta_rule_contribution is not None
        
        # Check aggregation insights
        insights = manager.get_learning_insights()
        assert insights["total_experiences"] == 3
        assert insights["most_common_error"]["type"] == "IncorrectAction"
        assert len(insights["recommendations"]) > 0
        
        # Verify meta-rule content includes all experiences
        content = meta_rule.content
        assert "IncorrectAction: 2 occurrences" in content
        assert "Misunderstanding: 1 occurrences" in content
        assert "major: 1 occurrences" in content
        assert "critical: 1 occurrences" in content
    
    def test_meta_rule_aggregation_algorithm(self):
        """Test the meta-rule aggregation algorithm with edge cases."""
        manager = MetaRuleManager()
        
        # Test with no experiences
        summary = manager.get_aggregation_summary()
        assert summary["tracked_learnt_count"] == 0
        
        insights = manager.get_learning_insights()
        assert insights["message"] == "No learning data available yet"
        
        # Add single experience
        learnt = Learnt.create_from_error("IncorrectAction", "Single test", "I", "O", "C", "major", "S")
        manager.add_learnt_experience(learnt)
        
        insights = manager.get_learning_insights()
        assert insights["total_experiences"] == 1
        assert insights["most_common_error"]["percentage"] == 100.0
        
        # Test effectiveness metrics
        effectiveness = manager.get_meta_rule_effectiveness()
        assert effectiveness["overall_rating"] == "insufficient_data"
        
        # Add more experiences to reach different rating levels
        for i in range(20):
            learnt = Learnt.create_from_error(
                error_type="IncorrectAction" if i % 2 == 0 else "Misunderstanding",
                problem_summary=f"Problem {i}",
                problematic_input=f"Input {i}",
                problematic_output=f"Output {i}",
                root_cause=f"Cause {i}",
                severity="major" if i % 3 == 0 else "minor",
                solution=f"Solution {i}"
            )
            manager.add_learnt_experience(learnt)
        
        effectiveness = manager.get_meta_rule_effectiveness()
        assert effectiveness["overall_rating"] == "mature"
        assert effectiveness["data_coverage"]["total_experiences"] == 21
    
    def test_concurrent_learning_simulation(self):
        """Simulate concurrent learning scenarios."""
        manager = MetaRuleManager()
        
        # Simulate rapid addition of experiences
        experiences = []
        for i in range(10):
            learnt = Learnt.create_from_error(
                error_type=["IncorrectAction", "Misunderstanding", "UnmetUserGoal"][i % 3],
                problem_summary=f"Concurrent problem {i}",
                problematic_input=f"Input {i}",
                problematic_output=f"Output {i}",
                root_cause=f"Cause {i}",
                severity=["critical", "major", "minor"][i % 3],
                solution=f"Solution {i}"
            )
            experiences.append(learnt)
        
        # Add all experiences
        results = []
        for learnt in experiences:
            result = manager.add_learnt_experience(learnt)
            results.append(result)
        
        # All should succeed
        assert all(results)
        assert manager.tracked_learnt_count == 10
        
        # Verify consistency
        meta_rule = manager.meta_rule
        assert len(meta_rule.source_learnt_ids) == 10
        
        # Check aggregation stats consistency
        stats = manager._aggregation_stats
        total_errors = sum(stats["error_types"].values())
        total_severities = sum(stats["severity_levels"].values())
        
        assert total_errors == 10
        assert total_severities == 10
        assert stats["total_learnt"] == 10
    
    def test_error_handling_and_recovery(self):
        """Test error handling and system recovery."""
        manager = MetaRuleManager()
        
        # Test with invalid learnt experience
        invalid_learnt = Learnt.create_from_error("IncorrectAction", "Valid problem", "I", "O", "C", "major", "S")
        
        # Simulate callback error
        def failing_callback(learnt):
            raise Exception("Simulated callback failure")
        
        invalid_learnt.set_meta_rule_update_callback(failing_callback)
        
        # Should handle error gracefully
        result = manager.add_learnt_experience(invalid_learnt)
        assert not result  # Should fail gracefully
        
        # System should remain functional
        valid_learnt = Learnt.create_from_error("IncorrectAction", "Valid problem 2", "I", "O", "C", "major", "S")
        result = manager.add_learnt_experience(valid_learnt)
        assert result  # Should work normally
        
        assert manager.tracked_learnt_count == 1
    
    def test_serialization_integration(self):
        """Test serialization across all models in integration."""
        # Create complete system state
        manager = MetaRuleManager()
        
        learnt = Learnt.create_from_error("IncorrectAction", "Serialization integration", "I", "O", "C", "major", "S")
        manager.add_learnt_experience(learnt)
        
        # Export everything
        manager_export = manager.export_meta_rule_knowledge()
        learnt_dict = learnt.to_dict()
        meta_rule_dict = manager.meta_rule.to_dict()
        
        # Verify all can be restored
        restored_learnt = Learnt.from_dict(learnt_dict)
        restored_meta_rule = Rule.from_dict(meta_rule_dict)
        
        new_manager = MetaRuleManager()
        import_result = new_manager.import_meta_rule_knowledge(manager_export)
        
        assert import_result
        assert restored_learnt.learnt_id == learnt.learnt_id
        assert restored_meta_rule.rule_id == manager.meta_rule.rule_id
        assert new_manager.tracked_learnt_count == manager.tracked_learnt_count


# Pytest fixtures and test runners
@pytest.fixture
def sample_rule():
    """Create a sample rule for testing."""
    return Rule(
        rule_name="Sample Rule",
        content="Sample rule content",
        category=RuleCategory.FRONTEND,
        priority=7,
        tags=["test", "sample"]
    )


@pytest.fixture
def sample_learnt():
    """Create a sample learnt experience for testing."""
    return Learnt.create_from_error(
        error_type="IncorrectAction",
        problem_summary="Sample AI error",
        problematic_input="User asked for help",
        problematic_output="AI gave wrong answer",
        root_cause="Insufficient context",
        severity="major",
        solution="Gather more context before responding"
    )


@pytest.fixture
def sample_manager():
    """Create a sample meta-rule manager for testing."""
    manager = MetaRuleManager()
    manager.initialize_meta_rule()
    return manager


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v", "--tb=short"]) 