#!/usr/bin/env python3
"""
Tests for Configuration Management System.

This module tests centralized configuration management including:
- Environment variable loading
- Database type detection
- Configuration validation
- Factory functions
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

from src.config import (
    Config, DatabaseConfig, ServerConfig, LoggingConfig, PerformanceConfig,
    config, db_config, server_config, logging_config, performance_config,
    get_database, get_db_type, get_db_adapter,
    validate_enum_values, is_valid_rule_category, is_valid_rule_type,
    is_valid_error_type, is_valid_severity_level,
    get_environment_info, load_env_file
)
from src.database import DatabaseConnectionError, ValidationError


class TestDatabaseConfig:
    """Test database configuration management."""
    
    def test_get_db_type_default(self):
        """Test default database type is networkx."""
        with patch.dict(os.environ, {}, clear=True):
            assert DatabaseConfig.get_db_type() == "networkx"
    
    def test_get_db_type_from_env(self):
        """Test database type from environment variable."""
        with patch.dict(os.environ, {"GRAPH_DB_TYPE": "neo4j"}):
            assert DatabaseConfig.get_db_type() == "neo4j"
        
        with patch.dict(os.environ, {"GRAPH_DB_TYPE": "  NetworkX  "}):
            assert DatabaseConfig.get_db_type() == "networkx"
    
    def test_get_db_type_invalid(self):
        """Test invalid database type raises ValueError."""
        with patch.dict(os.environ, {"GRAPH_DB_TYPE": "invalid"}):
            with pytest.raises(ValueError, match="Invalid GRAPH_DB_TYPE"):
                DatabaseConfig.get_db_type()
    
    def test_networkx_config_creation(self):
        """Test NetworkX configuration creation."""
        with patch.dict(os.environ, {"GRAPH_DB_TYPE": "networkx"}, clear=True):
            config = DatabaseConfig()
            assert config.db_type == "networkx"
            assert "data_file" in config.config
            assert config.config["data_file"] == "data/graph_data.json"
            assert config.config["enable_backup"] is True
    
    def test_networkx_custom_config(self):
        """Test NetworkX custom configuration."""
        with patch.dict(os.environ, {
            "GRAPH_DB_TYPE": "networkx",
            "NETWORKX_DATA_FILE": "custom/path.json",
            "ENABLE_BACKUP": "false",
            "BACKUP_COUNT": "3",
            "AUTO_SAVE": "false"
        }):
            config = DatabaseConfig()
            assert config.config["data_file"] == "custom/path.json"
            assert config.config["enable_backup"] is False
            assert config.config["backup_count"] == 3
            assert config.config["auto_save"] is False
    
    def test_neo4j_config_creation(self):
        """Test Neo4j configuration creation."""
        with patch.dict(os.environ, {
            "GRAPH_DB_TYPE": "neo4j",
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j", 
            "NEO4J_PASSWORD": "password"
        }):
            config = DatabaseConfig()
            assert config.db_type == "neo4j"
            assert config.config["uri"] == "bolt://localhost:7687"
            assert config.config["username"] == "neo4j"  # Changed from 'user' to 'username'
            assert config.config["password"] == "password"
            assert config.config["timeout"] == 30
    
    def test_neo4j_incomplete_config(self):
        """Test Neo4j incomplete configuration raises ValueError."""
        with patch.dict(os.environ, {
            "GRAPH_DB_TYPE": "neo4j",
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "",  # Empty username should fail validation
            "NEO4J_PASSWORD": ""  # Empty password should fail validation
        }):
            with pytest.raises(ValueError, match="Neo4j configuration incomplete"):
                DatabaseConfig()
    
    def test_neo4j_custom_config(self):
        """Test Neo4j custom configuration."""
        with patch.dict(os.environ, {
            "GRAPH_DB_TYPE": "neo4j",
            "NEO4J_URI": "bolt://custom:7687",
            "NEO4J_USER": "custom_user",
            "NEO4J_PASSWORD": "custom_password",
            "DATABASE_TIMEOUT": "60",
            "MAX_CONNECTION_POOL_SIZE": "20"
        }):
            config = DatabaseConfig()
            assert config.config["uri"] == "bolt://custom:7687"
            assert config.config["username"] == "custom_user"  # Changed from 'user' to 'username'
            assert config.config["password"] == "custom_password"
            assert config.config["timeout"] == 60
            assert config.config["max_pool_size"] == 20
    
    @patch('src.config.create_database')  # Patch in the config module where it's imported
    def test_get_db_adapter_networkx(self, mock_create):
        """Test database adapter creation for NetworkX."""
        mock_adapter = MagicMock()
        mock_create.return_value = mock_adapter
        
        with patch.dict(os.environ, {"GRAPH_DB_TYPE": "networkx"}):
            config = DatabaseConfig()
            adapter = config.get_db_adapter()
            
            mock_create.assert_called_once_with("networkx", config.config)
            assert adapter == mock_adapter
    
    @patch('src.config.create_database')  # Patch in the config module where it's imported
    def test_get_db_adapter_neo4j(self, mock_create):
        """Test database adapter creation for Neo4j."""
        mock_adapter = MagicMock()
        mock_create.return_value = mock_adapter
        
        with patch.dict(os.environ, {
            "GRAPH_DB_TYPE": "neo4j",
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password"
        }):
            config = DatabaseConfig()
            adapter = config.get_db_adapter()
            
            mock_create.assert_called_once_with("neo4j", config.config)
            assert adapter == mock_adapter


class TestServerConfig:
    """Test server configuration management."""
    
    def test_default_config(self):
        """Test default server configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config = ServerConfig()
            assert config.host == "localhost"
            assert config.port == 8000
            assert config.debug is False
            assert config.environment == "development"
            assert config.cors_origins == ["*"]
            assert config.cors_credentials is True
    
    def test_custom_config(self):
        """Test custom server configuration."""
        with patch.dict(os.environ, {
            "MCP_SERVER_HOST": "0.0.0.0",
            "MCP_SERVER_PORT": "3000",
            "DEBUG": "true",
            "ENVIRONMENT": "production",
            "CORS_ORIGINS": "http://localhost:3000,http://localhost:8080",
            "CORS_ALLOW_CREDENTIALS": "false"
        }):
            config = ServerConfig()
            assert config.host == "0.0.0.0"
            assert config.port == 3000
            assert config.debug is True
            assert config.environment == "production"
            assert config.cors_origins == ["http://localhost:3000", "http://localhost:8080"]
            assert config.cors_credentials is False
    
    def test_cors_origins_parsing(self):
        """Test CORS origins parsing."""
        # Test wildcard
        with patch.dict(os.environ, {"CORS_ORIGINS": "*"}):
            config = ServerConfig()
            assert config.cors_origins == ["*"]
        
        # Test multiple origins
        with patch.dict(os.environ, {"CORS_ORIGINS": "http://a.com,http://b.com"}):
            config = ServerConfig()
            assert config.cors_origins == ["http://a.com", "http://b.com"]
        
        # Test with spaces
        with patch.dict(os.environ, {"CORS_ORIGINS": " http://a.com , http://b.com "}):
            config = ServerConfig()
            assert config.cors_origins == ["http://a.com", "http://b.com"]


class TestLoggingConfig:
    """Test logging configuration management."""
    
    def test_default_config(self):
        """Test default logging configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config = LoggingConfig()
            assert config.level == "INFO"
            assert config.log_file == "logs/mcp-server.log"
            assert "%(asctime)s" in config.format
    
    def test_custom_config(self):
        """Test custom logging configuration."""
        with patch.dict(os.environ, {
            "LOG_LEVEL": "debug",
            "LOG_FILE": "custom/path.log"
        }):
            config = LoggingConfig()
            assert config.level == "DEBUG"
            assert config.log_file == "custom/path.log"
    
    @patch('os.makedirs')
    def test_log_directory_creation(self, mock_makedirs):
        """Test log directory creation."""
        with patch.dict(os.environ, {"LOG_FILE": "custom/logs/app.log"}):
            LoggingConfig()
            mock_makedirs.assert_called_once_with("custom/logs", exist_ok=True)


class TestPerformanceConfig:
    """Test performance configuration management."""
    
    def test_default_config(self):
        """Test default performance configuration."""
        with patch.dict(os.environ, {}, clear=True):
            config = PerformanceConfig()
            assert config.enable_caching is True
            assert config.cache_ttl == 3600
            assert config.max_workers == 4
            assert config.request_timeout == 30
    
    def test_custom_config(self):
        """Test custom performance configuration."""
        with patch.dict(os.environ, {
            "ENABLE_CACHING": "false",
            "CACHE_TTL": "7200",
            "MAX_WORKERS": "8",
            "REQUEST_TIMEOUT": "60"
        }):
            config = PerformanceConfig()
            assert config.enable_caching is False
            assert config.cache_ttl == 7200
            assert config.max_workers == 8
            assert config.request_timeout == 60


class TestMainConfig:
    """Test main configuration class."""
    
    @patch('src.config.LoggingConfig.configure_logging')
    def test_config_initialization(self, mock_configure_logging):
        """Test main config initialization."""
        with patch.dict(os.environ, {"GRAPH_DB_TYPE": "networkx"}):
            config = Config()
            assert isinstance(config.database, DatabaseConfig)
            assert isinstance(config.server, ServerConfig) 
            assert isinstance(config.logging, LoggingConfig)
            assert isinstance(config.performance, PerformanceConfig)
            mock_configure_logging.assert_called_once()
    
    @patch('src.config.DatabaseConfig.get_db_adapter')
    def test_validate_configuration_success(self, mock_get_adapter):
        """Test successful configuration validation."""
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        
        with patch.dict(os.environ, {"GRAPH_DB_TYPE": "networkx"}):
            config = Config()
            result = config.validate_configuration()
            
            assert result["valid"] is True
            assert result["database_config"] == "valid"
            assert result["database_type"] == "networkx"
            assert "errors" in result
            assert "warnings" in result
    
    @patch('src.config.DatabaseConfig.get_db_adapter')
    def test_validate_configuration_failure(self, mock_get_adapter):
        """Test configuration validation failure."""
        mock_get_adapter.side_effect = ValueError("Configuration error")
        
        with patch.dict(os.environ, {"GRAPH_DB_TYPE": "networkx"}):
            config = Config()
            result = config.validate_configuration()
            
            assert result["valid"] is False
            assert len(result["errors"]) > 0
            assert "Configuration error" in result["errors"][0]
    
    def test_validate_configuration_warnings(self):
        """Test configuration validation warnings."""
        with patch.dict(os.environ, {
            "GRAPH_DB_TYPE": "neo4j",
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password",
            "DEBUG": "true",
            "ENVIRONMENT": "production"
        }):
            config = Config()
            result = config.validate_configuration()
            
            warnings = result["warnings"]
            assert any("Debug mode enabled in production" in w for w in warnings)
            assert any("Using localhost Neo4j URI" in w for w in warnings)


class TestFactoryFunctions:
    """Test factory functions."""
    
    @pytest.mark.asyncio
    @patch('src.config.db_config.get_db_adapter')
    async def test_get_database_connected(self, mock_get_adapter):
        """Test get_database with already connected adapter."""
        mock_adapter = MagicMock()
        mock_adapter.is_connected = True
        mock_get_adapter.return_value = mock_adapter
        
        result = await get_database()
        assert result == mock_adapter
        mock_adapter.connect.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('src.config.db_config.get_db_adapter')
    async def test_get_database_not_connected(self, mock_get_adapter):
        """Test get_database with disconnected adapter."""
        mock_adapter = AsyncMock()
        mock_adapter.is_connected = False
        mock_get_adapter.return_value = mock_adapter
        
        result = await get_database()
        assert result == mock_adapter
        mock_adapter.connect.assert_called_once()
    
    def test_get_db_type(self):
        """Test get_db_type function."""
        with patch.dict(os.environ, {"GRAPH_DB_TYPE": "neo4j"}):
            # Refresh the global config
            from src.config import db_config
            db_config.db_type = DatabaseConfig.get_db_type()
            assert get_db_type() == "neo4j"
    
    @patch('src.config.db_config.get_db_adapter')
    def test_get_db_adapter(self, mock_get_adapter):
        """Test get_db_adapter function."""
        mock_adapter = MagicMock()
        mock_get_adapter.return_value = mock_adapter
        
        result = get_db_adapter()
        assert result == mock_adapter
        mock_get_adapter.assert_called_once()


class TestValidationFunctions:
    """Test validation helper functions."""
    
    def test_validate_enum_values(self):
        """Test enum values validation."""
        result = validate_enum_values()
        
        assert "rule_categories" in result
        assert "rule_types" in result
        assert "error_types" in result
        assert "severity_levels" in result
        
        assert isinstance(result["rule_categories"], list)
        assert isinstance(result["rule_types"], list)
        assert isinstance(result["error_types"], list) 
        assert isinstance(result["severity_levels"], list)
        
        # Check some expected values
        assert "frontend" in result["rule_categories"]
        assert "best_practice" in result["rule_types"]
        assert "IncorrectAction" in result["error_types"]  # Use actual ErrorType enum value
        assert "critical" in result["severity_levels"]
    
    def test_is_valid_rule_category(self):
        """Test rule category validation."""
        assert is_valid_rule_category("frontend")
        assert is_valid_rule_category("BACKEND")  # Case insensitive
        assert not is_valid_rule_category("invalid")
    
    def test_is_valid_rule_type(self):
        """Test rule type validation."""
        assert is_valid_rule_type("best_practice")
        assert is_valid_rule_type("ANTI_PATTERN")  # Case insensitive
        assert not is_valid_rule_type("invalid")
    
    def test_is_valid_error_type(self):
        """Test error type validation."""
        assert is_valid_error_type("IncorrectAction")  # Use actual ErrorType enum value
        assert not is_valid_error_type("InvalidError")
    
    def test_is_valid_severity_level(self):
        """Test severity level validation."""
        assert is_valid_severity_level("critical")
        assert is_valid_severity_level("MAJOR")  # Case insensitive
        assert not is_valid_severity_level("invalid")


class TestEnvironmentHelpers:
    """Test environment helper functions."""
    
    def test_get_environment_info(self):
        """Test environment information retrieval."""
        info = get_environment_info()
        
        assert "database_type" in info
        assert "server_host" in info
        assert "server_port" in info
        assert "environment" in info
        assert "debug_mode" in info
        assert "log_level" in info
        assert "caching_enabled" in info
        assert "configuration_valid" in info
        
        # Just check the type is valid, not a specific value since it depends on global config
        assert info["database_type"] in ["networkx", "neo4j"]
    
    def test_load_env_file_default(self):
        """Test loading default .env file."""
        with patch('src.config.load_dotenv') as mock_load:
            mock_load.return_value = True
            
            result = load_env_file()
            assert result is True
            mock_load.assert_called_once_with()
    
    def test_load_env_file_custom(self):
        """Test loading custom env file."""
        with patch('src.config.load_dotenv') as mock_load:
            mock_load.return_value = True
            
            result = load_env_file("custom.env")
            assert result is True
            mock_load.assert_called_once_with("custom.env")


class TestGlobalInstances:
    """Test global configuration instances."""
    
    def test_global_instances_exist(self):
        """Test that global configuration instances exist."""
        # Import to ensure they are created
        from src.config import config, db_config, server_config, logging_config, performance_config
        
        assert config is not None
        assert db_config is not None
        assert server_config is not None
        assert logging_config is not None
        assert performance_config is not None
        
        assert isinstance(config, Config)
        assert isinstance(db_config, DatabaseConfig)
        assert isinstance(server_config, ServerConfig)
        assert isinstance(logging_config, LoggingConfig)
        assert isinstance(performance_config, PerformanceConfig)


class TestEnvironmentIntegration:
    """Test real environment integration."""
    
    def test_with_real_env_file(self):
        """Test configuration with a real environment file."""
        # Create a temporary .env file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("GRAPH_DB_TYPE=neo4j\n")
            f.write("NEO4J_URI=bolt://test:7687\n")
            f.write("NEO4J_USER=test\n")
            f.write("NEO4J_PASSWORD=test\n")
            f.write("MCP_SERVER_PORT=9000\n")
            f.write("LOG_LEVEL=DEBUG\n")
            env_file = f.name
        
        try:
            # Load the environment file
            result = load_env_file(env_file)
            assert result is True
            
            # Test that configuration picks up the values
            # Note: This might be affected by global state, so we create new instances
            db_cfg = DatabaseConfig()
            server_cfg = ServerConfig()
            logging_cfg = LoggingConfig()
            
            assert db_cfg.db_type == "neo4j"
            assert db_cfg.config["uri"] == "bolt://test:7687"
            assert server_cfg.port == 9000
            assert logging_cfg.level == "DEBUG"
            
        finally:
            # Clean up
            os.unlink(env_file)


if __name__ == "__main__":
    pytest.main([__file__]) 