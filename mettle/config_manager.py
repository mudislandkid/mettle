import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

class ConfigManager:
    """
    Manages configuration for the code counter application.
    
    This class is responsible for:
    - Loading configuration from YAML files
    - Providing access to configuration values
    - Validating configuration values
    
    Configuration is loaded from the following locations in order of precedence:
    1. Current directory (.mettle.yaml or .mettle.yml)
    2. Package directory (config.yaml)
    3. User home directory (~/.mettle.yaml or ~/.mettle.yml)
    """
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.load_config()
        self.validate_config()
    
    def get_config_paths(self) -> List[Path]:
        """Get list of possible config file locations in order of precedence."""
        paths = []
        
        # Current directory
        paths.append(Path.cwd() / '.mettle.yaml')
        paths.append(Path.cwd() / '.mettle.yml')
        
        # Package directory
        package_dir = Path(__file__).parent
        paths.append(package_dir / 'config.yaml')
        
        # User home directory
        home = Path.home()
        paths.append(home / '.mettle.yaml')
        paths.append(home / '.mettle.yml')
        
        return paths
    
    def load_config(self):
        """Load configuration from the first available config file."""
        for path in self.get_config_paths():
            if not path.exists():
                continue
            try:
                loaded = yaml.safe_load(path.read_text()) or {}
            except yaml.YAMLError as exc:
                # Don't silently fall through — surface which file is broken
                # so a typo in ~/.mettle.yaml is noticeable.
                import sys
                print(f"[mettle] warning: failed to parse {path}: {exc}", file=sys.stderr)
                continue
            self.config = loaded
            return

        # Fallback: bundled defaults.
        default_config = Path(__file__).parent / 'config.yaml'
        if default_config.exists():
            self.config = yaml.safe_load(default_config.read_text()) or {}
    
    def validate_config(self):
        """Validate the loaded configuration."""
        # Ensure required sections exist
        required_sections = ['exclude', 'reports', 'languages', 'output']
        for section in required_sections:
            if section not in self.config:
                self.config[section] = {}
        
        # Ensure exclude section has directories and files
        if 'directories' not in self.config['exclude']:
            self.config['exclude']['directories'] = []
        if 'files' not in self.config['exclude']:
            self.config['exclude']['files'] = []
        
        # Ensure reports section has required reporters
        if 'console' not in self.config['reports']:
            self.config['reports']['console'] = {'enabled': True}
        if 'markdown' not in self.config['reports']:
            self.config['reports']['markdown'] = {'enabled': True}
        if 'pdf' not in self.config['reports']:
            self.config['reports']['pdf'] = {'enabled': True}
        
        # Ensure output section has required fields
        if 'analysis_dir' not in self.config['output']:
            self.config['output']['analysis_dir'] = 'analysis'
        if 'default_format' not in self.config['output']:
            self.config['output']['default_format'] = 'both'
    
    def get_excluded_dirs(self) -> List[str]:
        """Get list of directories to exclude."""
        return self.config.get('exclude', {}).get('directories', [])
    
    def get_excluded_files(self) -> List[str]:
        """Get list of file patterns to exclude."""
        return self.config.get('exclude', {}).get('files', [])
    
    def get_report_config(self, reporter: str) -> Dict[str, Any]:
        """Get configuration for a specific reporter."""
        return self.config.get('reports', {}).get(reporter, {})
    
    def get_language_config(self, language: str) -> Dict[str, Any]:
        """Get configuration for a specific language (with inheritance)."""
        lang_config = self.config.get('languages', {}).get(language, {})

        if 'inherit_from' in lang_config:
            # Build a fresh dict so we don't mutate the cached parent — the
            # previous code did `parent.update(lang_config)` which polluted the
            # parent's entry on subsequent lookups.
            parent = self.get_language_config(lang_config['inherit_from'])
            merged = dict(parent)
            merged.update(lang_config)
            return merged

        return lang_config
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration."""
        return self.config.get('output', {})
    
    def should_show_metric(self, report_type: str, metric: str) -> bool:
        """Check if a metric should be shown in a report type."""
        report_config = self.get_report_config(report_type)
        return report_config.get('metrics', {}).get(f'show_{metric}', True)
    
    def is_language_enabled(self, language: str) -> bool:
        """Check if a language is enabled."""
        lang_config = self.get_language_config(language)
        return lang_config.get('enabled', True)
    
    def get_language_metrics(self, language: str) -> List[str]:
        """Get list of metrics to track for a language."""
        lang_config = self.get_language_config(language)
        return lang_config.get('metrics', []) 