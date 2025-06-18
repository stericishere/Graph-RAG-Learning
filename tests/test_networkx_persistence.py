"""
Tests for NetworkX adapter file persistence functionality.
"""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from src.database.networkx_adapter import NetworkXAdapter
from src.database.base import DatabaseConnectionError


class TestNetworkXPersistence:
    """Test suite for NetworkX adapter file persistence."""
    
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
    def adapter_config(self, temp_data_file):
        """Configuration for NetworkX adapter with temporary file."""
        return {
            "data_file": str(temp_data_file),
            "auto_save": True,
            "backup_count": 2
        }
    
    @pytest.mark.asyncio
    async def test_save_and_load_empty_graph(self, adapter_config):
        """Test saving and loading an empty graph."""
        adapter = NetworkXAdapter(adapter_config)
        await adapter.connect()
        
        # Empty graph should save without issues
        await adapter._save_graph()
        await adapter.disconnect()
        
        # Load in new adapter
        adapter2 = NetworkXAdapter(adapter_config)
        await adapter2.connect()
        stats = adapter2.get_graph_stats()
        
        assert stats["node_count"] == 0
        assert stats["edge_count"] == 0
        
        await adapter2.disconnect()
    
    @pytest.mark.asyncio
    async def test_data_persistence_across_sessions(self, adapter_config):
        """Test that data persists across different adapter sessions."""
        # Session 1: Create data
        adapter1 = NetworkXAdapter(adapter_config)
        await adapter1.connect()
        
        rule_id = await adapter1.create_node("Rule", {
            "title": "Test Rule",
            "description": "A test rule",
            "category": "Testing"
        })
        
        learnt_id = await adapter1.create_node("Learnt", {
            "original_error": "Test error",
            "solution": "Test solution"
        })
        
        rel_id = await adapter1.create_relationship(
            rule_id, learnt_id, "LEARNED_FROM", {"confidence": 0.95}
        )
        
        await adapter1.disconnect()
        
        # Session 2: Load and verify data
        adapter2 = NetworkXAdapter(adapter_config)
        await adapter2.connect()
        
        stats = adapter2.get_graph_stats()
        assert stats["node_count"] == 2
        assert stats["edge_count"] == 1
        
        # Verify node data
        rule_data = await adapter2.get_node(rule_id)
        assert rule_data["title"] == "Test Rule"
        assert rule_data["label"] == "Rule"
        
        learnt_data = await adapter2.get_node(learnt_id)
        assert learnt_data["solution"] == "Test solution"
        assert learnt_data["label"] == "Learnt"
        
        # Verify relationship
        relationships = await adapter2.get_relationships(rule_id)
        assert len(relationships) == 1
        assert relationships[0]["type"] == "LEARNED_FROM"
        assert relationships[0]["confidence"] == 0.95
        
        await adapter2.disconnect()
    
    @pytest.mark.asyncio
    async def test_auto_save_functionality(self, adapter_config):
        """Test that auto-save works correctly."""
        data_file = Path(adapter_config["data_file"])
        
        adapter = NetworkXAdapter(adapter_config)
        await adapter.connect()
        
        # File should exist but be minimal after connect
        assert data_file.exists()
        
        # Add a node - should trigger auto-save
        await adapter.create_node("Rule", {"title": "Auto-save test"})
        
        # Verify file was updated
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        assert data["metadata"]["node_count"] == 1
        assert len(data["graph"]["nodes"]) == 1
        
        await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_backup_creation(self, adapter_config):
        """Test that backups are created correctly."""
        data_file = Path(adapter_config["data_file"])
        
        # Create initial data
        adapter = NetworkXAdapter(adapter_config)
        await adapter.connect()
        await adapter.create_node("Rule", {"title": "Initial"})
        await adapter.disconnect()
        
        # Verify initial state
        with open(data_file, 'r') as f:
            initial_data = json.load(f)
        initial_count = initial_data["metadata"]["node_count"]
        
        # Modify data to trigger backup
        adapter = NetworkXAdapter(adapter_config)
        await adapter.connect()
        await adapter.create_node("Rule", {"title": "Modified"})
        await adapter.disconnect()
        
        # Check for backup files
        backup_files = list(data_file.parent.glob(f"{data_file.stem}.bak*"))
        assert len(backup_files) > 0
        
        # Verify backup was created (backup should exist)
        backup_file = data_file.with_suffix('.bak1')
        assert backup_file.exists()
        
        # Verify current file has more data
        with open(data_file, 'r') as f:
            current_data = json.load(f)
        assert current_data["metadata"]["node_count"] > initial_count
    
    @pytest.mark.asyncio
    async def test_empty_file_handling(self, adapter_config):
        """Test handling of empty data files."""
        data_file = Path(adapter_config["data_file"])
        
        # Create empty file
        data_file.touch()
        
        adapter = NetworkXAdapter(adapter_config)
        await adapter.connect()  # Should not fail
        
        stats = adapter.get_graph_stats()
        assert stats["node_count"] == 0
        assert stats["edge_count"] == 0
        
        await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_invalid_json_handling(self, adapter_config):
        """Test handling of corrupted JSON files."""
        data_file = Path(adapter_config["data_file"])
        
        # Create file with invalid JSON
        with open(data_file, 'w') as f:
            f.write("invalid json content")
        
        adapter = NetworkXAdapter(adapter_config)
        await adapter.connect()  # Should not fail, start with empty graph
        
        stats = adapter.get_graph_stats()
        assert stats["node_count"] == 0
        assert stats["edge_count"] == 0
        
        await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_metadata_persistence(self, adapter_config):
        """Test that metadata is properly saved and loaded."""
        adapter = NetworkXAdapter(adapter_config)
        await adapter.connect()
        
        # Create nodes of different labels
        await adapter.create_node("Rule", {"title": "Rule1"})
        await adapter.create_node("Rule", {"title": "Rule2"})
        await adapter.create_node("Learnt", {"solution": "Solution1"})
        
        # Check internal metadata
        assert "Rule" in adapter._nodes_by_label
        assert "Learnt" in adapter._nodes_by_label
        assert len(adapter._nodes_by_label["Rule"]) == 2
        assert len(adapter._nodes_by_label["Learnt"]) == 1
        
        await adapter.disconnect()
        
        # Load in new adapter and verify metadata
        adapter2 = NetworkXAdapter(adapter_config)
        await adapter2.connect()
        
        assert "Rule" in adapter2._nodes_by_label
        assert "Learnt" in adapter2._nodes_by_label
        assert len(adapter2._nodes_by_label["Rule"]) == 2
        assert len(adapter2._nodes_by_label["Learnt"]) == 1
        
        await adapter2.disconnect()
    
    @pytest.mark.asyncio
    async def test_atomic_save_operation(self, adapter_config):
        """Test that save operations are atomic."""
        data_file = Path(adapter_config["data_file"])
        
        adapter = NetworkXAdapter(adapter_config)
        await adapter.connect()
        
        # Mock a failure during the final move operation
        with patch('pathlib.Path.replace', side_effect=OSError("Simulated failure")):
            with pytest.raises(DatabaseConnectionError, match="Graph save failed"):
                await adapter._save_graph()
        
        # Temporary file should be cleaned up, original should be intact
        temp_files = list(data_file.parent.glob(f"{data_file.stem}.tmp"))
        assert len(temp_files) == 0
        
        await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_backup_rotation(self, adapter_config):
        """Test that backup files are rotated correctly."""
        # Set backup count to 2 for easier testing
        adapter_config["backup_count"] = 2
        data_file = Path(adapter_config["data_file"])
        
        adapter = NetworkXAdapter(adapter_config)
        await adapter.connect()
        
        # Create initial file
        await adapter.create_node("Rule", {"title": "Initial"})
        await adapter.disconnect()
        
        # Multiple saves to test rotation
        for i in range(3):
            adapter = NetworkXAdapter(adapter_config)
            await adapter.connect()
            await adapter.create_node("Rule", {"title": f"Update {i}"})
            await adapter.disconnect()
        
        # Should have at most backup_count backup files
        backup_files = list(data_file.parent.glob(f"{data_file.stem}.bak*"))
        assert len(backup_files) <= adapter_config["backup_count"]
        
        # Check that backups are numbered correctly
        bak1 = data_file.with_suffix('.bak1')
        bak2 = data_file.with_suffix('.bak2')
        assert bak1.exists()
        assert bak2.exists()
    
    @pytest.mark.asyncio 
    async def test_no_auto_save_mode(self, adapter_config):
        """Test adapter with auto-save disabled."""
        adapter_config["auto_save"] = False
        data_file = Path(adapter_config["data_file"])
        
        adapter = NetworkXAdapter(adapter_config)
        await adapter.connect()
        
        # Add data without auto-save
        await adapter.create_node("Rule", {"title": "No auto-save"})
        
        # File should be empty/minimal since no auto-save
        # The file might not exist or be empty
        if data_file.exists() and data_file.stat().st_size > 0:
            with open(data_file, 'r') as f:
                data = json.load(f)
            assert data["metadata"]["node_count"] == 0
        
        # Manual save
        await adapter._save_graph()
        
        # Now file should contain data
        assert data_file.exists()
        with open(data_file, 'r') as f:
            data = json.load(f)
        assert data["metadata"]["node_count"] == 1
        
        await adapter.disconnect() 