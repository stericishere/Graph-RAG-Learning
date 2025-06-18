# Final Minimal Lean Graph Database MCP

A highly efficient, minimal graph database MCP (Model Context Protocol) server that serves as a centralized brain for AI agents. This system stores only essential information: **Rules** (AI behaviors/logic) and **Learnt** (validated solutions to problems).

## 🎯 Project Overview

This MCP server provides a dual-database architecture supporting both **Neo4j** and **NetworkX**, automatically selecting the appropriate database based on environment configuration. It's designed to be:

- **Minimal**: Stores only essential rules and validated learning experiences
- **Efficient**: Optimized for quick rule retrieval and learning storage
- **Dual-Compatible**: Seamlessly switches between Neo4j and NetworkX
- **File-Based**: Portable storage for easy deployment and backup

## 🏗️ Architecture

### Core Components

```
ruling_database_mcp/
├── src/
│   ├── server.py              # Main MCP server
│   ├── database/
│   │   ├── base.py           # Abstract database interface
│   │   ├── neo4j_adapter.py  # Neo4j implementation
│   │   └── networkx_adapter.py # NetworkX implementation
│   ├── models/
│   │   ├── rule.py           # Rule node model
│   │   └── learnt.py         # Learnt node model
│   └── tools/
│       ├── rule_tools.py     # Rule management tools
│       └── learning_tools.py # Learning management tools
├── data/                     # File-based storage
├── tests/                    # Test suite
└── docs/                     # Documentation
```

### Node Definitions

#### Rule Node
- `ruleId`: Unique identifier (UUID)
- `ruleName`: String for cursor rule file creation
- `content`: String containing the rule content
- `category`: String (e.g., "frontend", "backend", "database")
- `type`: String (e.g., "always", "auto_attached", "agent_requested", "manual")

#### Learnt Node (Validated Solutions Only)
- `learntId`: Unique identifier (UUID)
- `timestamp_recorded`: ISO timestamp
- `type_of_error`: Error classification
- `problem_summary`: Concise problem description
- `validated_solution_description`: Proven solution details
- `related_rule_ids`: List of improved Rule node IDs

### Relationships
- `(Learnt)-[:IMPROVES_RULE]->(Rule)`: Links validated solutions to improved rules

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Virtual environment support
- Optional: Neo4j server (if using Neo4j mode)

### Installation

1. **Clone and setup the project:**
   ```bash
   git clone <repository-url>
   cd "Ruling database"
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp graph_mcp.env.example .env
   # Edit .env to configure your database settings
   ```

### Environment Configuration

Choose your database backend by setting `GRAPH_DB_TYPE` in your `.env` file:

#### For NetworkX (File-based, recommended for development):
```env
GRAPH_DB_TYPE=networkx
NETWORKX_DATA_FILE=data/graph_data.json
```

#### For Neo4j (Production-ready):
```env
GRAPH_DB_TYPE=neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### Running the Server

```bash
# Using the installed script
ruling-mcp-server

# Or directly with Python
python -m src.server
```

## 🛠️ MCP Tools

The server exposes 8 main tools for AI agents:

### Rule Management Tools
1. **`rules/create_rule`** - Create new rules
2. **`rules/update_rule`** - Modify existing rules
3. **`rules/delete_rule`** - Remove rules
4. **`rules/get_all_rules`** - List rules with filtering
5. **`rules/get_rule_details`** - Get specific rule details

### Learning Management Tools
6. **`learning/record_validated_solution`** - Store proven solutions
7. **`learning/get_learnt_solutions`** - Retrieve learning history
8. **`learning/get_solution_details`** - Get specific solution details

## 💾 Database Modes

### NetworkX Mode (Default)
- **File-based storage** in `data/graph_data.json`
- **Zero dependencies** beyond Python packages
- **Perfect for development** and small deployments
- **Automatic persistence** with JSON serialization

### Neo4j Mode
- **Production-ready** graph database
- **High performance** for large datasets
- **Advanced querying** capabilities
- **Concurrent access** support

## 🧪 Development

### Running Tests
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src
```

### Code Quality
```bash
# Format code
black src/

# Type checking
mypy src/

# Linting
flake8 src/
```

## 📊 Initial Data

The system starts with two example rules:

1. **Frontend Rule** (`react_best_practices`)
   - Category: "frontend"
   - Type: "always"
   - Content: React development best practices

2. **Backend Rule** (`api_security`)
   - Category: "backend" 
   - Type: "always"
   - Content: API security guidelines

## 🔧 Configuration Options

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GRAPH_DB_TYPE` | Database type: "neo4j" or "networkx" | "networkx" | Yes |
| `NEO4J_URI` | Neo4j connection URI | bolt://localhost:7687 | If using Neo4j |
| `NEO4J_USER` | Neo4j username | neo4j | If using Neo4j |
| `NEO4J_PASSWORD` | Neo4j password | - | If using Neo4j |
| `NETWORKX_DATA_FILE` | NetworkX storage file | data/graph_data.json | If using NetworkX |
| `MCP_SERVER_HOST` | Server host | localhost | No |
| `MCP_SERVER_PORT` | Server port | 8000 | No |
| `LOG_LEVEL` | Logging level | INFO | No |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♀️ Support

For questions, issues, or contributions:
- Create an issue on GitHub
- Check the documentation in the `docs/` directory
- Review the test files for usage examples

## 🚀 Performance Goals

- **Response Time**: < 100ms for simple queries
- **Memory Usage**: Minimal footprint for file-based storage
- **Concurrent Access**: Support multiple MCP connections
- **Data Integrity**: Consistent data across operations 