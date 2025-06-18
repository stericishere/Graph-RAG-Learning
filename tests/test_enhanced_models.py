#!/usr/bin/env python3
"""
Enhanced Professional Test Suite for Final Minimal Lean Graph Database MCP Models.

This comprehensive test suite uses pytest fixtures, parametrization, and advanced testing
techniques to validate the Rule, Learnt, and MetaRuleManager components.
"""

import pytest
import time
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, '.')

from src.models import Rule, Learnt, MetaRuleManager
from src.models.rule import RuleCategory, RuleType
from src.models.learnt import ErrorType, SeverityLevel


# ================================
# Test Configuration & Fixtures
# ================================

@dataclass
class TestConfig:
    """Test configuration for enhanced testing scenarios."""
    stress_test_size: int = 100
    concurrent_workers: int = 10
    performance_timeout: float = 5.0


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return TestConfig()


@pytest.fixture
def clean_manager():
    """Provide a clean MetaRuleManager instance for each test."""
    return MetaRuleManager()


@pytest.fixture(params=[
    ("IncorrectAction", "major"),
    ("Misunderstanding", "critical"),
    ("UnmetUserGoal", "minor"),
    ("InvalidResponse", "critical"),
])
def sample_error_types(request):
    """Parametrized fixture providing various error types and severities."""
    return request.param


# ================================
# Performance Testing
# ================================

class TestPerformance:
    """Performance testing for model operations."""
    
    @pytest.mark.parametrize("operation_count", [10, 50, 100])
    def test_rule_creation_performance(self, operation_count, test_config):
        """Test rule creation performance under various loads."""
        start_time = time.time()
        
        rules = []
        for i in range(operation_count):
            rule = Rule(
                rule_name=f"Performance Test Rule {i}",
                content=f"Test content for rule {i}"
            )
            rules.append(rule)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert execution_time < test_config.performance_timeout
        assert len(rules) == operation_count
        
        # Validate all rules are properly created
        for rule in rules:
            assert len(rule.rule_id) == 36  # UUID format
            assert rule.rule_name.startswith("Performance Test Rule")

    def test_meta_rule_content_generation_performance(self, clean_manager, test_config):
        """Test meta-rule content generation performance with large datasets."""
        manager = clean_manager
        manager.initialize_meta_rule()
        
        # Add diverse learning experiences
        error_types = ["IncorrectAction", "Misunderstanding", "UnmetUserGoal", "InvalidResponse"]
        severities = ["critical", "major", "minor", "low"]
        
        start_time = time.time()
        
        for i in range(test_config.stress_test_size):
            error_type = error_types[i % len(error_types)]
            severity = severities[i % len(severities)]
            
            learnt = Learnt.create_from_error(
                error_type=error_type,
                problem_summary=f"Performance test problem {i}",
                problematic_input=f"Input {i}",
                problematic_output=f"Output {i}",
                root_cause=f"Cause {i}",
                severity=severity,
                solution=f"Solution {i}"
            )
            manager.add_learnt_experience(learnt)
        
        # Trigger content generation
        insights = manager.get_learning_insights()
        content = manager.meta_rule.content
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Performance assertions
        assert execution_time < test_config.performance_timeout * 2
        assert len(content) > 1000  # Should generate substantial content
        assert insights["total_experiences"] == test_config.stress_test_size


# ================================
# Concurrent Operations Testing
# ================================

class TestConcurrency:
    """Test concurrent operations and thread safety."""
    
    def test_concurrent_rule_creation(self, test_config):
        """Test concurrent rule creation across multiple threads."""
        rules_created = []
        creation_errors = []
        
        def create_rule_batch(batch_id: int, batch_size: int):
            """Create a batch of rules in a thread."""
            try:
                batch_rules = []
                for i in range(batch_size):
                    rule = Rule(
                        rule_name=f"Concurrent Rule {batch_id}-{i}",
                        content=f"Concurrent test content {batch_id}-{i}"
                    )
                    batch_rules.append(rule)
                return batch_rules
            except Exception as e:
                creation_errors.append(e)
                return []
        
        # Execute concurrent rule creation
        with ThreadPoolExecutor(max_workers=test_config.concurrent_workers) as executor:
            futures = []
            batch_size = 10
            
            for batch_id in range(test_config.concurrent_workers):
                future = executor.submit(create_rule_batch, batch_id, batch_size)
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                batch_rules = future.result()
                rules_created.extend(batch_rules)
        
        # Validation
        assert len(creation_errors) == 0, f"Errors during concurrent creation: {creation_errors}"
        assert len(rules_created) == test_config.concurrent_workers * batch_size
        
        # Verify all UUIDs are unique
        rule_ids = [rule.rule_id for rule in rules_created]
        assert len(set(rule_ids)) == len(rule_ids), "Duplicate rule IDs found"


# ================================
# Edge Cases and Error Handling
# ================================

class TestEdgeCases:
    """Test edge cases and error handling scenarios."""
    
    @pytest.mark.parametrize("invalid_input", [
        "",  # Empty string
        "   ",  # Whitespace only
        "a" * 10000,  # Very long string
    ])
    def test_rule_creation_invalid_inputs(self, invalid_input):
        """Test rule creation with various invalid inputs."""
        with pytest.raises(ValueError):
            Rule(rule_name=invalid_input, content="Valid content")

    def test_extreme_meta_rule_aggregation(self, clean_manager):
        """Test meta-rule aggregation with extreme scenarios."""
        manager = clean_manager
        manager.initialize_meta_rule()
        
        # Test with identical experiences
        for i in range(50):
            learnt = Learnt.create_from_error(
                error_type="IncorrectAction",
                problem_summary="Identical problem",
                problematic_input="Identical input",
                problematic_output="Identical output",
                root_cause="Identical cause",
                severity="major",
                solution="Identical solution"
            )
            manager.add_learnt_experience(learnt)
        
        insights = manager.get_learning_insights()
        content = manager.meta_rule.content
        
        # Should handle identical experiences gracefully
        assert insights["total_experiences"] == 50
        assert "IncorrectAction: 50 occurrences" in content
        assert manager.tracked_learnt_count == 50

    def test_unicode_and_special_characters(self, clean_manager):
        """Test handling of unicode and special characters."""
        manager = clean_manager
        manager.initialize_meta_rule()
        
        # Test with unicode characters
        unicode_learnt = Learnt.create_from_error(
            error_type="IncorrectAction",
            problem_summary="Unicode test: 🤖 AI failed with émojis",
            problematic_input="Input with 中文 and العربية",
            problematic_output="Output with Ñoño and Żółć",
            root_cause="Encoding issues with ñ and ü",
            severity="major",
            solution="Use proper UTF-8 encoding"
        )
        
        result = manager.add_learnt_experience(unicode_learnt)
        assert result
        
        # Verify content generation handles unicode
        content = manager.meta_rule.content
        assert "Unicode test" in content or "AI Learning Aggregator" in content
        assert manager.tracked_learnt_count == 1


# ================================
# Integration Testing
# ================================

class TestIntegration:
    """Integration tests for complete system workflows."""
    
    def test_complete_learning_lifecycle(self, clean_manager):
        """Test complete learning lifecycle from error to meta-rule."""
        manager = clean_manager
        
        # Phase 1: Initialize system
        meta_rule = manager.initialize_meta_rule()
        assert meta_rule.is_meta_rule
        assert len(meta_rule.content) > 0  # Has content
        
        # Phase 2: Add learning experiences
        sample_data = [
            {
                "error_type": "IncorrectAction",
                "problem_summary": "AI suggested deprecated method",
                "problematic_input": "How to handle state?",
                "problematic_output": "Use setState",
                "root_cause": "Old React knowledge",
                "severity": "major",
                "solution": "Use useState hook"
            },
            {
                "error_type": "InvalidResponse",
                "problem_summary": "Provided incorrect information",
                "problematic_input": "What's the capital of France?",
                "problematic_output": "London",
                "root_cause": "Knowledge error",
                "severity": "critical",
                "solution": "Verify facts before responding"
            }
        ]
        
        learnt_experiences = []
        for i, data in enumerate(sample_data):
            learnt = Learnt.create_from_error(**data)
            learnt_experiences.append(learnt)
            
            result = manager.add_learnt_experience(learnt)
            assert result
            
            # Verify progressive state
            assert manager.tracked_learnt_count == i + 1
            assert learnt.learnt_id in manager.meta_rule.source_learnt_ids
        
        # Phase 3: Analyze learning insights
        insights = manager.get_learning_insights()
        assert insights["total_experiences"] == len(sample_data)
        assert "most_common_error" in insights
        
        # Phase 4: Export and import knowledge
        export_data = manager.export_meta_rule_knowledge()
        assert "meta_rule" in export_data
        assert "tracked_learnt_ids" in export_data
        
        new_manager = MetaRuleManager()
        import_result = new_manager.import_meta_rule_knowledge(export_data)
        assert import_result
        assert new_manager.tracked_learnt_count == len(sample_data)


# ================================
# Benchmark Tests
# ================================

class TestBenchmarks:
    """Benchmark tests for performance measurement."""
    
    def test_rule_serialization_benchmark(self):
        """Benchmark rule serialization performance."""
        rules = []
        for i in range(1000):
            rule = Rule(
                rule_name=f"Benchmark Rule {i}",
                content=f"Benchmark content {i}"
            )
            rules.append(rule)
        
        # Benchmark serialization
        start_time = time.time()
        serialized_rules = [rule.to_dict() for rule in rules]
        serialization_time = time.time() - start_time
        
        # Benchmark deserialization
        start_time = time.time()
        deserialized_rules = [Rule.from_dict(rule_dict) for rule_dict in serialized_rules]
        deserialization_time = time.time() - start_time
        
        # Performance assertions
        assert serialization_time < 1.0  # Should complete within 1 second
        assert deserialization_time < 1.0
        assert len(deserialized_rules) == 1000
        
        # Verify fidelity
        for original, deserialized in zip(rules, deserialized_rules):
            assert original.rule_id == deserialized.rule_id
            assert original.rule_name == deserialized.rule_name
            assert original.content == deserialized.content
            assert original.category == deserialized.category
            assert original.rule_type == deserialized.rule_type
            assert original.is_meta_rule == deserialized.is_meta_rule 