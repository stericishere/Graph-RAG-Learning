#!/usr/bin/env python3
"""
Configuration Management for Final Minimal Lean Graph Database MCP.

This module provides centralized configuration management including:
- Environment variable loading and validation
- Database type detection and configuration
- Factory functions for database adapter creation
- Logging and server configuration
"""

import os
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dotenv import load_dotenv

# Import database components
from .database import create_database, GraphDatabase, DatabaseConnectionError, ValidationError
from .models.rule import RuleCategory, RuleType
from .models.learnt import ErrorType, SeverityLevel


# ================================
# Environment Setup
# ================================

# Load environment variables from .env file
load_dotenv()


# ================================
# Configuration Classes
# ================================

class DatabaseConfig:
    """Database configuration management."""
    
    def __init__(self):
        self.db_type = self.get_db_type()
        self.config = self._get_database_config()
    
    @staticmethod
    def get_db_type() -> str:
        """
        Get the configured database type from environment.
        
        Returns:
            str: Database type ('neo4j' or 'networkx')
        """
        db_type = os.getenv('GRAPH_DB_TYPE', 'networkx').lower().strip()
        
        if db_type not in ['neo4j', 'networkx']:
            raise ValueError(f"Invalid GRAPH_DB_TYPE '{db_type}'. Must be 'neo4j' or 'networkx'")
        
        return db_type
    
    def _get_database_config(self) -> Dict[str, Any]:
        """
        Get database-specific configuration based on database type.
        
        Returns:
            Dict[str, Any]: Database configuration dictionary
            
        Raises:
            ValueError: If required environment variables are missing
        """
        if self.db_type == "neo4j":
            config = {
                "uri": os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                "username": os.getenv("NEO4J_USER", "neo4j"),  # Changed from 'user' to 'username'
                "password": os.getenv("NEO4J_PASSWORD", "password"),
                "timeout": int(os.getenv("DATABASE_TIMEOUT", "30")),
                "max_pool_size": int(os.getenv("MAX_CONNECTION_POOL_SIZE", "10"))
            }
            
            # Validate required Neo4j settings
            if not all([config["uri"], config["username"], config["password"]]):
                raise ValueError(
                    "Neo4j configuration incomplete. Required: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD"
                )
                
        elif self.db_type == "networkx":
            config = {
                "data_file": os.getenv("NETWORKX_DATA_FILE", "data/graph_data.json"),
                "enable_backup": os.getenv("ENABLE_BACKUP", "true").lower() == "true",
                "backup_count": int(os.getenv("BACKUP_COUNT", "5")),
                "auto_save": os.getenv("AUTO_SAVE", "true").lower() == "true"
            }
            
            # Ensure data directory exists
            data_dir = os.path.dirname(config["data_file"])
            if data_dir and not os.path.exists(data_dir):
                os.makedirs(data_dir, exist_ok=True)
        
        return config
    
    def get_db_adapter(self) -> GraphDatabase:
        """
        Factory function to return the appropriate database adapter.
        
        Returns:
            GraphDatabase: Configured database adapter instance
            
        Raises:
            ValueError: If unsupported database type is specified
            ValidationError: If configuration is invalid
        """
        return create_database(self.db_type, self.config)


class ServerConfig:
    """Server configuration management."""
    
    def __init__(self):
        self.host = os.getenv("MCP_SERVER_HOST", "localhost")
        self.port = int(os.getenv("MCP_SERVER_PORT", "8000"))
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.environment = os.getenv("ENVIRONMENT", "development")
        
        # CORS settings
        self.cors_origins = self._parse_cors_origins()
        self.cors_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
        self.cors_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.cors_headers = ["*"]
    
    def _parse_cors_origins(self) -> list:
        """Parse CORS origins from environment variable."""
        origins_str = os.getenv("CORS_ORIGINS", "*")
        if origins_str == "*":
            return ["*"]
        return [origin.strip() for origin in origins_str.split(",") if origin.strip()]


class LoggingConfig:
    """Logging configuration management."""
    
    def __init__(self):
        self.level = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_file = os.getenv("LOG_FILE", "logs/mcp-server.log")
        self.format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Ensure logs directory exists
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    
    def configure_logging(self):
        """Configure Python logging."""
        logging.basicConfig(
            level=getattr(logging, self.level),
            format=self.format,
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )


class PerformanceConfig:
    """Performance and caching configuration."""
    
    def __init__(self):
        self.enable_caching = os.getenv("ENABLE_CACHING", "true").lower() == "true"
        self.cache_ttl = int(os.getenv("CACHE_TTL", "3600"))
        self.max_workers = int(os.getenv("MAX_WORKERS", "4"))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))


# ================================
# Global Configuration Instance
# ================================

class Config:
    """Main configuration class that aggregates all configuration sections."""
    
    def __init__(self):
        self.database = DatabaseConfig()
        self.server = ServerConfig()
        self.logging = LoggingConfig()
        self.performance = PerformanceConfig()
        
        # Configure logging on initialization
        self.logging.configure_logging()
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate the entire configuration and return status.
        
        Returns:
            Dict[str, Any]: Validation results with any errors or warnings
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "database_type": self.database.db_type,
            "environment": self.server.environment
        }
        
        try:
            # Test database configuration
            db = self.database.get_db_adapter()
            results["database_config"] = "valid"
        except Exception as e:
            results["valid"] = False
            results["errors"].append(f"Database configuration error: {str(e)}")
        
        # Check for common issues
        if self.server.debug and self.server.environment == "production":
            results["warnings"].append("Debug mode enabled in production environment")
        
        if self.database.db_type == "neo4j":
            # Check Neo4j connection details
            if "localhost" in self.database.config.get("uri", ""):
                results["warnings"].append("Using localhost Neo4j URI - ensure Neo4j is running")
        
        return results


# ================================
# Global Configuration Instances
# ================================

# Create global configuration instance
config = Config()

# Convenience access to specific configurations
db_config = config.database
server_config = config.server
logging_config = config.logging
performance_config = config.performance


# ================================
# Factory Functions
# ================================

async def get_database() -> GraphDatabase:
    """
    Get configured database instance with connection.
    
    Returns:
        GraphDatabase: Connected database adapter
        
    Raises:
        DatabaseConnectionError: If database connection fails
        ValueError: If configuration is invalid
    """
    db = db_config.get_db_adapter()
    
    # Ensure connection
    if not db.is_connected:
        await db.connect()
    
    return db


def get_db_type() -> str:
    """
    Get the configured database type.
    
    Returns:
        str: Database type ('neo4j' or 'networkx')
    """
    return db_config.db_type


def get_db_adapter() -> GraphDatabase:
    """
    Factory function to return the appropriate database adapter (without connection).
    
    Returns:
        GraphDatabase: Configured database adapter instance
        
    Raises:
        ValueError: If unsupported database type is specified
        ValidationError: If configuration is invalid
    """
    return db_config.get_db_adapter()


# ================================
# Validation Functions
# ================================

def validate_enum_values() -> Dict[str, list]:
    """
    Get all valid enum values for validation purposes.
    
    Returns:
        Dict[str, list]: Dictionary mapping enum names to their valid values
    """
    return {
        "rule_categories": [cat.value for cat in RuleCategory],
        "rule_types": [rt.value for rt in RuleType],
        "error_types": [et.value for et in ErrorType],
        "severity_levels": [sl.value for sl in SeverityLevel]
    }


def is_valid_rule_category(category: str) -> bool:
    """Check if a category is valid."""
    try:
        RuleCategory(category.lower())
        return True
    except ValueError:
        return False


def is_valid_rule_type(rule_type: str) -> bool:
    """Check if a rule type is valid."""
    try:
        RuleType(rule_type.lower())
        return True
    except ValueError:
        return False


def is_valid_error_type(error_type: str) -> bool:
    """Check if an error type is valid."""
    try:
        ErrorType(error_type)
        return True
    except ValueError:
        return False


def is_valid_severity_level(severity: str) -> bool:
    """Check if a severity level is valid."""
    try:
        SeverityLevel(severity.lower())
        return True
    except ValueError:
        return False


# ================================
# Environment Helpers
# ================================

def get_environment_info() -> Dict[str, Any]:
    """
    Get comprehensive environment information for debugging.
    
    Returns:
        Dict[str, Any]: Environment details and configuration status
    """
    return {
        "database_type": config.database.db_type,
        "server_host": config.server.host,
        "server_port": config.server.port,
        "environment": config.server.environment,
        "debug_mode": config.server.debug,
        "log_level": config.logging.level,
        "caching_enabled": config.performance.enable_caching,
        "configuration_valid": config.validate_configuration()["valid"]
    }


def load_env_file(env_file: Optional[str] = None) -> bool:
    """
    Load environment variables from a specific file.
    
    Args:
        env_file: Path to environment file (defaults to .env)
        
    Returns:
        bool: True if file was loaded successfully
    """
    if env_file:
        return load_dotenv(env_file)
    return load_dotenv()


# ================================
# Module Exports
# ================================

__all__ = [
    # Configuration classes
    "Config",
    "DatabaseConfig", 
    "ServerConfig",
    "LoggingConfig",
    "PerformanceConfig",
    
    # Global instances
    "config",
    "db_config",
    "server_config", 
    "logging_config",
    "performance_config",
    
    # Factory functions
    "get_database",
    "get_db_type",
    "get_db_adapter",
    
    # Validation functions
    "validate_enum_values",
    "is_valid_rule_category",
    "is_valid_rule_type", 
    "is_valid_error_type",
    "is_valid_severity_level",
    
    # Environment helpers
    "get_environment_info",
    "load_env_file"
] 