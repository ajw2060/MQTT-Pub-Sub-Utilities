"""
Template Manager Module for MQTT Publisher GUI

This module handles the loading, validation, and management of MQTT message templates.
It provides a structured way to define and access message payload templates stored in YAML files.

Key Features:
- YAML template loading and validation
- Dynamic field type support
- Template organization and discovery
- Schema validation for template structure
"""

import os
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path

class TemplateManager:
    """Manages loading, validating, and accessing message templates."""
    
    def __init__(self, templates_dir: str):
        """Initialize the template manager with the directory containing template files.
        
        Args:
            templates_dir: Path to the directory containing template YAML files
        """
        self.templates_dir = Path(templates_dir)
        self.current_template: Optional[Dict[str, Any]] = None
        self._ensure_templates_dir()
    
    def _ensure_templates_dir(self) -> None:
        """Ensure the templates directory exists."""
        self.templates_dir.mkdir(parents=True, exist_ok=True)
    
    def list_templates(self) -> List[str]:
        """List all available template filenames.
        
        Returns:
            List of template filenames
        """
        return [f for f in os.listdir(self.templates_dir) if f.endswith(('.yaml', '.yml'))]
    
    def XXload_template(self, template_name: str) -> Dict[str, Any]:
        """Load a template by filename.
        
        Args:
            template_name: Name of the template file to load
            
        Returns:
            Parsed template data
            
        Raises:
            FileNotFoundError: If the template file doesn't exist
            yaml.YAMLError: If the template file contains invalid YAML
        """
        template_path = self.templates_dir / template_name
        with open(template_path, 'r') as f:
            template_data = yaml.safe_load(f)
        
        self.current_template = template_data
        return template_data
    




    def load_template(self, filename):
        """
        Loads a YAML template, ensuring that values like 'on', 'off', 'yes', 'no'
        are treated as strings, not booleans.
        """
        # --- This is the new, corrected loading logic ---

        # Create a custom SafeLoader that doesn't auto-convert boolean-like strings.
        # We do this by removing the rule that identifies booleans.
        class StringOnlySafeLoader(yaml.SafeLoader):
            pass

        # Get a copy of the default "implicit resolvers"
        resolvers = StringOnlySafeLoader.yaml_implicit_resolvers.copy()

        # Find the resolver that handles booleans and remove it for every
        # possible starting character ('o', 'y', 't', 'f', etc.)
        for char, resolver_list in resolvers.items():
            StringOnlySafeLoader.yaml_implicit_resolvers[char] = [
                (tag, regexp) for tag, regexp in resolver_list
                if tag != 'tag:yaml.org,2002:bool'
            ]
        # --- End of custom loader setup ---

        filepath = self.templates_dir / filename
        with open(filepath, 'r') as f:
            # Use our custom loader to parse the YAML.
            # This now correctly loads 'on' as a string, not a boolean.
            # Note: Using yaml.load() with a SafeLoader subclass is the correct, modern approach.
            self.current_template = yaml.load(f, Loader=StringOnlySafeLoader)
        
        return self.current_template



    def get_template_field(self, field_name: str) -> Optional[Dict[str, Any]]:
        """Get a field definition by name from the current template.
        
        Args:
            field_name: Name of the field to retrieve
            
        Returns:
            Field definition or None if not found
        """
        if not self.current_template or 'fields' not in self.current_template:
            return None
            
        for field in self.current_template['fields']:
            if field.get('name') == field_name:
                return field
        return None
    
    def get_template_text(self) -> str:
        """Get the template text from the current template.
        
        Returns:
            The template text or empty string if no template is loaded
        """
        if not self.current_template:
            return ""
        return self.current_template.get('template', '')
