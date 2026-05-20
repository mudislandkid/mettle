from dataclasses import dataclass, field


@dataclass
class FileMetrics:
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    characters: int = 0
    words: int = 0
    avg_line_length: float = 0
    max_line_length: int = 0
    functions: int = 0
    classes: int = 0
    todos: int = 0
    imports: int = 0
    # Per-file TODO markers (line_no, marker, text). Captured by the base
    # analyzer; reporters/cache treat this as optional.
    todo_items: list[tuple[int, str, str]] = field(default_factory=list)
    # Top-N most complex functions in this file (name, qualname, complexity, line_no).
    complex_functions: list[tuple[str, str, int, int]] = field(default_factory=list)

    # Python
    decorators: int = 0
    list_comprehensions: int = 0
    lambda_functions: int = 0
    f_strings: int = 0

    # JavaScript / TypeScript
    jsx_components: int = 0
    react_hooks: int = 0
    async_functions: int = 0
    interfaces: int = 0
    type_aliases: int = 0
    enums: int = 0

    # HTML/CSS
    elements: int = 0
    attributes: int = 0
    media_queries: int = 0
    selectors: int = 0

    # SQL
    tables: int = 0
    queries: int = 0
    indexes: int = 0
