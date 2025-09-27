"""
Configuration Manager Module for MQTT Publisher GUI

This module manages the application's configuration, including window settings,
MQTT connection parameters, and message history. It handles persistence of these
settings to disk and provides type-safe access to configuration values.

Key Features:
- JSON-based configuration storage
- Type-safe configuration access
- Automatic saving and loading of settings
- History management for messages and topics
"""

import json
import os
from typing import Dict, Any, List, Optional

class ConfigManager:
    """Manages application configuration and persistence."""
    
    def __init__(self, config_file: str):
        """Initialize the config manager with a configuration file.
        
        Args:
            config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = {
            'window_geometry': {
                'width': 750,
                'height': 650,
                'x': 0,
                'y': 0,
                'preview_width': 350,
                'main_pane_height': 300
            },
            'broker': 'localhost',
            'port': '1883',
            'username': '',
            'topic_history': []
        }
    
    def load(self) -> None:
        """Load configuration from file if it exists."""
        if not os.path.exists(self.config_file):
            return
            
        try:
            with open(self.config_file, 'r') as f:
                loaded_config = json.load(f)
                self._merge_config(loaded_config)
        except (json.JSONDecodeError, IOError) as e:
            pass
    
    def save(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except IOError as e:
            pass
    
    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """Merge new configuration values into the current config.
        
        Args:
            new_config: New configuration values to merge
        """
        for key, value in new_config.items():
            if key in self.config and isinstance(self.config[key], dict) and isinstance(value, dict):
                self.config[key].update(value)
            else:
                self.config[key] = value
    
    # Window geometry
    def set_window_geometry(self, geometry: Dict[str, int]) -> None:
        """Update window geometry settings.
        
        Args:
            geometry: Dictionary containing window geometry settings
        """
        if 'window_geometry' not in self.config:
            self.config['window_geometry'] = {}
        
        # Remove any old preview_width from root level
        if 'preview_width' in self.config:
            del self.config['preview_width']
            
        # Update window geometry with new values
        self.config['window_geometry'].update({
            'width': max(100, geometry.get('width', 750)),
            'height': max(100, geometry.get('height', 650)),
            'x': max(0, geometry.get('x', 0)),
            'y': max(0, geometry.get('y', 0)),
            'preview_width': max(100, min(geometry.get('preview_width', 350), 800)),
            'main_pane_height': max(100, min(geometry.get('main_pane_height', 300), 600))
        })
    
    def get_window_geometry(self) -> Dict[str, int]:
        """Get window geometry settings."""
        return self.config.get('window_geometry', {})
    
    # Preview width (kept for backward compatibility)
    def set_preview_width(self, width: int) -> None:
        """Set the preview pane width."""
        if 'window_geometry' not in self.config:
            self.config['window_geometry'] = {}
        self.config['window_geometry']['preview_width'] = max(100, min(width, 800))


    def get_preview_width(self) -> int:
        """Get the width of the preview pane."""
        return self.config.get('window_geometry', {}).get('preview_width', 350)

    # Connection settings
    def set_connection_settings(self, broker: str, port: str, username: str = '') -> None:
        """Set MQTT connection settings."""
        self.config['broker'] = broker
        self.config['port'] = port
        self.config['username'] = username
    
    def set_broker(self, broker: str) -> None:
        """Set the MQTT broker address."""
        self.config['broker'] = broker
    
    def set_port(self, port: str) -> None:
        """Set the MQTT broker port."""
        self.config['port'] = port
    
    def set_username(self, username: str) -> None:
        """Set the MQTT username."""
        self.config['username'] = username
    
    def get_connection_settings(self) -> Dict[str, str]:
        """Get MQTT connection settings."""
        return {
            'broker': self.config.get('broker', 'localhost'),
            'port': self.config.get('port', '1883'),
            'username': self.config.get('username', '')
        }
    
    # History
    def add_topic_to_history(self, topic: str) -> None:
        """Add a topic to history, removing duplicates and limiting history size."""
        self._add_to_history('topic_history', topic)
    
    def get_topic_history(self) -> List[str]:
        """Get the list of previously used topics."""
        return self.config['topic_history']
    
    def _add_to_history(self, history_key: str, item: str, max_items: int = 20) -> None:
        """Add an item to a history list, removing duplicates and limiting size."""
        if not item:
            return
            
        history = self.config.get(history_key, [])
        if item in history:
            history.remove(item)
        history.insert(0, item)
        self.config[history_key] = history[:max_items]
    
    # Preview width methods are defined above in the file
