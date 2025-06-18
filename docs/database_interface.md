# Database Interface Documentation

## Overview

The Final Minimal Lean Graph Database MCP provides a unified interface for graph database operations through two different adapters:

- **Neo4j Adapter**: For production-scale graph databases with full ACID compliance
- **NetworkX Adapter**: For development, testing, and file-based graph storage

Both adapters implement the same `GraphDatabase` interface, allowing seamless switching between database backends through configuration.

## Architecture

```
src/database/
├── base.py              # Abstract GraphDatabase interface
├── neo4j_adapter.py     # Neo4j implementation  
├── networkx_adapter.py  # NetworkX implementation
└── __init__.py          # Factory function and exports
```

## Quick Start

### 1. Database Selection via Factory

```python
from src.database import create_database

# Create NetworkX adapter (file-based)
networkx_config = {
    "data_file": "data/graph_data.json",
    "auto_save": True,
    "backup_count": 3
}
db = create_database("networkx", networkx_config)

# Create Neo4j adapter (server-based)
neo4j_config = {
    "uri": "neo4j://localhost:7687",
    "username": "neo4j",
    "password": "password",
    "database": "graph_mcp"
}
db = create_database("neo4j", neo4j_config)
```

### 2. Basic Usage Pattern

```python
async def example_usage():
    # Connect to database
    await db.connect()
    
    try:
        # Create nodes
        rule_id = await db.create_node("Rule", {
            "name": "frontend_best_practices",
            "category": "frontend",
            "content": "Always use TypeScript for React components"
        })
        
        learnt_id = await db.create_node("Learnt", {
            "problem": "React component re-renders",
            "solution": "Use React.memo for expensive components",
            "validated": True
        })
        
        # Create relationship
        rel_id = await db.create_relationship(
            rule_id, learnt_id, 
            "SUPPORTS", 
            {"strength": 0.9}
        )
        
        # Query nodes
        rules = await db.get_nodes_by_label("Rule", 
            filters={"category": "frontend"}
        )
        
        # Health check
        healthy = await db.health_check()
        print(f"Database healthy: {healthy}")
        
    finally:
        await db.disconnect()
```

## Interface Reference

### Core Methods

#### Connection Management
- `async connect() -> None`: Establish database connection
- `async disconnect() -> None`: Close database connection  
- `async health_check() -> bool`: Check database health

#### Node Operations
- `async create_node(label: str, properties: Dict, node_id: Optional[str] = None) -> str`
- `async get_node(node_id: str) -> Optional[Dict[str, Any]]`
- `async update_node(node_id: str, properties: Dict[str, Any]) -> bool`
- `async delete_node(node_id: str) -> bool`
- `async get_nodes_by_label(label: str, filters: Optional[Dict] = None, limit: Optional[int] = None) -> List[Dict]`

#### Relationship Operations
- `async create_relationship(start_node_id: str, end_node_id: str, relationship_type: str, properties: Optional[Dict] = None) -> str`
- `async get_relationships(node_id: str, relationship_type: Optional[str] = None, direction: str = "both") -> List[Dict]`
- `async delete_relationship(relationship_id: str) -> bool`

#### Data Operations
- `async execute_query(query: str, parameters: Optional[Dict] = None) -> Any`
- `async clear_all_data() -> None`

## Adapter-Specific Configuration

### NetworkX Adapter

```python
config = {
    "data_file": "path/to/graph.json",    # JSON file for persistence
    "auto_save": True,                     # Auto-save after operations
    "backup_count": 3                      # Number of backup files
}
```

**Features:**
- File-based JSON persistence using NetworkX node_link_data format
- Automatic backup rotation
- In-memory graph operations for fast access
- Atomic file operations for data safety

**Best for:** Development, testing, small datasets, portable storage

### Neo4j Adapter

```python
config = {
    "uri": "neo4j://localhost:7687",      # Neo4j server URI
    "username": "neo4j",                   # Database username
    "password": "password",                # Database password  
    "database": "neo4j",                   # Target database name
    "max_connection_pool_size": 10,        # Optional: connection pool size
    "connection_timeout": 30                # Optional: connection timeout
}
```

**Features:**
- Full ACID compliance
- Distributed clustering support
- Advanced query capabilities with Cypher
- Production-scale performance

**Best for:** Production applications, large datasets, complex queries

## Usage Examples

### Example 1: Basic Rule Storage

```python
import asyncio
from src.database import create_database

async def store_coding_rules():
    # Use NetworkX for this example
    db = create_database("networkx", {"data_file": "rules.json"})
    await db.connect()
    
    try:
        # Store frontend rules
        react_rule = await db.create_node("Rule", {
            "name": "react_hooks_rules",
            "category": "frontend", 
            "content": "Use useCallback for event handlers in lists",
            "priority": "high"
        })
        
        # Store backend rules  
        api_rule = await db.create_node("Rule", {
            "name": "api_error_handling",
            "category": "backend",
            "content": "Always return structured error responses",
            "priority": "critical"
        })
        
        # Create category relationship
        await db.create_relationship(
            react_rule, api_rule, 
            "COMPLEMENTS", 
            {"context": "full_stack_development"}
        )
        
        print(f"Stored rules: {react_rule}, {api_rule}")
        
    finally:
        await db.disconnect()

# Run example
asyncio.run(store_coding_rules())
```

### Example 2: Learning from Experience

```python
async def record_learning():
    db = create_database("networkx", {"data_file": "learnings.json"})
    await db.connect()
    
    try:
        # Record a problem and solution
        learning = await db.create_node("Learnt", {
            "problem": "Next.js hydration mismatch error",
            "solution": "Use dynamic imports for client-only components",
            "context": "React SSR application", 
            "validated": True,
            "confidence": 0.95
        })
        
        # Link to related rule if exists
        rules = await db.get_nodes_by_label("Rule", 
            filters={"category": "frontend"}
        )
        
        if rules:
            await db.create_relationship(
                learning, rules[0]["node_id"],
                "VALIDATES",
                {"strength": 0.8}
            )
            
        print(f"Recorded learning: {learning}")
        
    finally:
        await db.disconnect()
```

### Example 3: Switching Database Backends

```python
import os
from src.database import create_database

async def adaptive_database():
    # Choose database based on environment
    if os.getenv("ENVIRONMENT") == "production":
        config = {
            "uri": os.getenv("NEO4J_URI"),
            "username": os.getenv("NEO4J_USERNAME"), 
            "password": os.getenv("NEO4J_PASSWORD")
        }
        db = create_database("neo4j", config)
    else:
        config = {"data_file": "dev_graph.json"}
        db = create_database("networkx", config)
    
    await db.connect()
    
    try:
        # Same code works with both adapters!
        rules = await db.get_nodes_by_label("Rule")
        print(f"Found {len(rules)} rules")
        
    finally:
        await db.disconnect()
```

## Error Handling

The interface defines custom exceptions for different error scenarios:

```python
from src.database.base import (
    DatabaseConnectionError,    # Connection/configuration issues
    NodeNotFoundError,          # Node doesn't exist
    RelationshipNotFoundError,  # Relationship doesn't exist  
    ValidationError             # Invalid data/parameters
)

async def safe_database_operation():
    try:
        await db.create_node("Rule", {"name": "example"})
    except ValidationError as e:
        print(f"Invalid data: {e}")
    except DatabaseConnectionError as e:
        print(f"Database issue: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
```

## Testing

The database adapters include comprehensive test coverage:

```bash
# Run all database tests
pytest tests/test_adapter_consistency.py -v

# Run specific test functions
pytest tests/test_adapter_consistency.py::test_adapter_factory -v
pytest tests/test_adapter_consistency.py::TestAdapterConsistency::test_networkx_adapter_basic_operations -v
```

## Migration Between Adapters

When switching from NetworkX to Neo4j (or vice versa), you can migrate data:

```python
async def migrate_data():
    # Source: NetworkX
    source_db = create_database("networkx", {"data_file": "source.json"})
    await source_db.connect()
    
    # Target: Neo4j
    target_db = create_database("neo4j", {
        "uri": "neo4j://localhost:7687",
        "username": "neo4j",
        "password": "password"
    })
    await target_db.connect()
    
    try:
        # Migrate all nodes
        for label in ["Rule", "Learnt"]:
            nodes = await source_db.get_nodes_by_label(label)
            for node in nodes:
                # Create node in target with same ID
                await target_db.create_node(
                    label, 
                    {k: v for k, v in node.items() if k != "node_id"},
                    node["node_id"]
                )
                
        print("Migration completed successfully")
        
    finally:
        await source_db.disconnect()
        await target_db.disconnect()
```

## Best Practices

1. **Always use async context managers when possible:**
   ```python
   async with db:  # Automatically connects and disconnects
       await db.create_node("Rule", {"name": "example"})
   ```

2. **Use the factory pattern for adapter selection:**
   ```python
   # Good: Configurable
   db = create_database(config["db_type"], config["db_config"])
   
   # Avoid: Hard-coded
   db = Neo4jAdapter(config)
   ```

3. **Handle errors appropriately:**
   ```python
   try:
       node = await db.get_node(node_id)
       if node is None:
           # Handle missing node
           pass
   except DatabaseConnectionError:
       # Handle connection issues
       pass
   ```

4. **Use meaningful node IDs:**
   ```python
   # Good: Meaningful ID
   await db.create_node("Rule", properties, "rule_react_hooks_001")
   
   # OK: Auto-generated UUID
   await db.create_node("Rule", properties)  # Auto-generates UUID
   ```

This interface provides a clean, consistent way to work with graph data regardless of the underlying database technology. 