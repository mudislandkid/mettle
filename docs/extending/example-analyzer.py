"""Example analyzer plugin — demonstrates the Mettle analyzer plugin contract.

This file is NOT loaded by Mettle. It exists as a reference for authors of
third-party analyzer plugins. To register a custom analyzer as an entry-point
plugin, package this kind of class into a separate distribution and declare
the entry point under [project.entry-points."mettle.analyzers"] in your
pyproject.toml. See docs/extending/plugin-authoring.md for details.
"""

import re
from typing import Tuple
# When implementing a plugin, import from your mettle installation:
# from mettle.analyzers.base import BaseAnalyzer
# from mettle.metrics.file_metrics import FileMetrics

# For reference in this example:
try:
    from mettle.analyzers.base import BaseAnalyzer
    from mettle.metrics.file_metrics import FileMetrics
except ImportError:
    # Fallback for when running this file standalone
    BaseAnalyzer = object  # type: ignore
    FileMetrics = object  # type: ignore

class TemplateAnalyzer(BaseAnalyzer):
    """
    Template analyzer class to serve as a starting point for new language analyzers.
    
    This class provides a skeleton implementation of a language-specific analyzer.
    It should not be used directly but rather as a reference for creating new analyzers.
    """
    
    def __init__(self):
        super().__init__()
        # Define language-specific regex patterns
        # Example patterns - replace with patterns specific to your language
        self.function_pattern = re.compile(r'function\s+\w+\s*\(')
        self.class_pattern = re.compile(r'class\s+\w+')
        
        # Import patterns
        self.import_pattern = re.compile(r'import\s+\w+')
        
        # Comment patterns
        self.single_comment = re.compile(r'//.*$', re.MULTILINE)
        self.multi_comment = re.compile(r'/\*[\s\S]*?\*/')
        
        # TODO patterns
        self.todo_pattern = re.compile(r'(?://|/\*|#)\s*TODO', re.IGNORECASE)
        
    def count_functions_and_classes(self, content: str) -> Tuple[int, int]:
        """
        Count functions and classes in the code.
        
        Args:
            content: The source code content as a string
            
        Returns:
            A tuple of (function_count, class_count)
        """
        functions = len(self.function_pattern.findall(content))
        classes = len(self.class_pattern.findall(content))
        return functions, classes
        
    def count_imports(self, content: str) -> int:
        """
        Count import statements in the code.
        
        Args:
            content: The source code content as a string
            
        Returns:
            The number of import statements
        """
        return len(self.import_pattern.findall(content))
        
    def analyze_content(self, content: str, file_path: str) -> FileMetrics:
        """
        Analyze the content of a file and return metrics.
        
        This method should be customized for each language to extract
        language-specific metrics.
        
        Args:
            content: The source code content as a string
            file_path: Path to the file being analyzed
            
        Returns:
            FileMetrics object with calculated metrics
        """
        # Get basic metrics from parent
        metrics = super().analyze_content(content, file_path)
        
        # Handle comments properly
        clean_content = content
        
        # First remove multi-line comments and count their lines
        multi_comments = self.multi_comment.findall(content)
        multi_comment_lines = sum(comment.count('\n') + 1 for comment in multi_comments)
        clean_content = self.multi_comment.sub('', clean_content)
        
        # Then remove single-line comments and count them
        single_comments = self.single_comment.findall(clean_content)
        single_comment_lines = len(single_comments)
        clean_content = self.single_comment.sub('', clean_content)
        
        # Update comment lines count
        metrics.comment_lines = multi_comment_lines + single_comment_lines
        
        # Count functions and classes
        functions, classes = self.count_functions_and_classes(clean_content)
        metrics.functions = functions
        metrics.classes = classes
        
        # Count imports
        metrics.imports = self.count_imports(clean_content)
        
        # Count TODOs
        metrics.todos = len(self.todo_pattern.findall(content))
        
        # Calculate actual code lines
        # Code lines are non-blank lines that aren't comments
        metrics.code_lines = metrics.total_lines - metrics.blank_lines - metrics.comment_lines
        
        return metrics