from __future__ import annotations

from pathlib import Path

from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.traceback import Traceback

from textual.app import ComposeResult
from textual.reactive import reactive
from textual.widgets import Static

class CodeViewer(Static):
    """Syntax-highlighted code viewer panel."""

    DEFAULT_CSS = """
    CodeViewer {
        width: 100%;
        height: 100%;
        overflow: auto scroll;
        padding: 0 1;
        background: $surface;
    }
    
    CodeViewer > Static {
        width: auto;
    }
    """

    file_path: reactive[Path | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Static(id="code-content")

    def watch_file_path(self, file_path: Path | None) -> None:
        """Load and display the file when path changes."""
        content = self.query_one("#code-content", Static)
        
        if file_path is None:
            content.update("[dim italic]Select a file from the project tree to view its contents[/dim italic]")
            return
        
        if not file_path.exists():
            content.update(f"[red]File not found: {file_path}[/red]")
            return
        
        if not file_path.is_file():
            content.update(f"[dim]{file_path} is a directory[/dim]")
            return
        
        try:
            # Check file size - don't try to load huge files
            file_size = file_path.stat().st_size
            if file_size > 1_000_000:  # 1MB limit
                content.update(f"[yellow]File too large to display ({file_size:,} bytes)[/yellow]")
                return
            
            code = file_path.read_text(encoding="utf-8", errors="replace")
            
            # Determine lexer from file extension
            ext = file_path.suffix.lower()
            lexer_map = {
                ".py": "python",
                ".c": "c",
                ".h": "c",
                ".cpp": "cpp",
                ".hpp": "cpp",
                ".cc": "cpp",
                ".cxx": "cpp",
                ".asm": "nasm",
                ".s": "gas",
                ".inc": "nasm",
                ".json": "json",
                ".yaml": "yaml",
                ".yml": "yaml",
                ".toml": "toml",
                ".md": "markdown",
                ".rst": "rst",
                ".sh": "bash",
                ".bash": "bash",
                ".zsh": "zsh",
                ".fish": "fish",
                ".ps1": "powershell",
                ".bat": "batch",
                ".cmd": "batch",
                ".js": "javascript",
                ".ts": "typescript",
                ".html": "html",
                ".htm": "html",
                ".css": "css",
                ".tcss": "css",
                ".xml": "xml",
                ".java": "java",
                ".cs": "csharp",
                ".rs": "rust",
                ".go": "go",
                ".rb": "ruby",
                ".lua": "lua",
                ".make": "make",
                ".mk": "make",
            }
            # Handle Makefile specially
            if file_path.name.lower() in ("makefile", "gnumakefile"):
                lexer = "make"
            else:
                lexer = lexer_map.get(ext, "text")
            
            # Render Markdown files specially
            if ext in (".md", ".markdown"):
                md = Markdown(code)
                content.update(md)
            else:
                syntax = Syntax(
                    code, 
                    lexer, 
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=False,
                )
                content.update(syntax)
            
        except UnicodeDecodeError:
            content.update("[yellow]Binary file - cannot display[/yellow]")
        except Exception as e:
            content.update(Traceback(theme="monokai", width=None))
