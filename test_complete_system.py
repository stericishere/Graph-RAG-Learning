#!/usr/bin/env python3
"""
Comprehensive system test for the Final Minimal Lean Graph Database MCP.

This script validates all models (Rule, Learnt, MetaRuleManager) and their
interactions to ensure the self-improving AI system works correctly.
"""

import sys
import traceback
from datetime import datetime

# Add src to path
sys.path.insert(0, '.')

try:
    from src.models import Rule, Learnt, MetaRuleManager
    from src.models.rule import RuleCategory, RuleType
    from src.models.learnt import ErrorType, SeverityLevel
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)


def test_rule_model():
    """Test Rule model functionality."""
    print("\n🧪 Testing Rule Model...")
    
    try:
        # Test 1: Basic rule creation
        rule = Rule(
            rule_name="Test Rule",
            content="Test content for validation"
        )
        assert rule.rule_name == "Test Rule"
        assert len(rule.rule_id) == 36  # UUID format
        assert rule.category == RuleCategory.GENERAL
        assert not rule.is_meta_rule
        print("✅ Basic rule creation: PASSED")
        
        # Test 2: Meta-rule creation
        meta_rule = Rule.create_meta_rule(
            rule_name="Test Meta Rule",
            content="Meta rule content"
        )
        assert meta_rule.is_meta_rule
        assert meta_rule.category == RuleCategory.META_LEARNT
        assert meta_rule.rule_type == RuleType.META_AGGREGATION
        print("✅ Meta-rule creation: PASSED")
        
        # Test 3: Rule serialization
        rule_dict = rule.to_dict()
        restored_rule = Rule.from_dict(rule_dict)
        assert restored_rule.rule_name == rule.rule_name
        assert restored_rule.rule_id == rule.rule_id
        print("✅ Rule serialization: PASSED")
        
        # Test 4: Meta-rule source management
        meta_rule.add_source_learnt_id("learnt-1")
        meta_rule.add_source_learnt_id("learnt-2")
        assert len(meta_rule.source_learnt_ids) == 2
        
        removed = meta_rule.remove_source_learnt_id("learnt-1")
        assert removed
        assert len(meta_rule.source_learnt_ids) == 1
        print("✅ Meta-rule source management: PASSED")
        
        # Test 5: Validation constraints
        try:
            Rule(rule_name="", content="Valid content")
            assert False, "Should have raised validation error"
        except ValueError:
            pass  # Expected
        print("✅ Rule validation constraints: PASSED")
        
        return True
        
    except Exception as e:
        print(f"❌ Rule model test failed: {e}")
        traceback.print_exc()
        return False


def test_learnt_model():
    """Test Learnt model functionality."""
    print("\n🧪 Testing Learnt Model...")
    
    try:
        # Test 1: Basic learnt creation
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
        assert learnt.original_severity == SeverityLevel.MAJOR
        assert len(learnt.learnt_id) == 36  # UUID format
        assert not learnt.contributed_to_meta_rule
        print("✅ Basic learnt creation: PASSED")
        
        # Test 2: Meta-rule trigger
        result = learnt.trigger_meta_rule_update()
        assert result
        assert learnt.contributed_to_meta_rule
        assert learnt.meta_rule_contribution is not None
        assert "To avoid incorrectaction" in learnt.meta_rule_contribution
        print("✅ Meta-rule trigger: PASSED")
        
        # Test 3: Learnt serialization
        learnt_dict = learnt.to_dict()
        restored_learnt = Learnt.from_dict(learnt_dict)
        assert restored_learnt.problem_summary == learnt.problem_summary
        assert restored_learnt.learnt_id == learnt.learnt_id
        print("✅ Learnt serialization: PASSED")
        
        # Test 4: Callback system
        callback_called = False
        def test_callback(l):
            nonlocal callback_called
            callback_called = True
        
        learnt2 = Learnt.create_from_error("Misunderstanding", "Problem", "Input", "Output", "Cause", "minor", "Solution")
        learnt2.set_meta_rule_update_callback(test_callback)
        learnt2.trigger_meta_rule_update()
        assert callback_called
        print("✅ Callback system: PASSED")
        
        # Test 5: Verification status
        learnt.update_verification_status("validated")
        assert learnt.verification_status == "validated"
        print("✅ Verification status: PASSED")
        
        # Test 6: Learning summary
        summary = learnt.get_learning_summary()
        assert "id" in summary
        assert "problem" in summary
        assert "solution" in summary
        print("✅ Learning summary: PASSED")
        
        return True
        
    except Exception as e:
        print(f"❌ Learnt model test failed: {e}")
        traceback.print_exc()
        return False


def test_meta_rule_manager():
    """Test MetaRuleManager functionality."""
    print("\n🧪 Testing MetaRuleManager...")
    
    try:
        # Test 1: Manager initialization
        manager = MetaRuleManager()
        assert manager.meta_rule is None
        assert manager.tracked_learnt_count == 0
        print("✅ Manager initialization: PASSED")
        
        # Test 2: Meta-rule initialization
        meta_rule = manager.initialize_meta_rule()
        assert meta_rule is not None
        assert meta_rule.is_meta_rule
        assert manager.meta_rule == meta_rule
        print("✅ Meta-rule initialization: PASSED")
        
        # Test 3: Adding learnt experience
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
        assert learnt.contributed_to_meta_rule
        print("✅ Adding learnt experience: PASSED")
        
        # Test 4: Duplicate handling
        result2 = manager.add_learnt_experience(learnt)
        assert not result2  # Should reject duplicate
        assert manager.tracked_learnt_count == 1
        print("✅ Duplicate handling: PASSED")
        
        # Test 5: Aggregation summary
        summary = manager.get_aggregation_summary()
        assert summary["meta_rule_exists"]
        assert summary["tracked_learnt_count"] == 1
        assert len(summary["tracked_learnt_ids"]) == 1
        print("✅ Aggregation summary: PASSED")
        
        # Test 6: Learning insights
        insights = manager.get_learning_insights()
        assert insights["total_experiences"] == 1
        assert insights["most_common_error"] is not None
        print("✅ Learning insights: PASSED")
        
        # Test 7: Meta-rule content update
        content = manager.meta_rule.content
        assert "AI Learning Aggregator" in content
        assert "Total learnt experiences processed: 1" in content
        assert "IncorrectAction: 1 occurrences" in content
        print("✅ Meta-rule content update: PASSED")
        
        # Test 8: Export/Import
        export_data = manager.export_meta_rule_knowledge()
        assert export_data["meta_rule"] is not None
        assert len(export_data["tracked_learnt_ids"]) == 1
        
        new_manager = MetaRuleManager()
        import_result = new_manager.import_meta_rule_knowledge(export_data)
        assert import_result
        assert new_manager.tracked_learnt_count == 1
        print("✅ Export/Import: PASSED")
        
        return True
        
    except Exception as e:
        print(f"❌ MetaRuleManager test failed: {e}")
        traceback.print_exc()
        return False


def test_integration_scenarios():
    """Test integration scenarios between all models."""
    print("\n🧪 Testing Integration Scenarios...")
    
    try:
        # Test 1: End-to-end learning workflow
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
            
            result = manager.add_learnt_experience(learnt)
            assert result
        
        assert manager.tracked_learnt_count == 3
        print("✅ End-to-end workflow: PASSED")
        
        # Test 2: Aggregation algorithm
        insights = manager.get_learning_insights()
        assert insights["total_experiences"] == 3
        assert insights["most_common_error"]["type"] == "IncorrectAction"
        assert insights["most_common_error"]["count"] == 2
        print("✅ Aggregation algorithm: PASSED")
        
        # Test 3: Meta-rule relationship tracking
        meta_rule = manager.meta_rule
        assert len(meta_rule.source_learnt_ids) == 3
        for learnt in learnt_experiences:
            assert learnt.learnt_id in meta_rule.source_learnt_ids
            assert learnt.contributed_to_meta_rule
        print("✅ Relationship tracking: PASSED")
        
        # Test 4: Content generation quality
        content = meta_rule.content
        assert "IncorrectAction: 2 occurrences" in content
        assert "Misunderstanding: 1 occurrences" in content
        assert "Actionable Guidance:" in content
        assert "Meta-Learning Principles:" in content
        print("✅ Content generation: PASSED")
        
        # Test 5: System effectiveness
        effectiveness = manager.get_meta_rule_effectiveness()
        assert effectiveness["data_coverage"]["total_experiences"] == 3
        assert effectiveness["content_quality"]["source_diversity"] >= 2
        print("✅ System effectiveness: PASSED")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        traceback.print_exc()
        return False


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n🧪 Testing Edge Cases...")
    
    try:
        # Test 1: Non-validated learnt experiences
        manager = MetaRuleManager()
        learnt = Learnt.create_from_error("IncorrectAction", "Problem", "Input", "Output", "Cause", "major", "Solution")
        learnt.verification_status = "pending"  # Not validated
        
        result = manager.add_learnt_experience(learnt)
        assert not result  # Should be rejected
        assert manager.tracked_learnt_count == 0
        print("✅ Non-validated rejection: PASSED")
        
        # Test 2: Empty aggregation state
        insights = manager.get_learning_insights()
        assert insights["message"] == "No learning data available yet"
        print("✅ Empty state handling: PASSED")
        
        # Test 3: System reset
        manager.initialize_meta_rule()
        validated_learnt = Learnt.create_from_error("IncorrectAction", "Problem", "Input", "Output", "Cause", "major", "Solution")
        manager.add_learnt_experience(validated_learnt)
        assert manager.tracked_learnt_count == 1
        
        manager.reset_meta_rule()
        assert manager.tracked_learnt_count == 0
        assert manager.meta_rule is not None  # Should have new meta-rule
        print("✅ System reset: PASSED")
        
        # Test 4: Removal of learnt experiences
        learnt = Learnt.create_from_error("IncorrectAction", "Remove test", "Input", "Output", "Cause", "major", "Solution")
        manager.add_learnt_experience(learnt)
        assert manager.tracked_learnt_count == 1
        
        removed = manager.remove_learnt_experience(learnt.learnt_id)
        assert removed
        assert manager.tracked_learnt_count == 0
        print("✅ Learnt experience removal: PASSED")
        
        return True
        
    except Exception as e:
        print(f"❌ Edge case test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("🚀 Starting Comprehensive System Test")
    print("="*60)
    
    test_results = []
    
    # Run all test suites
    test_results.append(("Rule Model", test_rule_model()))
    test_results.append(("Learnt Model", test_learnt_model()))
    test_results.append(("MetaRuleManager", test_meta_rule_manager()))
    test_results.append(("Integration Scenarios", test_integration_scenarios()))
    test_results.append(("Edge Cases", test_edge_cases()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:25} {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The self-improving AI system is fully functional.")
        print("\n📋 System Capabilities Verified:")
        print("  • Rule model with meta-rule support")
        print("  • Learnt model with meta-rule integration") 
        print("  • MetaRuleManager orchestrating the self-improving system")
        print("  • End-to-end learning workflow")
        print("  • Knowledge aggregation and insights generation")
        print("  • Export/import functionality")
        print("  • Error handling and edge cases")
        return True
    else:
        print(f"\n⚠️  {total - passed} test suite(s) failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 