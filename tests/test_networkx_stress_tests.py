"""
Stress tests for NetworkX adapter file persistence functionality.
Tests edge cases, performance scenarios, and robustness patterns.
"""

import asyncio
import json
import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from src.database.networkx_adapter import NetworkXAdapter
from src.database.base import DatabaseConnectionError


class TestNetworkXStressTests:
    """Stress test suite for NetworkX adapter file persistence."""
    
    @pytest.fixture
    def temp_data_file(self):
        """Create a temporary data file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = Path(f.name)
        yield temp_file
        
        # Cleanup temp file and backups
        try:
            if temp_file.exists():
                temp_file.unlink()
            # Clean up backup files
            backup_files = list(temp_file.parent.glob(f"{temp_file.stem}.bak*"))
            for backup in backup_files:
                backup.unlink()
        except:
            pass
    
    @pytest.fixture
    def stress_config(self, temp_data_file):
        """Configuration for stress testing."""
        return {
            "data_file": str(temp_data_file),
            "auto_save": True,
            "backup_count": 3
        }

    @pytest.mark.asyncio
    async def test_large_graph_persistence(self, stress_config):
        """Test persistence with a large number of nodes and edges."""
        adapter = NetworkXAdapter(stress_config)
        await adapter.connect()
        
        # Create 200 nodes
        node_ids = []
        for i in range(200):
            node_id = await adapter.create_node("Rule", {
                "title": f"Rule {i}",
                "description": f"Description for rule {i}",
                "category": "performance",
                "complexity": i % 5,
                "data": f"Large data field with content {i}" * 10  # Make it larger
            })
            node_ids.append(node_id)
        
        # Create 300 relationships
        for i in range(150):
            await adapter.create_relationship(
                node_ids[i], node_ids[i+50], "RELATED_TO",
                {"strength": (i % 10) / 10.0, "metadata": f"Rel {i}"}
            )
        
        await adapter.disconnect()
        
        # Verify large graph persists correctly
        adapter2 = NetworkXAdapter(stress_config)
        await adapter2.connect()
        
        stats = adapter2.get_graph_stats()
        assert stats["node_count"] == 200
        assert stats["edge_count"] == 150
        
        # Verify metadata preservation
        rule_nodes = await adapter2.get_nodes_by_label("Rule")
        assert len(rule_nodes) == 200
        
        await adapter2.disconnect()

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, stress_config):
        """Test persistence with unicode and special characters."""
        adapter = NetworkXAdapter(stress_config)
        await adapter.connect()
        
        # Create nodes with various unicode characters
        special_chars = [
            "Unicode Test 🚀🌟⭐",
            "Émojis and spëcial chars: αβγδε",
            "Asian characters: 你好世界 こんにちは 안녕하세요",
            "Math symbols: ∑∏∫√∞±",
            "Quotes and escapes: \"test\" 'test' \\backslash",
            "Newlines\nand\ttabs",
            "JSON-like: {\"key\": \"value\", \"array\": [1,2,3]}",
            "Paths: C:\\Windows\\System32\\file.exe"
        ]
        
        node_ids = []
        for i, content in enumerate(special_chars):
            node_id = await adapter.create_node("Rule", {
                "title": content,
                "description": f"Test {i}: {content}",
                "content": content * 3  # Repeat for stress testing
            })
            node_ids.append(node_id)
        
        # Create relationships with special characters
        for i in range(len(node_ids) - 1):
            await adapter.create_relationship(
                node_ids[i], node_ids[i+1], "UNICODE_TEST",
                {"note": special_chars[i], "extra": "More unicode: ©®™"}
            )
        
        await adapter.disconnect()
        
        # Verify unicode characters persist correctly
        adapter2 = NetworkXAdapter(stress_config)
        await adapter2.connect()
        
        for i, expected_content in enumerate(special_chars):
            loaded_node = await adapter2.get_node(node_ids[i])
            assert expected_content in loaded_node["title"]
            assert expected_content in loaded_node["description"]
            assert loaded_node["content"].count(expected_content) == 3
        
        await adapter2.disconnect()

    @pytest.mark.asyncio
    async def test_rapid_operations_stress(self, stress_config):
        """Test behavior under rapid consecutive operations."""
        adapter = NetworkXAdapter(stress_config)
        await adapter.connect()
        
        start_time = time.time()
        
        # Rapid node creation
        node_ids = []
        for i in range(100):
            node_id = await adapter.create_node("Rule", {
                "title": f"Rapid {i}",
                "timestamp": time.time(),
                "batch": "stress_test"
            })
            node_ids.append(node_id)
        
        # Rapid relationship creation
        for i in range(50):
            await adapter.create_relationship(
                node_ids[i], node_ids[i+50], "RAPID_REL",
                {"created_at": time.time(), "index": i}
            )
        
        # Rapid updates
        for i in range(0, 50, 2):
            await adapter.update_node(node_ids[i], {
                "updated": True,
                "update_time": time.time()
            })
        
        end_time = time.time()
        duration = end_time - start_time
        
        await adapter.disconnect()
        
        # Should complete in reasonable time
        assert duration < 15.0, f"Rapid operations took too long: {duration:.2f} seconds"
        
        # Verify all data persisted correctly
        adapter2 = NetworkXAdapter(stress_config)
        await adapter2.connect()
        
        stats = adapter2.get_graph_stats()
        assert stats["node_count"] == 100
        assert stats["edge_count"] == 50
        
        # Verify updates were applied
        updated_count = 0
        for i in range(0, 50, 2):
            node = await adapter2.get_node(node_ids[i])
            if node and node.get("updated"):
                updated_count += 1
        assert updated_count == 25
        
        await adapter2.disconnect()

    @pytest.mark.asyncio
    async def test_backup_stress_test(self, stress_config):
        """Test backup system under stress."""
        stress_config["backup_count"] = 5
        data_file = Path(stress_config["data_file"])
        
        # Perform many operations that trigger backups
        for cycle in range(10):
            adapter = NetworkXAdapter(stress_config)
            await adapter.connect()
            
            # Add data in each cycle
            for i in range(5):
                await adapter.create_node("Rule", {
                    "title": f"Cycle {cycle} Node {i}",
                    "cycle": cycle,
                    "iteration": i
                })
            
            await adapter.disconnect()
        
        # Check backup rotation worked correctly
        backup_files = list(data_file.parent.glob(f"{data_file.stem}.bak*"))
        assert len(backup_files) <= stress_config["backup_count"]
        
        # Verify final data integrity
        adapter = NetworkXAdapter(stress_config)
        await adapter.connect()
        stats = adapter.get_graph_stats()
        assert stats["node_count"] == 50  # 10 cycles × 5 nodes
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_file_corruption_scenarios(self, stress_config):
        """Test various file corruption scenarios."""
        data_file = Path(stress_config["data_file"])
        
        # Create initial data
        adapter = NetworkXAdapter(stress_config)
        await adapter.connect()
        await adapter.create_node("Rule", {"title": "Initial"})
        await adapter.disconnect()
        
        corruption_scenarios = [
            '{"graph":',  # Truncated JSON
            '{"graph": {"nodes": [], "links": []}, "metadata": null}',  # Null metadata
            '{"invalid": "structure"}',  # Wrong structure
            '{"graph": {"nodes": "invalid"}, "metadata": {}}',  # Invalid nodes
            '',  # Empty file
            'not json at all',  # Non-JSON content
            '{"graph": {"nodes": [], "links": []}}',  # Missing metadata
        ]
        
        for i, corrupt_content in enumerate(corruption_scenarios):
            # Write corrupted content
            with open(data_file, 'w') as f:
                f.write(corrupt_content)
            
            # Adapter should handle corruption gracefully
            adapter = NetworkXAdapter(stress_config)
            await adapter.connect()  # Should not raise exception
            
            stats = adapter.get_graph_stats()
            assert stats["node_count"] == 0  # Should start with empty graph
            
            # Should be able to add new data
            await adapter.create_node("Rule", {"title": f"Recovery {i}"})
            
            await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_disk_space_simulation(self, stress_config):
        """Test behavior when disk space is limited (simulated)."""
        adapter = NetworkXAdapter(stress_config)
        await adapter.connect()
        
        # Add some initial data
        await adapter.create_node("Rule", {"title": "Before disk full"})
        
        # Mock disk full scenario during save
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            with pytest.raises(DatabaseConnectionError, match="Graph save failed"):
                await adapter._save_graph()
        
        # Adapter should still be functional for reads
        stats = adapter.get_graph_stats()
        assert stats["node_count"] == 1
        
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_complex_relationship_patterns(self, stress_config):
        """Test complex relationship patterns and cycles."""
        adapter = NetworkXAdapter(stress_config)
        await adapter.connect()
        
        # Create a complex graph with cycles and multiple relationship types
        node_ids = []
        for i in range(20):
            node_id = await adapter.create_node("Rule", {
                "title": f"Node {i}",
                "category": ["A", "B", "C"][i % 3]
            })
            node_ids.append(node_id)
        
        # Create various relationship patterns
        relationship_types = ["DEPENDS_ON", "CONFLICTS_WITH", "ENHANCES", "RELATES_TO"]
        
        # Linear chain
        for i in range(19):
            await adapter.create_relationship(
                node_ids[i], node_ids[i+1], "NEXT",
                {"chain_order": i}
            )
        
        # Cycles
        await adapter.create_relationship(
            node_ids[19], node_ids[0], "CYCLES_TO",
            {"creates_cycle": True}
        )
        
        # Many-to-many relationships
        for i in range(0, 10, 2):
            for j in range(10, 15):
                await adapter.create_relationship(
                    node_ids[i], node_ids[j], relationship_types[i % 4],
                    {"pattern": "many_to_many", "strength": (i + j) % 10}
                )
        
        await adapter.disconnect()
        
        # Verify complex graph persists correctly
        adapter2 = NetworkXAdapter(stress_config)
        await adapter2.connect()
        
        stats = adapter2.get_graph_stats()
        assert stats["node_count"] == 20
        # 19 linear + 1 cycle + 25 many-to-many = 45 relationships
        assert stats["edge_count"] == 45
        
        # Verify complex queries work
        node_0_rels = await adapter2.get_relationships(node_ids[0])
        assert len(node_0_rels) >= 3  # Should have multiple relationships
        
        await adapter2.disconnect()

    @pytest.mark.asyncio
    async def test_memory_efficiency(self, stress_config):
        """Test memory efficiency with large datasets."""
        adapter = NetworkXAdapter(stress_config)
        await adapter.connect()
        
        # Create nodes with large data fields
        large_data = "x" * 1000  # 1KB per field
        
        for i in range(100):
            await adapter.create_node("Rule", {
                "title": f"Large Node {i}",
                "large_field_1": large_data,
                "large_field_2": large_data,
                "large_field_3": large_data,
                "metadata": {"index": i, "size": "large"}
            })
        
        await adapter.disconnect()
        
        # Verify data persists and loads efficiently
        start_time = time.time()
        
        adapter2 = NetworkXAdapter(stress_config)
        await adapter2.connect()
        
        load_time = time.time() - start_time
        
        # Should load reasonably quickly even with large data
        assert load_time < 5.0, f"Loading took too long: {load_time:.2f} seconds"
        
        stats = adapter2.get_graph_stats()
        assert stats["node_count"] == 100
        
        # Verify data integrity with random sampling
        for i in [0, 25, 50, 75, 99]:
            nodes = await adapter2.get_nodes_by_label("Rule", {"metadata.index": i})
            if nodes:
                node = nodes[0]
                assert len(node["large_field_1"]) == 1000
                assert node["metadata"]["index"] == i
        
        await adapter2.disconnect() 