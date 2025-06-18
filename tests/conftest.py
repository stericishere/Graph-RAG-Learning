#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for the enhanced test suite.

This module provides common fixtures, utilities, and configuration
for all test modules in the test suite.
"""

import pytest
import sys
import time
import gc
from typing import Generator, Dict, Any, List
from dataclasses import dataclass, field

# Add src to path for all tests
sys.path.insert(0, '.')

from src.models import Rule, Learnt, MetaRuleManager
from src.models.rule import RuleCategory, RuleType
from src.models.learnt import ErrorType, SeverityLevel


# ================================
# Test Configuration
# ================================

@dataclass
class TestConfigurationProfile:
    """Configuration profile for different test scenarios."""
    name: str
    description: str
    
    # Performance settings
    max_execution_time: float = 5.0
    stress_test_size: int = 100
    benchmark_iterations: int = 1000
    
    # Concurrency settings
    max_workers: int = 10
    concurrent_batch_size: int = 5
    thread_safety_workers: int = 5
    
    # Memory settings
    memory_threshold_mb: float = 100.0
    large_dataset_size: int = 1000
    
    # Test data settings
    error_type_variants: List[str] = field(default_factory=lambda: [
        "IncorrectAction", "Misunderstanding", "UnmetUserGoal", "InvalidResponse"
    ])
    severity_variants: List[str] = field(default_factory=lambda: [
        "critical", "major", "minor", "low"
    ])


# Test configuration profiles
TEST_PROFILES = {
    "fast": TestConfigurationProfile(
        name="fast",
        description="Quick test configuration for development",
        max_execution_time=2.0,
        stress_test_size=25,
        benchmark_iterations=100,
        max_workers=5,
        memory_threshold_mb=50.0,
        large_dataset_size=100
    ),
    "standard": TestConfigurationProfile(
        name="standard", 
        description="Standard test configuration for CI/CD",
        max_execution_time=5.0,
        stress_test_size=100,
        benchmark_iterations=1000,
        max_workers=10,
        memory_threshold_mb=100.0,
        large_dataset_size=1000
    ),
    "comprehensive": TestConfigurationProfile(
        name="comprehensive",
        description="Comprehensive test configuration for thorough validation",
        max_execution_time=15.0,
        stress_test_size=500,
        benchmark_iterations=5000,
        max_workers=20,
        memory_threshold_mb=200.0,
        large_dataset_size=5000
    )
}


# ================================
# Core Fixtures
# ================================

@pytest.fixture(scope="session")
def test_profile():
    """Get test configuration profile from environment or default to standard."""
    import os
    profile_name = os.environ.get("TEST_PROFILE", "standard")
    return TEST_PROFILES.get(profile_name, TEST_PROFILES["standard"])


@pytest.fixture
def clean_manager() -> Generator[MetaRuleManager, None, None]:
    """Provide a clean MetaRuleManager instance for each test."""
    manager = MetaRuleManager()
    yield manager
    
    # Cleanup after test
    try:
        if manager.meta_rule is not None:
            manager.reset_meta_rule()
    except Exception:
        pass  # Ignore cleanup errors
    
    # Force garbage collection
    del manager
    gc.collect()


@pytest.fixture
def initialized_manager(clean_manager) -> MetaRuleManager:
    """Provide a MetaRuleManager with initialized meta-rule."""
    manager = clean_manager
    manager.initialize_meta_rule()
    return manager


# ================================
# Data Generation Fixtures
# ================================

@pytest.fixture
def sample_rule_factory():
    """Factory for creating sample rules with various configurations."""
    def create_rule(
        rule_type: str = "basic",
        category: RuleCategory = RuleCategory.GENERAL,
        rule_type_enum: RuleType = RuleType.GUIDELINE,
        is_meta: bool = False
    ) -> Rule:
        if rule_type == "basic":
            return Rule(
                rule_name="Basic Test Rule",
                content="Basic rule content for testing"
            )
        elif rule_type == "complex":
            return Rule(
                rule_name="Complex Test Rule",
                content="Complex rule with detailed requirements and constraints",
                category=category,
                rule_type=rule_type_enum,
                priority=1
            )
        elif rule_type == "meta":
            return Rule.create_meta_rule(
                rule_name="Meta Test Rule",
                content="Meta rule for testing aggregation"
            )
        else:
            raise ValueError(f"Unknown rule type: {rule_type}")
    
    return create_rule


@pytest.fixture
def sample_learnt_factory():
    """Factory for creating sample learnt experiences."""
    def create_learnt(
        error_type: str = "IncorrectAction",
        severity: str = "major",
        problem_prefix: str = "Test problem",
        unique_id: str = ""
    ) -> Learnt:
        suffix = f" {unique_id}" if unique_id else ""
        
        return Learnt.create_from_error(
            error_type=error_type,
            problem_summary=f"{problem_prefix}{suffix}",
            problematic_input=f"Test input{suffix}",
            problematic_output=f"Test output{suffix}",
            root_cause=f"Test root cause{suffix}",
            severity=severity,
            solution=f"Test solution{suffix}"
        )
    
    return create_learnt


@pytest.fixture
def diverse_learnt_dataset(sample_learnt_factory, test_profile):
    """Generate a diverse dataset of learnt experiences."""
    dataset = []
    
    for i in range(min(50, test_profile.stress_test_size)):
        error_type = test_profile.error_type_variants[i % len(test_profile.error_type_variants)]
        severity = test_profile.severity_variants[i % len(test_profile.severity_variants)]
        
        learnt = sample_learnt_factory(
            error_type=error_type,
            severity=severity,
            problem_prefix=f"Dataset problem {i}",
            unique_id=str(i)
        )
        dataset.append(learnt)
    
    return dataset


# ================================
# Performance Monitoring Fixtures
# ================================

@pytest.fixture
def performance_monitor():
    """Monitor performance metrics during test execution."""
    import psutil
    import os
    
    class PerformanceMonitor:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.initial_memory = self.get_memory_usage()
            self.start_time = None
            self.measurements = []
        
        def start_measurement(self):
            """Start performance measurement."""
            self.start_time = time.time()
            self.initial_memory = self.get_memory_usage()
        
        def stop_measurement(self) -> Dict[str, float]:
            """Stop measurement and return metrics."""
            if self.start_time is None:
                raise ValueError("Measurement not started")
            
            end_time = time.time()
            final_memory = self.get_memory_usage()
            
            metrics = {
                "execution_time": end_time - self.start_time,
                "memory_growth": final_memory - self.initial_memory,
                "peak_memory": final_memory,
                "initial_memory": self.initial_memory
            }
            
            self.measurements.append(metrics)
            self.start_time = None
            
            return metrics
        
        def get_memory_usage(self) -> float:
            """Get current memory usage in MB."""
            return self.process.memory_info().rss / 1024 / 1024
        
        def get_cpu_usage(self) -> float:
            """Get current CPU usage percentage."""
            return self.process.cpu_percent()
        
        def assert_performance_within_bounds(
            self, 
            metrics: Dict[str, float], 
            max_time: float, 
            max_memory_growth: float
        ):
            """Assert that performance metrics are within acceptable bounds."""
            assert metrics["execution_time"] < max_time, (
                f"Execution time {metrics['execution_time']:.2f}s exceeds limit {max_time}s"
            )
            assert metrics["memory_growth"] < max_memory_growth, (
                f"Memory growth {metrics['memory_growth']:.2f}MB exceeds limit {max_memory_growth}MB"
            )
    
    return PerformanceMonitor()


# ================================
# Validation Utilities
# ================================

@pytest.fixture
def validation_utils():
    """Provide validation utilities for test assertions."""
    
    class ValidationUtils:
        @staticmethod
        def assert_valid_uuid(uuid_string: str):
            """Assert that a string is a valid UUID."""
            import uuid
            try:
                uuid.UUID(uuid_string)
                assert len(uuid_string) == 36
            except ValueError:
                pytest.fail(f"Invalid UUID format: {uuid_string}")
        
        @staticmethod
        def assert_rule_integrity(rule: Rule):
            """Assert that a rule maintains data integrity."""
            assert rule.rule_name is not None and rule.rule_name.strip() != ""
            assert rule.content is not None and rule.content.strip() != ""
            assert isinstance(rule.category, RuleCategory)
            assert isinstance(rule.rule_type, RuleType)
            ValidationUtils.assert_valid_uuid(rule.rule_id)
        
        @staticmethod
        def assert_learnt_integrity(learnt: Learnt):
            """Assert that a learnt experience maintains data integrity."""
            assert learnt.problem_summary is not None and learnt.problem_summary.strip() != ""
            assert isinstance(learnt.type_of_error, ErrorType)
            assert isinstance(learnt.original_severity, SeverityLevel)
            ValidationUtils.assert_valid_uuid(learnt.learnt_id)
            assert learnt.timestamp_recorded is not None
        
        @staticmethod
        def assert_meta_rule_manager_integrity(manager: MetaRuleManager):
            """Assert that a MetaRuleManager maintains data integrity."""
            if manager.meta_rule is not None:
                ValidationUtils.assert_rule_integrity(manager.meta_rule)
                assert manager.meta_rule.is_meta_rule
                assert manager.tracked_learnt_count == len(manager.meta_rule.source_learnt_ids)
        
        @staticmethod
        def assert_serialization_fidelity(original, restored, exclude_fields=None):
            """Assert that serialization/deserialization maintains fidelity."""
            exclude_fields = exclude_fields or []
            
            for attr in dir(original):
                if (not attr.startswith('_') and 
                    not callable(getattr(original, attr)) and
                    attr not in exclude_fields):
                    
                    original_value = getattr(original, attr)
                    restored_value = getattr(restored, attr)
                    
                    assert original_value == restored_value, (
                        f"Attribute {attr} differs: {original_value} != {restored_value}"
                    )
    
    return ValidationUtils()


# ================================
# Test Environment Configuration
# ================================

def pytest_configure(config):
    """Configure pytest environment."""
    # Register custom markers
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "performance: mark test as performance benchmark")
    config.addinivalue_line("markers", "concurrency: mark test as concurrency test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "edge_case: mark test as edge case test")
    config.addinivalue_line("markers", "stress: mark test as stress test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Auto-mark tests based on naming conventions
        if "performance" in item.name.lower():
            item.add_marker(pytest.mark.performance)
        if "concurrent" in item.name.lower() or "thread" in item.name.lower():
            item.add_marker(pytest.mark.concurrency)
        if "integration" in item.name.lower() or "lifecycle" in item.name.lower():
            item.add_marker(pytest.mark.integration)
        if "edge" in item.name.lower() or "invalid" in item.name.lower():
            item.add_marker(pytest.mark.edge_case)
        if "stress" in item.name.lower() or "large" in item.name.lower():
            item.add_marker(pytest.mark.stress)
        if "benchmark" in item.name.lower():
            item.add_marker(pytest.mark.performance)


def pytest_runtest_setup(item):
    """Setup for each test run."""
    # Force garbage collection before each test
    gc.collect()


def pytest_runtest_teardown(item):
    """Teardown for each test run."""
    # Force garbage collection after each test
    gc.collect()


# ================================
# Parametrized Fixtures
# ================================

@pytest.fixture(params=TEST_PROFILES.keys())
def all_test_profiles(request):
    """Parametrized fixture that runs tests with all available profiles."""
    return TEST_PROFILES[request.param]


@pytest.fixture(params=[
    ("IncorrectAction", "major"),
    ("Misunderstanding", "critical"), 
    ("UnmetUserGoal", "minor"),
    ("InvalidResponse", "critical"),
    ("IncompleteSolution", "major"),
    ("WrongAssumption", "minor"),
    ("MissingContext", "major"),
])
def error_severity_combinations(request):
    """Parametrized fixture providing error type and severity combinations."""
    return request.param


@pytest.fixture(params=[1, 10, 50, 100])
def batch_sizes(request):
    """Parametrized fixture providing various batch sizes for testing."""
    return request.param 