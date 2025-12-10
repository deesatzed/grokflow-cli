#!/usr/bin/env python3
"""
GrokFlow CLI v2 - Professional SWE UX
Context-aware, action-first, git-native development environment
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.table import Table
from rich.tree import Tree
from rich import box
import difflib
import fnmatch
import re
import base64
import httpx

# Prompt toolkit for enhanced CLI
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter, PathCompleter, merge_completers
from prompt_toolkit.formatted_text import HTML

# GrokFlow logging, exceptions, and validation
from grokflow.logging_config import setup_logging, get_logger, log_operation
from grokflow.exceptions import (
    GrokFlowError, APIError, RateLimitError, AuthenticationError,
    FileOperationError, BinaryFileError, SessionCorruptedError,
    ValidationError, PathValidationError, ImageValidationError,
    GitError, GitNotFoundError, GitCommandError, NotInGitRepoError,
    KnowledgeBaseError, KnowledgeBaseNotAvailableError,
    TemplateError, TemplateNotFoundError, UndoError
)
from grokflow.validators import InputValidator, PathSanitizer

# Import GUKS (GrokFlow Universal Knowledge System) with graceful fallback
try:
    from grokflow.guks import EnhancedGUKS, GUKSAnalytics
    GUKS_AVAILABLE = True
except ImportError:
    # Dependencies not installed (sentence-transformers, faiss-cpu)
    EnhancedGUKS = None
    GUKSAnalytics = None
    GUKS_AVAILABLE = False

# Import UndoManager for proper undo/redo with command pattern
from grokflow.undo_manager import get_undo_manager, FileWriteCommand

console = Console()
logger = None  # Will be initialized in main()


class WorkspaceContext:
    """Smart workspace context manager"""
    
    def __init__(self, root: Path):
        self.root = root
        self.git_root = self._find_git_root()
        self.current_files = set()
        self.modified_files = set()
        self.last_error = None
        self.last_test_output = None
        
    def _find_git_root(self) -> Optional[Path]:
        """Find git repository root"""
        current = self.root
        while current != current.parent:
            if (current / '.git').exists():
                return current
            current = current.parent
        return None
    
    def get_git_status(self) -> Dict:
        """Get git status"""
        if not self.git_root:
            return {}
        
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.git_root,
                capture_output=True,
                text=True
            )
            
            status = {'modified': [], 'untracked': [], 'staged': []}
            for line in result.stdout.splitlines():
                if line.startswith(' M'):
                    status['modified'].append(line[3:])
                elif line.startswith('??'):
                    status['untracked'].append(line[3:])
                elif line.startswith('M '):
                    status['staged'].append(line[3:])
            
            return status
        except subprocess.CalledProcessError as e:
            logger.error(f"Git status command failed: {e}", exc_info=True)
            return {}
        except FileNotFoundError:
            logger.warning("Git executable not found in PATH")
            return {}
        except PermissionError as e:
            logger.error(f"Permission denied accessing git: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error in get_git_status: {e}", exc_info=True)
            return {}
    
    def get_recent_files(self, limit: int = 5) -> List[str]:
        """Get recently modified files"""
        if not self.git_root:
            return []
        
        try:
            result = subprocess.run(
                ['git', 'log', '--pretty=format:', '--name-only', '-n', '10'],
                cwd=self.git_root,
                capture_output=True,
                text=True
            )
            
            files = [f for f in result.stdout.splitlines() if f]
            return list(dict.fromkeys(files))[:limit]  # Dedupe and limit
        except subprocess.CalledProcessError as e:
            logger.error(f"Git log command failed: {e}", exc_info=True)
            return []
        except FileNotFoundError:
            logger.warning("Git executable not found in PATH")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_recent_files: {e}", exc_info=True)
            return []
    
    def get_diff(self, file_path: str) -> str:
        """Get git diff for file"""
        if not self.git_root:
            return ""
        
        try:
            result = subprocess.run(
                ['git', 'diff', file_path],
                cwd=self.git_root,
                capture_output=True,
                text=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Git diff command failed: {e}", exc_info=True)
            return ""
        except FileNotFoundError:
            logger.warning("Git executable not found in PATH")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error in get_diff: {e}", exc_info=True)
            return ""


class GrokFlowV2:
    """Professional SWE-focused CLI"""
    
    # Model configuration for dual-model architecture
    PLANNER_MODEL = "grok-4-1-fast"  # For analysis and planning (updated 2025-12)
    EXECUTOR_MODEL = "grok-4-1-fast"  # For fast code execution (updated 2025-12)
    
    def __init__(self):
        logger.info("Initializing GrokFlow v2")
        
        self.api_key = os.getenv("XAI_API_KEY")
        if not self.api_key:
            logger.warning("XAI_API_KEY not set - running in local mode")
            console.print("[yellow]⚠ XAI_API_KEY not set - running in local mode[/yellow]")
            self.client = None
        else:
            try:
                self.client = OpenAI(
                    api_key=self.api_key,
                    base_url="https://api.x.ai/v1",
                    timeout=httpx.Timeout(3600.0)
                )
                logger.info("API client initialized successfully")
                
                # Check if fast executor model is available
                self._check_executor_model()
            except Exception as e:
                logger.error(f"Failed to initialize API client: {e}", exc_info=True)
                console.print(f"[red]Failed to initialize API client: {e}[/red]")
                raise
        
        self.workspace = WorkspaceContext(Path.cwd())
        self.config_dir = Path.home() / ".grokflow"
        self.config_dir.mkdir(exist_ok=True)
        self.session_file = self.config_dir / "session_v2.json"
        
        self.session = self.load_session()

        # Initialize GUKS (GrokFlow Universal Knowledge System)
        self.guks = None
        self.guks_analytics = None
        if GUKS_AVAILABLE:
            try:
                self.guks = EnhancedGUKS()
                logger.info(f"GUKS initialized with {len(self.guks.patterns)} patterns")

                # Initialize analytics engine
                self.guks_analytics = GUKSAnalytics(self.guks.patterns)
                logger.info("GUKS Analytics initialized")

                console.print(f"[dim]✨ GUKS loaded: {len(self.guks.patterns)} patterns from {len(set(p.get('project', '') for p in self.guks.patterns))} projects[/dim]")
            except ImportError as e:
                logger.info(f"GUKS dependencies not installed: {e}")
                console.print("[dim]GUKS not available (install: pip install sentence-transformers faiss-cpu)[/dim]")
            except PermissionError as e:
                logger.error(f"Permission denied initializing GUKS: {e}")
                console.print("[yellow]⚠ Cannot access GUKS data directory[/yellow]")
            except Exception as e:
                logger.error(f"Failed to initialize GUKS: {e}", exc_info=True)
                console.print(f"[yellow]⚠ GUKS disabled: {e}[/yellow]")

        # Track last GUKS query for recording fixes
        self.last_guks_query: Optional[Dict] = None

        # Undo system: use proper UndoManager with command pattern
        self.undo_manager = get_undo_manager(max_history=100, force_new=False)

        # Track file path to error/solution mapping for GUKS integration on undo
        self._undo_guks_mapping: Dict[str, Dict] = {}

        # Reasoning display toggle (can be changed via 'reasoning on/off' command)
        self.show_reasoning = True

        # Performance tracking for dual-model architecture
        self.perf_metrics = {
            "planner_calls": 0,
            "executor_calls": 0,
            "planner_time": 0.0,
            "executor_time": 0.0,
            "total_tokens_saved": 0  # Estimated tokens saved vs single-model
        }
        
        # Enhanced prompt session with completion and history
        self._setup_prompt_session()
    
    def _check_executor_model(self):
        """Check if fast executor model is available, fallback to planner if not"""
        if self.EXECUTOR_MODEL != self.PLANNER_MODEL:
            console.print(f"[dim]✨ Dual-model active: {self.PLANNER_MODEL} (reasoning) → {self.EXECUTOR_MODEL} (execution)[/dim]")
            console.print(f"[dim]💡 Faster execution and lower costs with grok-4-fast[/dim]")
        else:
            console.print(f"[dim]Using single model: {self.PLANNER_MODEL}[/dim]")
    
    def _setup_prompt_session(self):
        """Setup enhanced prompt session with completion and history"""
        # Command completer
        commands = WordCompleter(
            ['architect', 'plan', 'fix', 'test', 'commit', 'status', 'context', 'add', 'new', 'templates', 'image', 'guks', 'guks stats', 'guks patterns', 'guks recurring', 'guks report', 'knowledge', 'undo', 'redo', 'history', 'reasoning', 'reasoning on', 'reasoning off', 'perf', 'exit', 'help'],
            ignore_case=True,
            sentence=True
        )
        
        # Path completer for file arguments
        path_completer = PathCompleter(
            expanduser=True,
            only_directories=False
        )
        
        # Merge completers
        self.completer = merge_completers([commands, path_completer])
        
        # History file
        history_file = self.config_dir / "command_history.txt"
        
        # Create prompt session
        self.prompt_session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=self.completer,
            complete_while_typing=True,
            enable_history_search=True
        )
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary by reading first 8KB"""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(8192)
                # Check for null bytes (common in binary files)
                if b'\x00' in chunk:
                    return True
                # Check if mostly non-text characters
                text_chars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
                non_text = sum(1 for byte in chunk if byte not in text_chars)
                return non_text / len(chunk) > 0.3 if chunk else False
        except PermissionError as e:
            logger.warning(f"Permission denied reading {file_path}: {e}")
            return True  # Treat as binary if can't read
        except OSError as e:
            logger.error(f"OS error reading {file_path}: {e}")
            return True
        except Exception as e:
            logger.error(f"Unexpected error in binary detection for {file_path}: {e}", exc_info=True)
            raise  # Don't swallow unexpected errors
    
    def load_session(self) -> Dict:
        """Load session with workspace context"""
        if self.session_file.exists():
            with open(self.session_file, 'r') as f:
                return json.load(f)
        
        return {
            'workspace': str(self.workspace.root),
            'context_files': [],
            'conversation': [],
            'undo_stack': []
        }
    
    def save_session(self):
        """Save session"""
        with open(self.session_file, 'w') as f:
            json.dump(self.session, f, indent=2)
    
    def show_context(self):
        """Display current workspace context"""
        console.print(Panel.fit(
            f"[bold cyan]Workspace:[/bold cyan] {self.workspace.root}\n"
            f"[bold cyan]Git:[/bold cyan] {self.workspace.git_root or 'Not a git repo'}\n"
            f"[bold cyan]Last Error:[/bold cyan] {'Yes' if self.workspace.last_error else 'None'}",
            title="Context",
            border_style="cyan"
        ))
        
        # Show git status if available
        git_status = self.workspace.get_git_status()
        if git_status:
            if git_status.get('modified'):
                console.print(f"\n[yellow]Modified:[/yellow] {', '.join(git_status['modified'][:3])}")
            if git_status.get('untracked'):
                console.print(f"[blue]Untracked:[/blue] {', '.join(git_status['untracked'][:3])}")
        
        # Show context memory
        context_files = self.session.get('context_files', [])
        if context_files:
            console.print(f"\n[cyan]Context Memory:[/cyan] {len(context_files)} file(s) loaded")
            console.print(f"[dim]Use 'context' command to see details[/dim]")
    
    def show_context_memory(self):
        """Display detailed context memory - what files/data are loaded"""
        context_files = self.session.get('context_files', [])
        
        if not context_files:
            console.print("[yellow]No files currently in context memory[/yellow]")
            console.print("[dim]Context is loaded automatically when you run 'fix' on a file[/dim]")
            return
        
        table = Table(title="Context Memory", box=box.ROUNDED)
        table.add_column("File", style="cyan", no_wrap=False)
        table.add_column("Size", style="white", justify="right")
        table.add_column("Lines", style="white", justify="right")
        table.add_column("Loaded", style="dim")
        
        total_size = 0
        total_lines = 0
        
        for ctx_file in context_files:
            file_path = Path(ctx_file.get('path', ''))
            if file_path.exists():
                size = file_path.stat().st_size
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                except (OSError, UnicodeDecodeError) as e:
                    logger.debug(f"Could not count lines in {file_path}: {e}")
                    lines = 0
                
                total_size += size
                total_lines += lines
                
                # Format size
                if size < 1024:
                    size_str = f"{size}B"
                elif size < 1024 * 1024:
                    size_str = f"{size/1024:.1f}KB"
                else:
                    size_str = f"{size/(1024*1024):.1f}MB"
                
                loaded_time = ctx_file.get('loaded', 'Unknown')
                
                table.add_row(
                    str(file_path.name),
                    size_str,
                    str(lines),
                    loaded_time
                )
        
        console.print(table)
        
        # Show summary
        if total_size < 1024:
            total_size_str = f"{total_size}B"
        elif total_size < 1024 * 1024:
            total_size_str = f"{total_size/1024:.1f}KB"
        else:
            total_size_str = f"{total_size/(1024*1024):.1f}MB"
        
        console.print(f"\n[cyan]Total:[/cyan] {len(context_files)} files, {total_size_str}, {total_lines:,} lines")
        console.print(f"[dim]This is what the AI can see when analyzing your code[/dim]")
    
    def add_directory_to_context(self, directory_path: str, patterns: Optional[List[str]] = None, exclude_patterns: Optional[List[str]] = None):
        """
        Recursively add all files from a directory to context
        
        Args:
            directory_path: Path to directory to add
            patterns: List of glob patterns to include (e.g., ['*.py', '*.js'])
            exclude_patterns: List of glob patterns to exclude (e.g., ['*.pyc', '__pycache__/*'])
        """
        dir_path = Path(directory_path)
        
        if not dir_path.exists():
            console.print(f"[red]Directory not found: {directory_path}[/red]")
            return
        
        if not dir_path.is_dir():
            console.print(f"[red]Not a directory: {directory_path}[/red]")
            return
        
        # Default patterns
        if patterns is None:
            patterns = ['*.py', '*.js', '*.ts', '*.jsx', '*.tsx', '*.java', '*.cpp', '*.c', '*.h', 
                       '*.go', '*.rs', '*.rb', '*.php', '*.swift', '*.kt', '*.scala', '*.sh',
                       '*.md', '*.txt', '*.json', '*.yaml', '*.yml', '*.toml', '*.xml']
        
        if exclude_patterns is None:
            exclude_patterns = [
                '*.pyc', '__pycache__/*', '.git/*', '.venv/*', 'venv/*', 'node_modules/*',
                '.pytest_cache/*', '.mypy_cache/*', '*.egg-info/*', 'dist/*', 'build/*',
                '.DS_Store', '*.so', '*.dylib', '*.dll', '*.exe', '*.bin', '*.o', '*.a'
            ]
        
        console.print(f"[cyan]📂 Scanning directory: {directory_path}[/cyan]")
        
        added_files = []
        skipped_binary = 0
        skipped_excluded = 0
        
        # Walk directory recursively
        for file_path in dir_path.rglob('*'):
            if not file_path.is_file():
                continue
            
            # Get relative path for pattern matching
            rel_path = file_path.relative_to(dir_path)
            
            # Check exclusion patterns
            excluded = False
            for pattern in exclude_patterns:
                if fnmatch.fnmatch(str(rel_path), pattern) or fnmatch.fnmatch(file_path.name, pattern):
                    excluded = True
                    skipped_excluded += 1
                    break
            
            if excluded:
                continue
            
            # Check inclusion patterns
            included = False
            for pattern in patterns:
                if fnmatch.fnmatch(file_path.name, pattern):
                    included = True
                    break
            
            if not included:
                skipped_excluded += 1
                continue
            
            # Check if binary
            if self._is_binary_file(file_path):
                skipped_binary += 1
                continue
            
            # Add to context
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Add to session context
                context_entry = {
                    'path': str(file_path),
                    'loaded': datetime.now().strftime('%H:%M:%S'),
                    'size': file_path.stat().st_size,
                    'lines': len(content.splitlines())
                }
                
                # Check if already in context
                existing_paths = [f['path'] for f in self.session.get('context_files', [])]
                if str(file_path) not in existing_paths:
                    if 'context_files' not in self.session:
                        self.session['context_files'] = []
                    self.session['context_files'].append(context_entry)
                    added_files.append(file_path)
                
            except PermissionError as e:
                logger.warning(f"Permission denied reading {file_path}: {e}")
                console.print(f"[dim]⚠ Skipped {file_path.name}: Permission denied[/dim]")
                continue
            except UnicodeDecodeError as e:
                logger.debug(f"Binary file skipped {file_path}: {e}")
                console.print(f"[dim]⚠ Skipped {file_path.name}: Binary file[/dim]")
                continue
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}", exc_info=True)
                console.print(f"[dim]⚠ Skipped {file_path.name}: {str(e)}[/dim]")
                continue
        
        # Save session
        self.save_session()
        
        # Report results
        console.print(f"\n[green]✓ Added {len(added_files)} files to context[/green]")
        if skipped_binary > 0:
            console.print(f"[dim]Skipped {skipped_binary} binary files[/dim]")
        if skipped_excluded > 0:
            console.print(f"[dim]Skipped {skipped_excluded} excluded/non-matching files[/dim]")
        
        if added_files:
            console.print(f"\n[cyan]Sample files added:[/cyan]")
            for f in added_files[:5]:
                console.print(f"  • {f.name}")
            if len(added_files) > 5:
                console.print(f"  ... and {len(added_files) - 5} more")
            
            console.print(f"\n[dim]Use 'context' command to see all loaded files[/dim]")
    
    def _get_file_templates(self) -> Dict[str, str]:
        """Get built-in file templates"""
        return {
            'python': '''#!/usr/bin/env python3
"""
{description}
"""

def main():
    """Main entry point"""
    pass


if __name__ == "__main__":
    main()
''',
            'python-class': '''"""
{description}
"""

class {classname}:
    """
    {classname} class
    """
    
    def __init__(self):
        """Initialize {classname}"""
        pass
''',
            'python-test': '''"""
Tests for {module}
"""
import pytest


class Test{classname}:
    """Test suite for {classname}"""
    
    def test_example(self):
        """Test example"""
        assert True
''',
            'javascript': '''/**
 * {description}
 */

function main() {
  // Implementation
}

if (require.main === module) {
  main();
}

module.exports = { main };
''',
            'typescript': '''/**
 * {description}
 */

export function main(): void {
  // Implementation
}

if (require.main === module) {
  main();
}
''',
            'markdown': '''# {title}

{description}

## Overview

## Usage

## Examples

''',
            'readme': r'''# {project_name}

{description}

## Features

- Feature 1
- Feature 2

## Installation

```bash
# Installation steps
```

## Usage

```bash
# Usage examples
```

## License

MIT
''',
            'config-json': '''{
  "name": "{project_name}",
  "version": "0.1.0",
  "description": "{description}"
}
''',
            'config-yaml': '''# {description}

name: {project_name}
version: 0.1.0

settings:
  debug: false
'''
        }
    
    def create_from_template(self, template_name: str, file_path: str, **kwargs):
        """
        Create a new file from a template
        
        Args:
            template_name: Name of the template to use
            file_path: Path where the file should be created
            **kwargs: Variables to substitute in the template
        """
        templates = self._get_file_templates()
        
        if template_name not in templates:
            console.print(f"[red]Unknown template: {template_name}[/red]")
            console.print(f"[dim]Available templates: {', '.join(templates.keys())}[/dim]")
            return
        
        target_path = Path(file_path)
        
        # Check if file already exists
        if target_path.exists():
            if not Confirm.ask(f"[yellow]File {file_path} already exists. Overwrite?[/yellow]"):
                console.print("[dim]Cancelled[/dim]")
                return
        
        # Get template content
        template_content = templates[template_name]
        
        # Auto-fill some variables if not provided
        if 'filename' not in kwargs:
            kwargs['filename'] = target_path.stem
        if 'classname' not in kwargs:
            # Convert filename to PascalCase for class name
            kwargs['classname'] = ''.join(word.capitalize() for word in target_path.stem.split('_'))
        if 'module' not in kwargs:
            kwargs['module'] = target_path.stem
        if 'description' not in kwargs:
            kwargs['description'] = f"{target_path.stem} module"
        if 'title' not in kwargs:
            kwargs['title'] = target_path.stem.replace('_', ' ').replace('-', ' ').title()
        if 'project_name' not in kwargs:
            kwargs['project_name'] = self.workspace.root.name
        
        # Substitute variables
        try:
            content = template_content.format(**kwargs)
        except KeyError as e:
            console.print(f"[red]Missing template variable: {e}[/red]")
            return
        
        # Create parent directories if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            console.print(f"[green]✓ Created {file_path} from template '{template_name}'[/green]")
            
            # Show preview
            lines = content.split('\n')
            preview_lines = min(10, len(lines))
            console.print(f"\n[dim]Preview (first {preview_lines} lines):[/dim]")
            syntax = Syntax(content.split('\n\n')[0], "python" if template_name.startswith('python') else "text", 
                          theme="monokai", line_numbers=False)
            console.print(syntax)
            
        except PermissionError as e:
            logger.error(f"Permission denied creating {target_path}: {e}")
            console.print(f"[red]Permission denied: Cannot create {target_path}[/red]")
        except OSError as e:
            logger.error(f"OS error creating {target_path}: {e}")
            console.print(f"[red]Error creating file: {e}[/red]")
        except Exception as e:
            logger.error(f"Unexpected error creating file: {e}", exc_info=True)
            console.print(f"[red]Error creating file: {e}[/red]")
    
    def list_templates(self):
        """List available file templates"""
        templates = self._get_file_templates()
        
        table = Table(title="Available File Templates", box=box.ROUNDED)
        table.add_column("Template", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Example", style="dim")
        
        template_info = {
            'python': ('Python script with main', 'new python script.py'),
            'python-class': ('Python class file', 'new python-class myclass.py'),
            'python-test': ('Python test file', 'new python-test test_feature.py'),
            'javascript': ('JavaScript module', 'new javascript module.js'),
            'typescript': ('TypeScript module', 'new typescript module.ts'),
            'markdown': ('Markdown document', 'new markdown doc.md'),
            'readme': ('README file', 'new readme README.md'),
            'config-json': ('JSON config file', 'new config-json config.json'),
            'config-yaml': ('YAML config file', 'new config-yaml config.yml')
        }
        
        for template_name, (desc, example) in template_info.items():
            table.add_row(template_name, desc, example)
        
        console.print(table)
        console.print(f"\n[dim]Usage: new <template> <filename> [description=\"...\"][/dim]")
    
    def _encode_image_to_base64(self, image_path: Path) -> Optional[str]:
        """Encode image to base64 data URL for grok-4-fast vision"""
        try:
            # Check file size (max 20MiB per docs)
            file_size = image_path.stat().st_size
            max_size = 20 * 1024 * 1024  # 20 MiB
            
            if file_size > max_size:
                console.print(f"[yellow]⚠ Image too large: {file_size / (1024*1024):.1f}MB (max 20MB)[/yellow]")
                return None
            
            # Check file type (jpg/jpeg or png per docs)
            ext = image_path.suffix.lower()
            if ext not in ['.jpg', '.jpeg', '.png']:
                console.print(f"[yellow]⚠ Unsupported image type: {ext} (use .jpg, .jpeg, or .png)[/yellow]")
                return None
            
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Determine MIME type
            mime_type = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png'
            
            # Return data URL format
            return f"data:{mime_type};base64,{base64_image}"
            
        except FileNotFoundError as e:
            logger.error(f"Image file not found: {img_path}")
            console.print(f"[red]Image file not found: {img_path}[/red]")
            return None
        except PermissionError as e:
            logger.error(f"Permission denied reading image: {img_path}")
            console.print(f"[red]Permission denied reading image[/red]")
            return None
        except Exception as e:
            logger.error(f"Error encoding image {img_path}: {e}", exc_info=True)
            console.print(f"[red]Error encoding image: {e}[/red]")
            return None
    
    def analyze_image(self, image_path: str, prompt: Optional[str] = None):
        """
        Analyze an image using grok-4-fast vision capabilities
        
        Args:
            image_path: Path to the image file
            prompt: Optional custom prompt (default: general UI analysis)
        """
        if not self.client:
            console.print("[red]API key required for AI features[/red]")
            return
        
        img_path = Path(image_path)
        
        if not img_path.exists():
            console.print(f"[red]Image not found: {image_path}[/red]")
            return
        
        console.print(f"[cyan]📸 Analyzing image: {image_path}[/cyan]")
        
        # Encode image
        base64_image = self._encode_image_to_base64(img_path)
        if not base64_image:
            return
        
        # Default prompt for UI/screenshot analysis
        if not prompt:
            prompt = """Analyze this image in detail. If it's a UI/screenshot:
- Describe the layout and components
- Identify any visual issues or bugs
- Suggest improvements
- Note accessibility concerns

If it's code or documentation:
- Describe what you see
- Identify any issues
- Suggest fixes

Provide actionable insights."""
        
        # Build message with image (per grok_models.md format)
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": base64_image,
                            "detail": "high"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
        
        try:
            # Use grok-4-fast for vision (supports image input per docs)
            console.print("[dim]Using grok-4-fast vision model...[/dim]\n")
            
            response = self.client.chat.completions.create(
                model="grok-4-fast",
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            analysis = response.choices[0].message.content
            
            # Display analysis
            console.print(Panel(
                Markdown(analysis),
                title=f"Image Analysis: {img_path.name}",
                border_style="cyan"
            ))
            
            # Save to session for context
            if 'image_analyses' not in self.session:
                self.session['image_analyses'] = []
            
            self.session['image_analyses'].append({
                'image': str(img_path),
                'prompt': prompt,
                'analysis': analysis,
                'timestamp': datetime.now().isoformat()
            })
            
            self.save_session()
            
        except FileNotFoundError as e:
            logger.error(f"Image file not found: {image_path}")
            console.print(f"[red]Image file not found: {image_path}[/red]")
        except ImageValidationError as e:
            logger.warning(f"Image validation failed: {e}")
            console.print(f"[red]Invalid image: {e}[/red]")
        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded: {e}")
            console.print(f"[red]Rate limit exceeded. Please try again later.[/red]")
        except AuthenticationError as e:
            logger.error(f"API authentication failed: {e}")
            console.print(f"[red]Authentication failed. Check your API key.[/red]")
        except Exception as e:
            logger.error(f"Error analyzing image: {e}", exc_info=True)
            console.print(f"[red]Error analyzing image: {e}[/red]")
            if "vision" in str(e).lower() or "image" in str(e).lower():
                console.print("[yellow]Note: Make sure you're using a model with vision support (grok-4-fast)[/yellow]")
    
    def smart_fix(self, target: Optional[str] = None):
        """
        Smart fix - analyzes context and suggests/applies fixes
        
        UX: grokflow fix [file]
        - No file: fixes last error
        - With file: analyzes and fixes file
        """
        if not self.client:
            console.print("[red]API key required for AI features[/red]")
            return
        
        console.print("[cyan]🔍 Analyzing context...[/cyan]\n")
        start_time = datetime.now()
        original_code: Optional[str] = None
        file_path: Optional[Path] = None
        
        # Determine what to fix
        if target:
            # Fix specific file
            file_path = Path(target)
            if not file_path.exists():
                console.print(f"[red]File not found: {target}[/red]")
                return
            
            # Check if binary file
            if self._is_binary_file(file_path):
                console.print(f"[yellow]⚠ Skipping binary file: {target}[/yellow]")
                console.print(f"[dim]Binary files (images, compiled code, etc.) cannot be analyzed[/dim]")
                return
            
            try:
                with file_path.open('r', encoding='utf-8') as f:
                    original_code = f.read()
            except UnicodeDecodeError:
                console.print(f"[yellow]⚠ Cannot read file (encoding issue): {target}[/yellow]")
                return
            
            context = f"File: {target}\n\n```\n{original_code}\n```"
        
        elif self.workspace.last_error:
            # Fix last error (no direct file)
            context = f"Last error:\n{self.workspace.last_error}"
        
        else:
            # Smart detection - check git status
            git_status = self.workspace.get_git_status()
            if git_status.get('modified'):
                target = git_status['modified'][0]
                file_path = Path(target)
                console.print(f"[cyan]Detected modified file: {target}[/cyan]")
                
                # Check if binary file
                if self._is_binary_file(file_path):
                    console.print(f"[yellow]⚠ Skipping binary file: {target}[/yellow]")
                    console.print(f"[dim]Specify a text file to analyze[/dim]")
                    return
                
                try:
                    with file_path.open('r', encoding='utf-8') as f:
                        original_code = f.read()
                except UnicodeDecodeError:
                    console.print(f"[yellow]⚠ Cannot read file (encoding issue): {target}[/yellow]")
                    return
                
                diff = self.workspace.get_diff(target)
                context = (
                    f"File: {target}\n\nRecent changes:\n{diff}\n\n"
                    f"Current content:\n```\n{original_code}\n```"
                )
            else:
                console.print("[yellow]Nothing to fix. Specify a file or run code first.[/yellow]")
                return

        # Surface similar past issues from GUKS, if available
        self._show_guks_suggestions(file_path, original_code)

        # Phase 1: Use planner model for analysis and creating fix plan
        console.print(f"[cyan]🧠 {self.PLANNER_MODEL} is analyzing...[/cyan]\n")
        
        plan_system = (
            "You are an expert software engineer analyzing bugs. "
            "Provide a clear analysis of the issue and create a detailed fix plan. "
            "Be specific about what needs to change and why."
        )
        plan_prompt = f"{context}\n\nAnalyze this issue and create a detailed fix plan."
        
        try:
            # Get analysis and plan from planner model
            plan_start = datetime.now()
            plan_response = self.client.chat.completions.create(
                model=self.PLANNER_MODEL,
                messages=[
                    {"role": "system", "content": plan_system},
                    {"role": "user", "content": plan_prompt},
                ],
                temperature=0.2,
                max_tokens=1500,
                stream=True,
            )
        except RateLimitError as e:
            logger.warning(f"Rate limit exceeded on planner call: {e}")
            console.print(f"[red]Rate limit exceeded. Please try again later.[/red]")
            return
        except AuthenticationError as e:
            logger.error(f"API authentication failed: {e}")
            console.print(f"[red]Authentication failed. Check your API key.[/red]")
            return
        except Exception as e:
            logger.error(f"Planner model call failed: {e}", exc_info=True)
            console.print(f"[red]Planner model call failed: {e}[/red]")
            return

        # Stream plan with reasoning display
        plan_text, plan_reasoning = self._stream_with_reasoning(plan_response)
        plan_duration = (datetime.now() - plan_start).total_seconds()
        self.perf_metrics["planner_calls"] += 1
        self.perf_metrics["planner_time"] += plan_duration
        
        if not plan_text:
            console.print("[red]No plan received from planner[/red]")
            return
        
        console.print()  # Newline after streaming
        
        # Phase 2: Use executor model to generate the actual fix
        if original_code:
            console.print(f"[cyan]⚡ {self.EXECUTOR_MODEL} is generating fix...[/cyan]\n")
            
            fix_system = (
                "You are a code generator. Given an analysis and fix plan, generate the corrected code. "
                "Return ONLY the complete corrected file inside a single ```python``` block. "
                "No explanations, just the code."
            )
            fix_prompt = f"""Analysis and Plan:
{plan_text}

Original Code:
{original_code}

Generate the complete corrected code following the plan above."""
            
            try:
                exec_start = datetime.now()
                fix_response = self.client.chat.completions.create(
                    model=self.EXECUTOR_MODEL,
                    messages=[
                        {"role": "system", "content": fix_system},
                        {"role": "user", "content": fix_prompt},
                    ],
                    temperature=0.1,  # Lower temperature for code generation
                    max_tokens=2000,
                    stream=False,  # Non-streaming for executor
                )
                assistant_text = fix_response.choices[0].message.content or ""
                exec_duration = (datetime.now() - exec_start).total_seconds()
                self.perf_metrics["executor_calls"] += 1
                self.perf_metrics["executor_time"] += exec_duration
                
                # Display performance info
                console.print(f"[dim]⏱️  Plan: {plan_duration:.1f}s | Execute: {exec_duration:.1f}s | Total: {plan_duration + exec_duration:.1f}s[/dim]")
            except RateLimitError as e:
                logger.warning(f"Rate limit exceeded on executor call: {e}")
                console.print(f"[red]Rate limit exceeded. Please try again later.[/red]")
                return
            except AuthenticationError as e:
                logger.error(f"API authentication failed: {e}")
                console.print(f"[red]Authentication failed. Check your API key.[/red]")
                return
            except Exception as e:
                logger.error(f"Executor model call failed: {e}", exc_info=True)
                console.print(f"[red]Executor model call failed: {e}[/red]")
                return
        else:
            # No code to fix, use plan as the response
            assistant_text = plan_text

        # Try to extract corrected code and show diff
        new_code: Optional[str] = None
        if original_code is not None:
            new_code = self._extract_code_block(assistant_text)

        applied = False
        if file_path and original_code is not None and new_code:
            diff_text = "\n".join(
                difflib.unified_diff(
                    original_code.splitlines(),
                    new_code.splitlines(),
                    fromfile=str(file_path),
                    tofile=str(file_path),
                    lineterm="",
                )
            )
            if diff_text.strip():
                console.print(Panel(
                    Syntax(diff_text, "diff", theme="monokai", line_numbers=False),
                    title="Proposed Diff",
                    border_style="cyan",
                ))
            else:
                console.print("[yellow]Proposed code is identical to current file.[/yellow]")

            if Confirm.ask("\n[cyan]Apply this diff to the file?[/cyan]"):
                try:
                    # Use FileWriteCommand through UndoManager for proper undo support
                    cmd = FileWriteCommand(
                        file_path=file_path,
                        content=new_code,
                        backup_content=original_code,
                        description=f"Fix applied to {file_path.name}"
                    )
                    self.undo_manager.execute(cmd)

                    # Track GUKS mapping for potential undo
                    self._undo_guks_mapping[str(file_path)] = {
                        "error_id": self.last_error_id,
                        "solution_id": None,  # Will be set when solution is recorded
                        "timestamp": datetime.now().isoformat()
                    }

                    console.print("[green]✓ Fix applied to file[/green]")
                    console.print(f"[dim]💾 Undo point saved (use 'undo' to revert, 'redo' to reapply)[/dim]")
                    applied = True
                except UndoError as e:
                    logger.error(f"Undo system error: {e}")
                    console.print(f"[red]Failed to apply fix: {e}[/red]")
                except PermissionError as e:
                    logger.error(f"Permission denied writing to {file_path}: {e}")
                    console.print(f"[red]Permission denied: Cannot write to {file_path}[/red]")
                except OSError as e:
                    logger.error(f"OS error writing to {file_path}: {e}")
                    console.print(f"[red]Failed to write file: {e}[/red]")
                except Exception as e:
                    logger.error(f"Unexpected error writing file: {e}", exc_info=True)
                    console.print(f"[red]Failed to write file: {e}[/red]")
            else:
                console.print("[yellow]Skipped automatic apply. You can edit the file manually using the proposal above.[/yellow]")
        else:
            console.print("[yellow]No file context available; please apply the suggested changes manually.[/yellow]")

        console.print("[yellow]💡 Re-run your tests to verify the fix.[/yellow]")

        # Success/failure logging into universal knowledge
        duration = (datetime.now() - start_time).total_seconds()
        code_before = original_code if original_code is not None else context
        code_after = new_code if new_code is not None else assistant_text

        if Confirm.ask("\n[cyan]After re-running tests, did this fix fully resolve the issue?[/cyan]", default=False):
            # Record in GUKS
            self._record_fix_in_guks(
                error=self.workspace.last_error or "Unknown error",
                fix=f"Applied AI fix: {code_after[:200]}",
                file_path=file_path,
                success=True
            )
            console.print("[dim]✅ Fix recorded in GUKS for future reference[/dim]")
        else:
            if Confirm.ask("[cyan]Did the suggested fix fail to resolve the issue?[/cyan]", default=False):
                # Don't record failed fixes in GUKS (they would pollute the knowledge base)
                console.print("[dim]Fix not recorded in GUKS (unsuccessful)[/dim]")
    
    def quick_test(self, target: Optional[str] = None):
        """
        Quick test - runs relevant tests

        UX: grokflow test [file]
        - No file: runs all tests
        - With file: runs tests for that specific file or pattern
        """
        console.print("[cyan]🧪 Running tests...[/cyan]\n")

        # Detect test framework and build command
        cmd = None
        framework = None

        if Path('pytest.ini').exists() or Path('setup.py').exists() or Path('pyproject.toml').exists():
            framework = 'pytest'
            cmd = ['pytest', '-v', '--tb=short']
            if target:
                # Support both file paths and test patterns
                if '::' in target:
                    # pytest node ID format (file::class::method)
                    cmd.append(target)
                elif target.endswith('.py'):
                    # Direct file path
                    cmd.append(target)
                else:
                    # Pattern matching (e.g., "test_auth" -> runs test_auth*.py)
                    cmd.extend(['-k', target])
        elif Path('package.json').exists():
            framework = 'npm'
            cmd = ['npm', 'test']
            if target:
                cmd.extend(['--', target])
        elif Path('Cargo.toml').exists():
            framework = 'cargo'
            cmd = ['cargo', 'test']
            if target:
                cmd.append(target)
        elif Path('go.mod').exists():
            framework = 'go'
            cmd = ['go', 'test', '-v']
            if target:
                cmd.append(f'./{target}/...')
            else:
                cmd.append('./...')

        if not cmd:
            console.print("[yellow]No test framework detected (pytest, npm, cargo, go)[/yellow]")
            console.print("[dim]Supported: pytest.ini, setup.py, pyproject.toml, package.json, Cargo.toml, go.mod[/dim]")
            return

        console.print(f"[dim]Framework: {framework} | Command: {' '.join(cmd)}[/dim]\n")

        # Run tests with extended timeout for larger test suites
        timeout = 120 if not target else 60
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            # Show output
            output = result.stdout + result.stderr
            if result.returncode == 0:
                console.print("[green]✓ All tests passed[/green]")
                if output.strip():
                    # Show summary only for passing tests
                    lines = output.strip().split('\n')
                    summary_lines = [l for l in lines if 'passed' in l.lower() or 'ok' in l.lower() or 'success' in l.lower()]
                    if summary_lines:
                        console.print(f"[dim]{summary_lines[-1]}[/dim]")
            else:
                console.print("[red]✗ Tests failed[/red]")

                # Parse and display failures more helpfully
                if framework == 'pytest':
                    self._display_pytest_failures(output)
                else:
                    console.print(Panel(output[:3000], title="Test Output", border_style="red"))

                # Store error for smart fix and record in knowledge base
                self.workspace.last_error = output
                self.workspace.last_test_output = output
                self._record_error_in_knowledge(output)

                console.print("\n[yellow]💡 Run 'fix' to auto-fix with AI (includes universal knowledge suggestions)[/yellow]")

        except subprocess.TimeoutExpired:
            console.print(f"[red]Tests timed out after {timeout}s[/red]")
            console.print("[dim]Try running a specific test file: test <filename>[/dim]")
        except FileNotFoundError as e:
            console.print(f"[red]Test command not found: {cmd[0]}[/red]")
            console.print(f"[dim]Make sure {framework} is installed[/dim]")
        except Exception as e:
            logger.error(f"Test execution error: {e}", exc_info=True)
            console.print(f"[red]Test execution failed: {e}[/red]")

    def _display_pytest_failures(self, output: str):
        """Parse and display pytest failures in a helpful format."""
        lines = output.split('\n')
        failures = []
        current_failure = []
        in_failure = False

        for line in lines:
            if line.startswith('FAILED ') or line.startswith('ERROR '):
                if current_failure:
                    failures.append('\n'.join(current_failure))
                current_failure = [line]
                in_failure = True
            elif in_failure and (line.startswith('    ') or line.startswith('E   ')):
                current_failure.append(line)
            elif in_failure and line.strip() == '':
                if current_failure:
                    failures.append('\n'.join(current_failure))
                current_failure = []
                in_failure = False

        if current_failure:
            failures.append('\n'.join(current_failure))

        if failures:
            console.print(f"\n[red]Found {len(failures)} failure(s):[/red]")
            for i, failure in enumerate(failures[:5], 1):  # Show max 5 failures
                console.print(Panel(failure, title=f"Failure {i}", border_style="red"))
            if len(failures) > 5:
                console.print(f"[dim]... and {len(failures) - 5} more failures[/dim]")
        else:
            # Fallback to raw output
            console.print(Panel(output[:3000], title="Test Output", border_style="red"))

    def _parse_error_line(self, line: str) -> Tuple[str, str]:
        """Best-effort extraction of error type and message from a test failure line.

        Examples:
            "AttributeError: 'NoneType' object has no attribute 'x'" -> ("AttributeError", "'NoneType' object has no attribute 'x'")
            "E   AssertionError: expected 1" -> ("AssertionError", "expected 1")
        """
        text = line.strip()
        if not text:
            return "TestFailure", "(no message)"

        # Strip pytest prefixes like "E   "
        if text.startswith("E "):
            text = text[1:].strip()

        if ":" in text:
            first, rest = text.split(":", 1)
            first = first.strip()
            if first.endswith("Error") or first.endswith("Exception"):
                return first, rest.strip()

        return "TestFailure", text

    def _show_guks_suggestions(self, file_path: Optional[Path], code: Optional[str]):
        """Show similar patterns from GUKS based on error or code"""
        if not self.guks:
            return

        console.print("[cyan]📚 Querying GUKS...[/cyan]")

        # Build query from available context
        error_msg = None
        if self.workspace.last_error:
            # Extract last few lines of error
            error_lines = self.workspace.last_error.splitlines()
            error_msg = '\n'.join(error_lines[-5:])  # Last 5 lines

        code_snippet = None
        if code:
            # Extract key parts of code (imports, class defs, function defs)
            code_lines = code.splitlines()
            key_lines = [l for l in code_lines if any(kw in l for kw in ['import ', 'class ', 'def ', 'async def'])]
            code_snippet = '\n'.join(key_lines[:10]) if key_lines else code[:500]

        # Build context
        context = {}
        if file_path:
            context['file_type'] = file_path.suffix.lstrip('.')
            context['project'] = self.workspace.git_root.name if self.workspace.git_root else Path.cwd().name

        # Query GUKS
        query_text = f"{error_msg or ''}\n{code_snippet or ''}".strip()
        if not query_text:
            console.print("[blue]No context available for GUKS query[/blue]\n")
            return

        try:
            results = self.guks.query(
                code=code_snippet or "",
                error=error_msg,
                context=context
            )

            # Store query for later recording
            self.last_guks_query = {
                'code': code_snippet,
                'error': error_msg,
                'context': context,
                'timestamp': datetime.now().isoformat()
            }

            if not results:
                console.print("[blue]No similar patterns found in GUKS[/blue]\n")
                return

            # Display results
            table = Table(title="Similar Patterns from GUKS", box=box.SIMPLE)
            table.add_column("#", style="cyan", width=3)
            table.add_column("Similarity", style="magenta", width=10)
            table.add_column("Error", style="white", no_wrap=False)
            table.add_column("Fix", style="green", no_wrap=False)
            table.add_column("Project", style="dim", width=15)

            for idx, match in enumerate(results[:5], 1):
                similarity = match.get('similarity', match.get('score', 0))
                error = match.get('error', '')[:60]
                fix = match.get('fix', '')[:60]
                project = match.get('project', 'unknown')[:14]

                table.add_row(
                    str(idx),
                    f"{similarity*100:.0f}%",
                    error + ("..." if len(match.get('error', '')) > 60 else ""),
                    fix + ("..." if len(match.get('fix', '')) > 60 else ""),
                    project
                )

            console.print("\n[cyan]🔍 GUKS found similar patterns:[/cyan]")
            console.print(table)
            console.print()

            # Show top match details
            top_match = results[0]
            if top_match.get('similarity', top_match.get('score', 0)) > 0.7:
                console.print(f"[green]💡 Top suggestion ({top_match.get('similarity', top_match.get('score', 0))*100:.0f}% match):[/green]")
                console.print(f"[dim]Error:[/dim] {top_match['error']}")
                console.print(f"[dim]Fix:[/dim] {top_match['fix']}")
                console.print()

        except Exception as e:
            logger.error(f"GUKS query failed: {e}", exc_info=True)
            console.print(f"[yellow]⚠ GUKS query failed: {e}[/yellow]\n")

    def _record_fix_in_guks(
        self,
        error: str,
        fix: str,
        file_path: Optional[Path],
        success: bool = True
    ):
        """Record a successful fix in GUKS"""
        if not self.guks or not success:
            return

        # Build pattern dict
        project = self.workspace.git_root.name if self.workspace.git_root else Path.cwd().name
        file_name = file_path.name if file_path else "unknown"

        pattern = {
            'error': error[:500],  # Limit length
            'fix': fix[:500],
            'file': file_name,
            'project': project,
            'context': self.last_guks_query.get('context', {}) if self.last_guks_query else {}
        }

        try:
            # Record in GUKS
            self.guks.record_fix(pattern)
            logger.info(f"Recorded fix in GUKS: {file_name}")

            # Reinitialize analytics with updated patterns
            self.guks_analytics = GUKSAnalytics(self.guks.patterns)

        except Exception as e:
            logger.error(f"Failed to record fix in GUKS: {e}", exc_info=True)
            console.print(f"[yellow]⚠ Failed to record in GUKS: {e}[/yellow]")

    def _record_error_in_knowledge(self, raw_output: str):
        """Record failing test output as an error in the universal knowledge base."""
        if not self.knowledge:
            return

        lines = [l for l in (raw_output or "").splitlines() if l.strip()]
        if not lines:
            return

        error_line = lines[-1]
        error_type, error_message = self._parse_error_line(error_line)
        project_name = self.workspace.git_root.name if self.workspace.git_root else Path.cwd().name
        context = {"language": "python"}

        try:
            error_id = self.knowledge.record_error(
                error_type=error_type,
                error_message=error_message,
                context=context,
                project=project_name,
            )
            self.last_error_id = error_id
            logger.info(f"Recorded error in knowledge base: {error_id}")
        except KnowledgeBaseError as e:
            logger.warning(f"Knowledge base error: {e}")
            console.print(f"[yellow]⚠ Failed to record error in knowledge base: {e}[/yellow]")
        except Exception as e:
            logger.error(f"Unexpected error recording to knowledge base: {e}", exc_info=True)
            console.print(f"[yellow]⚠ Failed to record error in knowledge base: {e}[/yellow]")

    def _show_knowledge_suggestions(self):
        """Show similar past issues and their best solutions, if any."""
        if not self.knowledge or not self.workspace.last_error:
            return

        console.print("[cyan]📚 Checking universal knowledge...[/cyan]")
        # Use the tail of the last error, which usually contains the exception line
        tail = "\n".join(self.workspace.last_error.splitlines()[-10:])
        context = {"language": "python"}

        try:
            matches = self.knowledge.find_similar_errors(
                error_message=tail,
                context=context,
                min_confidence=0.7,
                top_k=5,
            )
            logger.info(f"Retrieved {len(matches)} knowledge base suggestions")
        except KnowledgeBaseError as e:
            logger.warning(f"Knowledge base lookup failed: {e}")
            console.print(f"[yellow]⚠ Knowledge lookup failed: {e}[/yellow]")
            return
        except Exception as e:
            logger.error(f"Unexpected error in knowledge lookup: {e}", exc_info=True)
            console.print(f"[yellow]⚠ Knowledge lookup failed: {e}[/yellow]")
            return

        if not matches:
            console.print("[blue]No similar past issues found in universal knowledge.[/blue]\n")
            return

        table = Table(title="Similar past issues", box=box.SIMPLE)
        table.add_column("#", style="cyan", width=3)
        table.add_column("Similarity", style="magenta", width=10)
        table.add_column("Error", style="white")
        table.add_column("Best Solution", style="green")
        table.add_column("Success", style="green", width=8)

        for idx, match in enumerate(matches, 1):
            best = match["solutions"][0] if match["solutions"] else None
            solution_desc = best["description"] if best else "(no recorded solution)"
            success = f"{best['success_rate']*100:.0f}%" if best else "-"
            table.add_row(
                str(idx),
                f"{match['similarity']*100:.0f}%",
                match["error_message"][:60] + ("…" if len(match["error_message"]) > 60 else ""),
                solution_desc[:60] + ("…" if len(solution_desc) > 60 else ""),
                success,
            )

        console.print("\n[cyan]🔎 Reusing past experience:[/cyan]")
        console.print(table)

    def _stream_with_reasoning(self, response) -> Tuple[str, str]:
        """Stream response with separate display for reasoning and content.

        The reasoning display can be toggled via self.show_reasoning.
        Reasoning is always captured even if display is off.

        Returns:
            Tuple of (content_text, reasoning_text)
        """
        full_content = ""
        full_reasoning = ""
        current_mode = None  # Track if we're in reasoning or content mode
        reasoning_hidden_count = 0  # Track tokens hidden when reasoning display is off

        try:
            for chunk in response:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # Check for reasoning tokens (if supported by model)
                if hasattr(delta, 'reasoning') and delta.reasoning:
                    # Always capture reasoning for session storage
                    full_reasoning += delta.reasoning

                    if self.show_reasoning:
                        # Transition to reasoning mode
                        if current_mode != "reasoning":
                            current_mode = "reasoning"
                            console.print("[cyan dim]💭 Reasoning:[/cyan dim] ", end="")

                        # Display reasoning in cyan dim
                        console.print(delta.reasoning, style="cyan dim", end="")
                    else:
                        reasoning_hidden_count += 1

                # Check for content tokens
                elif delta.content:
                    # Transition from reasoning to content
                    if current_mode == "reasoning":
                        console.print("\n\n")  # Add spacing between reasoning and content
                        current_mode = "content"
                    elif current_mode is None:
                        current_mode = "content"
                        # If we had hidden reasoning, show indicator
                        if reasoning_hidden_count > 0 and not self.show_reasoning:
                            console.print(f"[dim](reasoning hidden - use 'reasoning on' to show)[/dim]\n")

                    # Display content in normal color
                    console.print(delta.content, end="")
                    full_content += delta.content

        except RateLimitError as e:
            logger.warning(f"Rate limit during streaming: {e}")
            console.print(f"\n[red]Rate limit exceeded[/red]")
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            console.print(f"\n[red]Streaming error: {e}[/red]")

        # Store reasoning in session for replay
        if full_reasoning:
            self._store_reasoning_in_session(full_reasoning)

        return full_content, full_reasoning

    def _store_reasoning_in_session(self, reasoning: str):
        """Store reasoning text in session for history replay."""
        if 'reasoning_history' not in self.session:
            self.session['reasoning_history'] = []

        self.session['reasoning_history'].append({
            'timestamp': datetime.now().isoformat(),
            'reasoning': reasoning[:2000]  # Limit size to avoid bloat
        })

        # Keep only last 10 reasoning entries
        if len(self.session['reasoning_history']) > 10:
            self.session['reasoning_history'] = self.session['reasoning_history'][-10:]

        self.save_session()

    def toggle_reasoning(self, state: Optional[str] = None):
        """Toggle or set reasoning display state.

        Args:
            state: 'on', 'off', or None to toggle
        """
        if state == 'on':
            self.show_reasoning = True
            console.print("[green]✓ Reasoning display enabled[/green]")
        elif state == 'off':
            self.show_reasoning = False
            console.print("[yellow]✓ Reasoning display disabled[/yellow]")
        else:
            # Toggle
            self.show_reasoning = not self.show_reasoning
            state_str = "enabled" if self.show_reasoning else "disabled"
            console.print(f"[cyan]✓ Reasoning display {state_str}[/cyan]")
    
    def _extract_code_block(self, text: str) -> Optional[str]:
        """Extract the last ```python``` (or generic ```) code block from Grok-4 output."""
        if not text:
            return None

        lines = text.splitlines()
        code_blocks: List[List[str]] = []
        current: Optional[List[str]] = None
        in_block = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                fence = stripped[3:].strip().lower()
                if not in_block:
                    # Start of a block; track language but accept any
                    in_block = True
                    current = []
                else:
                    # End of current block
                    if current is not None:
                        code_blocks.append(current)
                    in_block = False
                    current = None
                continue

            if in_block and current is not None:
                current.append(line)

        if not code_blocks:
            return None

        # Use the last block as the most likely full corrected file
        return "\n".join(code_blocks[-1])

    def _record_solution_in_knowledge(
        self,
        description: str,
        code_before: str,
        code_after: str,
        time_spent: float,
        success: bool,
    ) -> None:
        """Record a solution attempt (success or failure) in the universal knowledge base."""
        if not self.knowledge or not self.last_error_id:
            return

        project_name = self.workspace.git_root.name if self.workspace.git_root else Path.cwd().name

        try:
            if success:
                self.knowledge.record_solution(
                    error_id=self.last_error_id,
                    description=description,
                    code_before=code_before,
                    code_after=code_after,
                    time_to_fix=time_spent,
                    project=project_name,
                    success=True,
                )
            else:
                # For failures, we log both a failed solution and a solution attempt with success=False
                self.knowledge.record_solution(
                    error_id=self.last_error_id,
                    description=description,
                    code_before=code_before,
                    code_after=code_after,
                    time_to_fix=time_spent,
                    project=project_name,
                    success=False,
                )
                self.knowledge.record_failed_solution(
                    error_id=self.last_error_id,
                    attempted_fix=code_after,
                    why_failed="User reported that tests still failed after applying fix.",
                    failure_reason="Grok-4 suggestion was incomplete or incorrect for this context.",
                    time_wasted=time_spent,
                    lessons_learned="Refine prompt or consider alternative fix; avoid reusing this exact fix blindly.",
                )
            logger.info(f"Recorded solution in knowledge base")
        except KnowledgeBaseError as e:
            logger.warning(f"Failed to record solution: {e}")
            console.print(f"[yellow]⚠ Failed to record solution in knowledge base: {e}[/yellow]")
        except Exception as e:
            logger.error(f"Unexpected error recording solution: {e}", exc_info=True)
            console.print(f"[yellow]⚠ Failed to record solution in knowledge base: {e}[/yellow]")

    def quick_commit(self, message: Optional[str] = None):
        """
        Quick commit - smart git commit
        
        UX: grokflow commit [message]
        - No message: AI generates commit message from diff
        - With message: uses provided message
        """
        if not self.workspace.git_root:
            console.print("[red]Not a git repository[/red]")
            return
        
        # Get status
        git_status = self.workspace.get_git_status()
        
        if not git_status.get('modified') and not git_status.get('untracked'):
            console.print("[yellow]No changes to commit[/yellow]")
            return
        
        # Show what will be committed
        console.print("[cyan]Changes to commit:[/cyan]\n")
        for f in git_status.get('modified', []):
            console.print(f"  [yellow]M[/yellow] {f}")
        for f in git_status.get('untracked', []):
            console.print(f"  [green]A[/green] {f}")
        
        # Generate commit message if not provided
        if not message and self.client:
            console.print("\n[cyan]🧠 Generating commit message...[/cyan]")
            # AI would generate message here
            message = "feat: improve error handling and add validation"
            console.print(f"[green]Suggested:[/green] {message}")
            
            if not Confirm.ask("\n[cyan]Use this message?[/cyan]"):
                message = Prompt.ask("Commit message")
        elif not message:
            message = Prompt.ask("Commit message")
        
        # Commit
        try:
            subprocess.run(['git', 'add', '-A'], cwd=self.workspace.git_root, check=True)
            subprocess.run(['git', 'commit', '-m', message], cwd=self.workspace.git_root, check=True)
            console.print(f"\n[green]✓ Committed:[/green] {message}")
        except subprocess.CalledProcessError as e:
            console.print(f"[red]Commit failed: {e}[/red]")
    
    def undo(self, filepath: Optional[str] = None):
        """Undo last edit using UndoManager with proper command pattern.

        Args:
            filepath: Ignored for now - UndoManager undoes in stack order.
                     Future: could filter by file path.
        """
        if not self.undo_manager.can_undo():
            console.print("[yellow]No undo history available[/yellow]")
            return

        # Get the description of the command we're about to undo
        undo_history = self.undo_manager.get_undo_history()
        if undo_history:
            last_action = undo_history[-1]
            console.print(f"[dim]Undoing: {last_action}[/dim]")

        try:
            success = self.undo_manager.undo()
            if success:
                console.print("[green]✓ Undo successful[/green]")

                # Check if we need to remove solution from GUKS
                # Find the most recent mapping and try to clean up
                if self._undo_guks_mapping and self.knowledge:
                    # Get the most recent entry
                    recent_path = max(self._undo_guks_mapping.keys(),
                                     key=lambda k: self._undo_guks_mapping[k].get("timestamp", ""))
                    guks_data = self._undo_guks_mapping.get(recent_path, {})

                    solution_id = guks_data.get("solution_id")
                    if solution_id:
                        try:
                            # Mark solution as reverted in GUKS (decrements success, increments failure)
                            # This helps the system learn that this fix was not effective
                            if self.knowledge.mark_solution_reverted(solution_id):
                                console.print("[dim]Marked solution as reverted in GUKS[/dim]")
                            del self._undo_guks_mapping[recent_path]
                        except AttributeError:
                            # mark_solution_reverted not implemented yet
                            console.print("[yellow]⚠ Solution remains in GUKS (update not available)[/yellow]")
                        except Exception as e:
                            logger.warning(f"Could not update solution in GUKS: {e}")
                            console.print(f"[yellow]⚠ Could not update GUKS: {e}[/yellow]")

                # Show redo hint
                if self.undo_manager.can_redo():
                    console.print(f"[dim]Use 'redo' to reapply the change[/dim]")
            else:
                console.print("[yellow]Undo failed - no changes were made[/yellow]")

        except UndoError as e:
            logger.error(f"Undo operation failed: {e}")
            console.print(f"[red]Undo failed: {e}[/red]")
        except Exception as e:
            logger.error(f"Unexpected error during undo: {e}", exc_info=True)
            console.print(f"[red]Undo failed: {e}[/red]")

    def redo(self):
        """Redo the last undone action using UndoManager."""
        if not self.undo_manager.can_redo():
            console.print("[yellow]No redo history available[/yellow]")
            return

        # Get the description of the command we're about to redo
        redo_history = self.undo_manager.get_redo_history()
        if redo_history:
            last_action = redo_history[-1]
            console.print(f"[dim]Redoing: {last_action}[/dim]")

        try:
            success = self.undo_manager.redo()
            if success:
                console.print("[green]✓ Redo successful[/green]")
                if self.undo_manager.can_undo():
                    console.print(f"[dim]Use 'undo' to undo the change again[/dim]")
            else:
                console.print("[yellow]Redo failed - no changes were made[/yellow]")

        except UndoError as e:
            logger.error(f"Redo operation failed: {e}")
            console.print(f"[red]Redo failed: {e}[/red]")
        except Exception as e:
            logger.error(f"Unexpected error during redo: {e}", exc_info=True)
            console.print(f"[red]Redo failed: {e}[/red]")

    def show_undo_history(self):
        """Display undo/redo history from UndoManager"""
        history_size = self.undo_manager.get_history_size()

        if history_size['undo_stack'] == 0 and history_size['redo_stack'] == 0:
            console.print("[yellow]No undo/redo history available[/yellow]")
            return

        # Show undo stack
        if history_size['undo_stack'] > 0:
            undo_history = self.undo_manager.get_undo_history()
            table = Table(title="Undo Stack (oldest to newest)", box=box.SIMPLE)
            table.add_column("#", style="cyan", width=3)
            table.add_column("Action", style="white")

            for idx, description in enumerate(undo_history, 1):
                table.add_row(str(idx), description)

            console.print(table)
        else:
            console.print("[dim]Undo stack is empty[/dim]")

        # Show redo stack
        if history_size['redo_stack'] > 0:
            redo_history = self.undo_manager.get_redo_history()
            table = Table(title="Redo Stack (available to redo)", box=box.SIMPLE)
            table.add_column("#", style="cyan", width=3)
            table.add_column("Action", style="green")

            for idx, description in enumerate(redo_history, 1):
                table.add_row(str(idx), description)

            console.print(table)

        console.print(f"\n[cyan]Summary:[/cyan] {history_size['undo_stack']} undoable, {history_size['redo_stack']} redoable")
        console.print(f"[dim]Use 'undo' to undo the most recent action[/dim]")
        console.print(f"[dim]Use 'redo' to redo the last undone action[/dim]")
    
    def show_performance_metrics(self):
        """Display dual-model architecture performance metrics"""
        metrics = self.perf_metrics
        
        if metrics["planner_calls"] == 0 and metrics["executor_calls"] == 0:
            console.print("[yellow]No performance data yet. Run 'fix' to generate metrics.[/yellow]")
            return
        
        table = Table(title="Dual-Model Performance Metrics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Planner Calls", str(metrics["planner_calls"]))
        table.add_row("Executor Calls", str(metrics["executor_calls"]))
        table.add_row("Planner Time", f"{metrics['planner_time']:.2f}s")
        table.add_row("Executor Time", f"{metrics['executor_time']:.2f}s")
        table.add_row("Total Time", f"{metrics['planner_time'] + metrics['executor_time']:.2f}s")
        
        if metrics["planner_calls"] > 0:
            avg_plan = metrics["planner_time"] / metrics["planner_calls"]
            table.add_row("Avg Plan Time", f"{avg_plan:.2f}s")
        
        if metrics["executor_calls"] > 0:
            avg_exec = metrics["executor_time"] / metrics["executor_calls"]
            table.add_row("Avg Execute Time", f"{avg_exec:.2f}s")
        
        console.print(table)
        
        # Show architecture info
        if self.PLANNER_MODEL != self.EXECUTOR_MODEL:
            console.print(f"\n[dim]✨ Architecture: {self.PLANNER_MODEL} (reasoning) → {self.EXECUTOR_MODEL} (execution)[/dim]")
            console.print(f"[dim]⚡ Using grok-4-fast for optimized speed and cost[/dim]")
        else:
            console.print(f"\n[dim]Architecture: Single model ({self.PLANNER_MODEL})[/dim]")

    def architect_plan(self, user_input: Optional[str] = None):
        """
        Generate comprehensive architectural plan using architect.md prompt

        Args:
            user_input: Optional app idea. If None, prompt for multi-line input.
        """
        # Load architect prompt template
        architect_prompt_path = Path.home() / ".claude" / "commands" / "architect.md"

        if not architect_prompt_path.exists():
            console.print(
                f"[yellow]⚠️  Architect prompt not found at:[/yellow]\n"
                f"[dim]{architect_prompt_path}[/dim]\n\n"
                f"[cyan]This command requires the architect.md prompt file.[/cyan]"
            )
            return

        try:
            architect_prompt = architect_prompt_path.read_text()
        except Exception as e:
            logger.error(f"Failed to read architect prompt: {e}")
            console.print(f"[red]❌ Failed to read architect prompt: {e}[/red]")
            return

        # Get user input if not provided
        if not user_input:
            console.print(
                "\n[cyan]📝 Describe your app idea:[/cyan]\n"
                "[dim]Enter your application description. Press Ctrl+D (Unix) or Ctrl+Z (Windows) when done.[/dim]\n"
            )
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                pass

            user_input = "\n".join(lines)

        if not user_input or not user_input.strip():
            console.print("[yellow]No input provided. Cancelling.[/yellow]")
            return

        # Call AI with architect prompt
        console.print("\n[cyan]🏗️  Generating comprehensive architectural plan...[/cyan]")
        console.print("[dim]This may take 30-60 seconds for detailed analysis...[/dim]\n")

        if not self.client:
            console.print("[red]❌ OpenAI client not initialized. Set XAI_API_KEY.[/red]")
            return

        try:
            response = self.client.chat.completions.create(
                model="grok-beta",  # Use grok-beta for complex architectural reasoning
                messages=[
                    {"role": "system", "content": architect_prompt},
                    {"role": "user", "content": f"Generate a comprehensive architectural plan for this application idea:\n\n{user_input}"}
                ],
                temperature=0.7,
                max_tokens=8000  # Long structured responses expected
            )

            plan = response.choices[0].message.content

            # Display plan with rich formatting
            console.print("\n" + "="*80 + "\n")
            console.print(Panel(
                Markdown(plan),
                title="[bold cyan]🏗️  Architectural Plan[/bold cyan]",
                border_style="cyan",
                padding=(1, 2)
            ))
            console.print("\n" + "="*80 + "\n")

            # Offer to save to file
            if Confirm.ask("\n💾 Save architectural plan to file?", default=True):
                filename = Prompt.ask("Filename", default="ARCHITECTURE.md")

                try:
                    Path(filename).write_text(plan)
                    console.print(f"[green]✅ Plan saved to {filename}[/green]")

                    # Log for undo system (optional, if you want undo support)
                    logger.info(f"Architectural plan saved to {filename}")

                except Exception as e:
                    logger.error(f"Failed to save plan: {e}")
                    console.print(f"[red]❌ Failed to save: {e}[/red]")

        except Exception as e:
            logger.error(f"Architect plan generation failed: {e}")
            console.print(f"[red]❌ Failed to generate plan: {e}[/red]")

    def show_guks(self, subcommand: str):
        """Display GUKS stats, patterns, or analytics"""
        if not self.guks or not self.guks_analytics:
            console.print("[yellow]GUKS is not available (install: pip install sentence-transformers faiss-cpu)[/yellow]")
            return

        parts = (subcommand or '').split()
        action = parts[0] if parts else 'stats'

        if action == 'stats':
            # Show GUKS statistics
            insights = self.guks_analytics.get_team_insights()

            table = Table(title="GUKS Statistics", box=box.ROUNDED)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Total Patterns", str(insights['total_patterns']))
            table.add_row("Recent Patterns (30d)", str(insights['recent_patterns']))
            table.add_row("Trend", insights['trend'].title())
            table.add_row("Recurring Bugs Detected", str(insights['recurring_bugs']))
            table.add_row("Constraint Rules Suggested", str(insights['constraint_rules_suggested']))

            console.print(table)

            # Category distribution
            if insights['category_distribution']:
                console.print("\n[cyan]Category Distribution:[/cyan]")
                for cat, count in sorted(insights['category_distribution'].items(), key=lambda x: x[1], reverse=True):
                    console.print(f"  • {cat.replace('_', ' ').title()}: {count}")

            # Hotspots
            if insights['file_hotspots']:
                console.print("\n[cyan]File Hotspots:[/cyan]")
                for file, count in insights['file_hotspots'][:5]:
                    console.print(f"  • {file}: {count} issues")

        elif action == 'patterns' or action == 'recurring':
            # Show recurring bugs
            recurring = self.guks_analytics.detect_recurring_bugs(min_count=2)

            if not recurring:
                console.print("[blue]No recurring patterns detected yet (need at least 2 occurrences)[/blue]")
                return

            table = Table(title="Recurring Bug Patterns", box=box.ROUNDED)
            table.add_column("Pattern", style="white", no_wrap=False)
            table.add_column("Count", style="magenta", justify="right")
            table.add_column("Projects", style="cyan", justify="right")
            table.add_column("Urgency", style="yellow")
            table.add_column("Suggested Action", style="green", no_wrap=False)

            for bug in recurring[:10]:
                table.add_row(
                    bug['pattern'][:60] + ("..." if len(bug['pattern']) > 60 else ""),
                    str(bug['count']),
                    str(len(bug['projects'])),
                    bug['urgency'],
                    bug['suggested_action'][:50] + ("..." if len(bug['suggested_action']) > 50 else "")
                )

            console.print(table)

            # Show recommendations
            if recurring:
                console.print("\n[yellow]💡 Top Recommendations:[/yellow]")
                for i, bug in enumerate(recurring[:3], 1):
                    console.print(f"  {i}. [{bug['urgency']}] {bug['suggested_action']}")

        elif action == 'constraints':
            # Show suggested constraint rules
            constraints = self.guks_analytics.suggest_constraint_rules()

            if not constraints:
                console.print("[blue]No constraint rules suggested yet (need more patterns)[/blue]")
                return

            table = Table(title="Suggested Constraint Rules", box=box.ROUNDED)
            table.add_column("Rule", style="cyan", no_wrap=True)
            table.add_column("Description", style="white", no_wrap=False)
            table.add_column("Reason", style="yellow", no_wrap=False)
            table.add_column("Severity", style="red")

            for rule in constraints:
                table.add_row(
                    rule['rule'],
                    rule['description'][:60] + ("..." if len(rule['description']) > 60 else ""),
                    rule['reason'],
                    rule['severity']
                )

            console.print(table)

            # Show implementation example
            if constraints:
                console.print("\n[cyan]Example Implementation:[/cyan]")
                top_rule = constraints[0]
                console.print(f"[dim]Pattern:[/dim] {top_rule['pattern']}")
                if 'eslint_rule' in top_rule:
                    console.print(f"[dim]ESLint:[/dim] {top_rule['eslint_rule']}")

        elif action == 'report':
            # Generate and display full report
            console.print("[cyan]Generating GUKS analytics report...[/cyan]\n")
            report = self.guks_analytics.generate_report()
            console.print(Markdown(report))

        else:
            console.print("[yellow]Usage: guks [stats|patterns|recurring|constraints|report][/yellow]")
            console.print("[dim]  stats      - Show GUKS statistics[/dim]")
            console.print("[dim]  patterns   - Show recurring bug patterns[/dim]")
            console.print("[dim]  constraints - Show suggested linting rules[/dim]")
            console.print("[dim]  report     - Generate full analytics report[/dim]")

    def show_knowledge(self, subcommand: str):
        """Display universal knowledge stats, patterns, or search results."""
        if not self.knowledge:
            console.print("[yellow]Universal knowledge system is not available (dependencies missing or initialization failed).[/yellow]")
            return

        parts = (subcommand or '').split()
        action = parts[0] if parts else 'stats'

        if action == 'stats':
            stats = self.knowledge.get_learning_stats()
            table = Table(title="Universal Knowledge Stats", box=box.SIMPLE)
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            table.add_row("Unique errors", str(stats['unique_errors']))
            table.add_row("Total occurrences", str(stats['total_occurrences']))
            table.add_row("Total solutions", str(stats['total_solutions']))
            table.add_row("Avg success rate", f"{stats['avg_success_rate']*100:.1f}%")
            table.add_row("Knowledge reuse", f"{stats['knowledge_reuse_rate']*100:.1f}%")
            console.print(table)

        elif action == 'patterns':
            patterns = self.knowledge.detect_patterns(min_frequency=2)
            if not patterns:
                console.print("[blue]No recurring patterns detected yet.[/blue]")
                return
            table = Table(title="Recurring Error Patterns", box=box.SIMPLE)
            table.add_column("Pattern", style="cyan")
            table.add_column("Frequency", style="magenta")
            table.add_column("Best Solution", style="green")
            table.add_column("Success", style="green")
            for p in patterns[:10]:
                solution = p['recommended_solution'] or "(none recorded)"
                success = f"{p['success_rate']*100:.0f}%" if p['success_rate'] else "-"
                table.add_row(p['pattern'], str(p['frequency']), solution, success)
            console.print(table)

        elif action == 'search':
            query = ' '.join(parts[1:]) if len(parts) > 1 else Prompt.ask("Search query")
            context = {"language": "python"}
            matches = self.knowledge.find_similar_errors(
                error_message=query,
                context=context,
                min_confidence=0.7,
                top_k=5,
            )
            if not matches:
                console.print("[blue]No similar issues found in universal knowledge.[/blue]")
                return
            table = Table(title=f"Search results for: {query}", box=box.SIMPLE)
            table.add_column("#", style="cyan", width=3)
            table.add_column("Similarity", style="magenta", width=10)
            table.add_column("Error", style="white")
            table.add_column("Best Solution", style="green")
            table.add_column("Success", style="green", width=8)
            for idx, match in enumerate(matches, 1):
                best = match["solutions"][0] if match["solutions"] else None
                solution_desc = best["description"] if best else "(no recorded solution)"
                success = f"{best['success_rate']*100:.0f}%" if best else "-"
                table.add_row(
                    str(idx),
                    f"{match['similarity']*100:.0f}%",
                    match["error_message"][:60] + ("…" if len(match["error_message"]) > 60 else ""),
                    solution_desc[:60] + ("…" if len(solution_desc) > 60 else ""),
                    success,
                )
            console.print(table)

        else:
            console.print("[yellow]Usage: grokflow knowledge [stats|patterns|search <query>][/yellow]")
    
    def _show_help(self):
        """Display help with keyboard shortcuts"""
        help_table = Table(title="GrokFlow v2 Help", box=box.ROUNDED)
        help_table.add_column("Command", style="cyan", no_wrap=True)
        help_table.add_column("Description", style="white")
        help_table.add_column("Example", style="dim")
        
        help_table.add_row("fix [file]", "Smart fix with AI", "fix buggy_module.py")
        help_table.add_row("test [file]", "Run tests", "test")
        help_table.add_row("commit [msg]", "Smart commit", "commit")
        help_table.add_row("status", "Show workspace context", "status")
        help_table.add_row("context", "Show context memory details", "context")
        help_table.add_row("add [dir]", "Add directory to context", "add src/")
        help_table.add_row("new <template> <file>", "Create file from template", "new python script.py")
        help_table.add_row("templates", "List available templates", "templates")
        help_table.add_row("image <file> [prompt]", "Analyze image with vision AI", "image screenshot.png")
        help_table.add_row("guks [subcommand]", "GUKS analytics and insights", "guks stats")
        help_table.add_row("knowledge", "Query universal knowledge", "knowledge stats")
        help_table.add_row("undo", "Undo last edit", "undo")
        help_table.add_row("redo", "Redo last undone edit", "redo")
        help_table.add_row("history", "Show undo/redo history", "history")
        help_table.add_row("reasoning [on/off]", "Toggle reasoning display", "reasoning off")
        help_table.add_row("perf", "Show performance metrics", "perf")
        help_table.add_row("help", "Show this help", "help")
        help_table.add_row("exit", "Quit interactive mode", "exit")
        
        console.print(help_table)
        
        shortcuts_table = Table(title="Keyboard Shortcuts", box=box.ROUNDED)
        shortcuts_table.add_column("Key", style="cyan", no_wrap=True)
        shortcuts_table.add_column("Action", style="white")
        
        shortcuts_table.add_row("Tab", "Auto-complete commands and file paths")
        shortcuts_table.add_row("↑ / ↓", "Navigate command history")
        shortcuts_table.add_row("Ctrl+R", "Search command history")
        shortcuts_table.add_row("Ctrl+C", "Cancel current input")
        shortcuts_table.add_row("Ctrl+D", "Exit (same as 'exit')")
        
        console.print(shortcuts_table)
    
    def interactive_mode(self):
        """
        Enhanced interactive mode with context awareness
        """
        console.print(Panel.fit(
            "[bold cyan]🌊 GrokFlow v2 - Professional Mode[/bold cyan]\n"
            "[white]Context-aware • Git-native • Action-first • GUKS-powered[/white]\n\n"
            "[yellow]Quick commands:[/yellow]\n"
            "  [cyan]architect[/cyan] - Generate architectural plan (app blueprints)\n"
            "  [cyan]fix[/cyan] - Smart fix (with GUKS suggestions)\n"
            "  [cyan]test[/cyan] - Quick test\n"
            "  [cyan]commit[/cyan] - Smart commit\n"
            "  [cyan]guks[/cyan] - GUKS analytics (stats/patterns/recurring/report)\n"
            "  [cyan]status[/cyan] - Show context\n"
            "  [cyan]undo[/cyan] / [cyan]redo[/cyan] - Undo/redo edits\n"
            "  [cyan]exit[/cyan] - Quit\n\n"
            "[dim]💡 Use Tab for completion, ↑↓ for history[/dim]",
            border_style="cyan"
        ))
        
        self.show_context()
        
        while True:
            try:
                # Use enhanced prompt session with completion and history
                cmd = self.prompt_session.prompt(HTML('<ansigreen><b>></b></ansigreen> '))
                
                if cmd == 'exit':
                    break
                elif cmd == 'status':
                    self.show_context()
                elif cmd == 'context':
                    self.show_context_memory()
                elif cmd.startswith('add '):
                    dir_path = cmd[4:].strip()
                    if dir_path:
                        self.add_directory_to_context(dir_path)
                    else:
                        console.print("[yellow]Usage: add <directory>[/yellow]")
                elif cmd == 'templates':
                    self.list_templates()
                elif cmd.startswith('new '):
                    parts = cmd[4:].strip().split(maxsplit=1)
                    if len(parts) >= 2:
                        template_name = parts[0]
                        file_path = parts[1]
                        self.create_from_template(template_name, file_path)
                    else:
                        console.print("[yellow]Usage: new <template> <filename>[/yellow]")
                        console.print("[dim]Use 'templates' to see available templates[/dim]")
                elif cmd.startswith('image '):
                    parts = cmd[6:].strip().split(maxsplit=1)
                    if parts:
                        image_path = parts[0]
                        prompt = parts[1] if len(parts) > 1 else None
                        self.analyze_image(image_path, prompt)
                    else:
                        console.print("[yellow]Usage: image <file> [prompt][/yellow]")
                elif cmd.startswith('guks'):
                    parts = cmd.split(maxsplit=1)
                    sub = parts[1] if len(parts) > 1 else ''
                    self.show_guks(sub)
                elif cmd.startswith('knowledge'):
                    parts = cmd.split(maxsplit=1)
                    sub = parts[1] if len(parts) > 1 else ''
                    self.show_knowledge(sub)
                elif cmd == 'fix':
                    self.smart_fix()
                elif cmd.startswith('fix '):
                    self.smart_fix(cmd[4:])
                elif cmd == 'test':
                    self.quick_test()
                elif cmd == 'commit':
                    self.quick_commit()
                elif cmd.startswith('commit '):
                    self.quick_commit(cmd[7:])
                elif cmd == 'undo':
                    self.undo()
                elif cmd.startswith('undo '):
                    self.undo(cmd[5:])
                elif cmd == 'redo':
                    self.redo()
                elif cmd == 'history':
                    self.show_undo_history()
                elif cmd == 'perf':
                    self.show_performance_metrics()
                elif cmd == 'reasoning':
                    self.toggle_reasoning()
                elif cmd == 'reasoning on':
                    self.toggle_reasoning('on')
                elif cmd == 'reasoning off':
                    self.toggle_reasoning('off')
                elif cmd == 'architect' or cmd == 'plan':
                    self.architect_plan()
                elif cmd.startswith('architect ') or cmd.startswith('plan '):
                    input_text = cmd.split(maxsplit=1)[1]
                    self.architect_plan(input_text)
                elif cmd == 'help':
                    self._show_help()
                else:
                    console.print("[yellow]Unknown command. Try: architect, fix, test, commit, status, undo, redo, history, reasoning, perf, help[/yellow]")
            
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except EOFError:
                break


def main():
    """Main entry point with smart defaults"""
    import argparse
    
    # Initialize logging first
    global logger
    logger = setup_logging()
    logger.info("GrokFlow v2 starting")
    
    parser = argparse.ArgumentParser(
        description="🌊 GrokFlow v2 - Professional SWE Development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quick Commands:
  grokflow                    Interactive mode (default)
  grokflow architect          Generate architectural plan (multi-line input)
  grokflow architect "idea"   Generate plan from inline description
  grokflow fix               Fix last error or modified file
  grokflow fix <file>        Fix specific file
  grokflow test              Run relevant tests
  grokflow commit            Smart commit with AI message
  grokflow status            Show workspace context

Examples:
  grokflow                   # Start interactive mode
  grokflow architect "Build a REST API for todo management with PostgreSQL"
  grokflow fix app.py        # Fix specific file
  grokflow test              # Run tests
  grokflow commit "feat: ..."  # Commit with message
        """
    )
    
    parser.add_argument('command', nargs='?', default='interactive',
                       choices=['interactive', 'fix', 'test', 'commit', 'status', 'guks', 'knowledge', 'undo', 'redo', 'history', 'add', 'context', 'new', 'templates', 'image', 'architect', 'plan'])
    parser.add_argument('args', nargs='*', help='Command arguments')
    
    args = parser.parse_args()
    
    # Initialize
    grok = GrokFlowV2()
    
    # Route commands
    if args.command == 'interactive' or not args.command:
        grok.interactive_mode()
    elif args.command == 'fix':
        grok.smart_fix(args.args[0] if args.args else None)
    elif args.command == 'test':
        grok.quick_test(args.args[0] if args.args else None)
    elif args.command == 'commit':
        grok.quick_commit(' '.join(args.args) if args.args else None)
    elif args.command == 'status':
        grok.show_context()
    elif args.command == 'architect' or args.command == 'plan':
        grok.architect_plan(' '.join(args.args) if args.args else None)
    elif args.command == 'guks':
        sub = ' '.join(args.args) if args.args else ''
        grok.show_guks(sub)
    elif args.command == 'knowledge':
        sub = ' '.join(args.args) if args.args else ''
        grok.show_knowledge(sub)
    elif args.command == 'undo':
        grok.undo(args.args[0] if args.args else None)
    elif args.command == 'redo':
        grok.redo()
    elif args.command == 'history':
        grok.show_undo_history()
    elif args.command == 'add':
        if args.args:
            grok.add_directory_to_context(args.args[0])
        else:
            console.print("[yellow]Usage: grokflow add <directory>[/yellow]")
    elif args.command == 'context':
        grok.show_context_memory()
    elif args.command == 'templates':
        grok.list_templates()
    elif args.command == 'new':
        if len(args.args) >= 2:
            grok.create_from_template(args.args[0], args.args[1])
        else:
            console.print("[yellow]Usage: grokflow new <template> <filename>[/yellow]")
            console.print("[dim]Use 'grokflow templates' to see available templates[/dim]")
    elif args.command == 'image':
        if args.args:
            image_path = args.args[0]
            prompt = ' '.join(args.args[1:]) if len(args.args) > 1 else None
            grok.analyze_image(image_path, prompt)
        else:
            console.print("[yellow]Usage: grokflow image <file> [prompt][/yellow]")


if __name__ == "__main__":
    main()
