"""
Environment variables loader for Shakespeare AI.

This module handles loading environment variables from a .env file
and provides them to the rest of the application.
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

# Try to import dotenv, but handle the case where it's not installed
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("Warning: python-dotenv not installed. Environment variables must be set manually.")

# Default environment variable values
DEFAULT_ENV_VALUES = {
    "MODEL_PROVIDER": "anthropic",
    "MODEL_NAME": "claude-3-7-sonnet-20250219",
    "TEMPERATURE": 0.7,
    "OUTPUT_DIR": "outputs/translated_scenes",
    "LOG_LEVEL": "INFO",
    "SAVE_LOGS": True,
}

def load_env_file(env_path: Optional[str] = None) -> bool:
    """
    Load environment variables from a .env file.
    
    Args:
        env_path: Path to the .env file. If not provided, looks in current directory
                 and parent directories.
        
    Returns:
        True if environment was loaded successfully, False otherwise
    """
    if not DOTENV_AVAILABLE:
        return False
    
    # If no specific path provided, try to find a .env file
    if env_path is None:
        # Start with current directory
        current_dir = Path.cwd()
        
        # Try current directory and up to 3 parent directories
        for _ in range(4):
            test_path = current_dir / ".env"
            if test_path.exists():
                env_path = str(test_path)
                break
            # Move up one directory
            parent_dir = current_dir.parent
            if parent_dir == current_dir:  # Reached root directory
                break
            current_dir = parent_dir
    
    # Load the .env file if found
    if env_path and Path(env_path).exists():
        return load_dotenv(env_path)
    else:
        return False

def get_env(var_name: str, default: Any = None) -> Any:
    """
    Get an environment variable value, with appropriate type conversion.
    
    Args:
        var_name: Name of the environment variable
        default: Default value to return if variable is not set
        
    Returns:
        The value of the environment variable, converted to the appropriate type
    """
    # If default is None, check DEFAULT_ENV_VALUES
    if default is None and var_name in DEFAULT_ENV_VALUES:
        default = DEFAULT_ENV_VALUES[var_name]
    
    # Get the value from environment
    value = os.environ.get(var_name)
    
    # Return default if not found
    if value is None:
        return default
    
    # Type conversion based on default value type
    if default is not None:
        if isinstance(default, bool):
            return value.lower() in ('true', 'yes', '1', 't', 'y')
        elif isinstance(default, int):
            try:
                return int(value)
            except ValueError:
                return default
        elif isinstance(default, float):
            try:
                return float(value)
            except ValueError:
                return default
        elif isinstance(default, list):
            return value.split(',')
    
    # Return as string if no type conversion needed
    return value

def get_api_key(provider: str) -> Optional[str]:
    """
    Get the API key for a specific provider.
    
    Args:
        provider: Provider name (e.g., "openai", "anthropic")
        
    Returns:
        API key string or None if not found
    """
    provider = provider.upper()
    key_name = f"{provider}_API_KEY"
    
    return get_env(key_name)

def load_env_to_dict() -> Dict[str, Any]:
    """
    Load all environment variables into a dictionary.
    
    Returns:
        Dictionary containing all environment variables
    """
    env_dict = {}
    
    # Load all default variables with their values from environment
    for var_name, default_value in DEFAULT_ENV_VALUES.items():
        env_dict[var_name] = get_env(var_name, default_value)
    
    # Add API keys
    for provider in ["OPENAI", "ANTHROPIC"]:
        key_name = f"{provider}_API_KEY"
        key_value = get_env(key_name)
        if key_value:
            env_dict[key_name] = key_value
    
    return env_dict

def initialize():
    """
    Initialize the environment. Should be called at application startup.
    
    Returns:
        True if initialization was successful, False otherwise
    """
    # Try to load environment from .env file
    env_loaded = load_env_file()
    
    # Check for critical API keys
    openai_key = get_api_key("openai")
    anthropic_key = get_api_key("anthropic")
    
    if not openai_key and not anthropic_key:
        print("Warning: No API keys found for OpenAI or Anthropic.")
        print("Please set OPENAI_API_KEY and/or ANTHROPIC_API_KEY environment variables.")
    
    # Set up logging based on environment
    log_level = get_env("LOG_LEVEL", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return env_loaded or (openai_key is not None or anthropic_key is not None)

# Auto-initialize when module is imported
initialized = initialize()