#!/usr/bin/env python3
"""
Database Interface Demonstration

This script demonstrates how to use both Neo4j and NetworkX adapters
through the same unified interface. It showcases:

1. Database adapter selection via factory
2. Basic CRUD operations
3. Relationship management
4. Error handling patterns
5. Adapter interchangeability

Run with: python examples/database_demo.py
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path to import src modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import create_database
from src.database.base import (
    DatabaseConnectionError,
    NodeNotFoundError,
    ValidationError
)


async def demo_networkx_adapter():
    """Demonstrate NetworkX adapter capabilities."""
    print("\n" + "="*50)
    print("🔗 NetworkX Adapter Demo")
    print("="*50)
    
    # Create temporary file path (but not the file itself)
    temp_dir = tempfile.mkdtemp()
    data_file = os.path.join(temp_dir, 'demo_graph.json')
    
    try:
        # Configure NetworkX adapter
        config = {
            "data_file": data_file,
            "auto_save": True,
            "backup_count": 2
        }
        
        db = create_database("networkx", config)
        await db.connect()
        
        try:
            print(f"✅ Connected to NetworkX database at: {data_file}")
            
            # Test health check
            healthy = await db.health_check()
            print(f"📊 Health check: {'PASS' if healthy else 'FAIL'}")
            
            # Create nodes
            print("\n📝 Creating nodes...")
            
            rule_id = await db.create_node("Rule", {
                "name": "react_performance",
                "category": "frontend",
                "content": "Use React.memo() for expensive components",
                "priority": "high",
                "tags": ["react", "performance", "optimization"]
            })
            print(f"   Created Rule: {rule_id}")
            
            learnt_id = await db.create_node("Learnt", {
                "problem": "Slow React app with many re-renders",
                "solution": "Wrapped expensive components with React.memo",
                "context": "E-commerce product listing page",
                "validated": True,
                "confidence": 0.95,
                "performance_gain": "60% render time reduction"
            })
            print(f"   Created Learnt: {learnt_id}")
            
            # Create relationship
            print("\n🔗 Creating relationships...")
            rel_id = await db.create_relationship(
                rule_id, learnt_id,
                "VALIDATES",
                {
                    "strength": 0.9,
                    "evidence": "Real-world performance improvement",
                    "date_validated": "2025-01-18"
                }
            )
            print(f"   Created relationship: {rel_id}")
            
            # Query operations
            print("\n🔍 Querying data...")
            
            # Get specific node
            retrieved_rule = await db.get_node(rule_id)
            print(f"   Retrieved rule: {retrieved_rule['name']}")
            
            # Get nodes by label
            all_rules = await db.get_nodes_by_label("Rule")
            print(f"   Total rules: {len(all_rules)}")
            
            # Get nodes with filters
            frontend_rules = await db.get_nodes_by_label("Rule", 
                filters={"category": "frontend"}
            )
            print(f"   Frontend rules: {len(frontend_rules)}")
            
            # Get relationships
            relationships = await db.get_relationships(rule_id)
            print(f"   Rule relationships: {len(relationships)}")
            
            # Update node
            print("\n✏️  Updating node...")
            updated = await db.update_node(rule_id, {
                "last_verified": "2025-01-18",
                "usage_count": 42
            })
            print(f"   Update successful: {updated}")
            
            # NetworkX-specific feature
            if hasattr(db, 'get_graph_stats'):
                stats = db.get_graph_stats()
                print(f"\n📈 Graph statistics:")
                print(f"   Nodes: {stats['node_count']}")
                print(f"   Edges: {stats['edge_count']}")
                print(f"   Connected: {stats['is_connected']}")
                print(f"   Avg degree: {stats['average_degree']:.2f}")
            
            print("\n✅ NetworkX demo completed successfully!")
            
        finally:
            await db.disconnect()
            
    finally:
        # Clean up temporary directory
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


async def demo_neo4j_adapter():
    """Demonstrate Neo4j adapter capabilities (mock for demo)."""
    print("\n" + "="*50)
    print("🛢️  Neo4j Adapter Demo")
    print("="*50)
    
    # This would normally connect to a real Neo4j instance
    # For demo purposes, we'll show configuration without connection
    config = {
        "uri": "neo4j://localhost:7687",
        "username": "neo4j",
        "password": "password",
        "database": "graph_mcp",
        "max_connection_pool_size": 10
    }
    
    try:
        db = create_database("neo4j", config)
        print(f"✅ Neo4j adapter created with config: {config['uri']}")
        print("ℹ️  Note: This demo doesn't connect to avoid Neo4j dependency")
        print("   In production, you would:")
        print("   1. Start Neo4j server")
        print("   2. Configure connection parameters") 
        print("   3. Use identical API calls as NetworkX demo")
        print("   4. Benefit from ACID compliance and clustering")
        
        # Show the same interface is available
        print(f"\n📋 Available methods: {[m for m in dir(db) if not m.startswith('_') and callable(getattr(db, m))]}")
        
    except Exception as e:
        print(f"⚠️  Neo4j configuration error (expected): {e}")


async def demo_error_handling():
    """Demonstrate proper error handling patterns."""
    print("\n" + "="*50)
    print("⚠️  Error Handling Demo")
    print("="*50)
    
    temp_dir = tempfile.mkdtemp()
    data_file = os.path.join(temp_dir, 'error_demo.json')
    
    try:
        db = create_database("networkx", {"data_file": data_file})
        await db.connect()
        
        try:
            # 1. Handling non-existent nodes
            print("🔍 Testing node not found...")
            non_existent = await db.get_node("non_existent_id")
            print(f"   Non-existent node result: {non_existent}")  # Should be None
            
            # 2. Validation errors
            print("\n❌ Testing validation errors...")
            try:
                await db.create_node("Rule", {})  # Empty properties might be invalid
                print("   Empty properties accepted")
            except ValidationError as e:
                print(f"   Validation error caught: {e}")
            
            # 3. Invalid operations
            print("\n🚫 Testing invalid operations...")
            try:
                deleted = await db.delete_node("definitely_not_exists")
                print(f"   Delete non-existent node result: {deleted}")  # Should be False
            except Exception as e:
                print(f"   Error during delete: {e}")
            
            # 4. Database connection issues
            print("\n🔌 Testing disconnected operations...")
            await db.disconnect()
            try:
                await db.create_node("Rule", {"name": "test"})
            except DatabaseConnectionError as e:
                print(f"   Connection error caught: {e}")
            
            print("\n✅ Error handling demo completed!")
            
        except Exception as e:
            print(f"Unexpected error: {e}")
            
    finally:
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


async def demo_adapter_switching():
    """Demonstrate seamless adapter switching."""
    print("\n" + "="*50)
    print("🔄 Adapter Switching Demo")
    print("="*50)
    
    # Function that works with any adapter
    async def store_knowledge(db, adapter_name):
        await db.connect()
        try:
            # Same code works regardless of adapter!
            rule_id = await db.create_node("Rule", {
                "name": f"test_rule_{adapter_name}",
                "content": f"Rule stored via {adapter_name} adapter",
                "adapter_used": adapter_name
            })
            
            nodes = await db.get_nodes_by_label("Rule")
            print(f"   {adapter_name}: Created rule {rule_id}, total rules: {len(nodes)}")
            
        finally:
            await db.disconnect()
    
    # Test with NetworkX
    temp_dir = tempfile.mkdtemp()
    networkx_file = os.path.join(temp_dir, 'switch_demo.json')
    
    try:
        print("📊 Using NetworkX adapter...")
        networkx_db = create_database("networkx", {"data_file": networkx_file})
        await store_knowledge(networkx_db, "NetworkX")
        
        print("\n🛢️  Would use Neo4j adapter with same code...")
        print("   (Skipped to avoid Neo4j dependency)")
        
        print("\n✅ Same interface works with both adapters!")
        
    finally:
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


async def main():
    """Run all database demonstrations."""
    print("🎯 Final Minimal Lean Graph Database MCP")
    print("Database Interface Demonstration")
    print("="*60)
    
    try:
        # Run all demos
        await demo_networkx_adapter()
        await demo_neo4j_adapter()
        await demo_error_handling()
        await demo_adapter_switching()
        
        print("\n" + "="*60)
        print("🎉 All demonstrations completed successfully!")
        print("✨ The database interface provides:")
        print("   • Unified API for Neo4j and NetworkX")
        print("   • Seamless adapter switching")
        print("   • Robust error handling")
        print("   • Production-ready features")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        raise


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main()) 