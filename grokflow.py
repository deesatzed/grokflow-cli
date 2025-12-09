#!/usr/bin/env python3
"""
GrokFlow CLI - Ultimate Vibe Coding with Grok-4-fast
Command-line interface for reasoning-amplified development
"""
import os
import sys
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
import httpx
from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.layout import Layout
from rich import box
from codebase_manager import CodebaseManager

# VAMS Skill Manager import
try:
    from grokflow_skill_manager import GrokFlowSkillManager
    VAMS_AVAILABLE = True
except ImportError:
    VAMS_AVAILABLE = False
    GrokFlowSkillManager = None

# Constraint Manager import
try:
    from grokflow_constraints import ConstraintManager
    CONSTRAINTS_AVAILABLE = True
except ImportError:
    CONSTRAINTS_AVAILABLE = False
    ConstraintManager = None

console = Console()

class GrokFlowCLI:
    """Main CLI application class"""

    def __init__(self, codebase_root: str = "."):
        self.api_key = os.getenv("XAI_API_KEY")
        if not self.api_key:
            console.print("[red]Error: XAI_API_KEY not set in environment[/red]")
            console.print("Set it with: export XAI_API_KEY='your_key_here'")
            sys.exit(1)

        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1",
            timeout=httpx.Timeout(3600.0)
        )

        self.config_dir = Path.home() / ".grokflow"
        self.config_dir.mkdir(exist_ok=True)
        self.session_file = self.config_dir / "session.json"
        self.history_file = self.config_dir / "history.json"
        self.first_run_file = self.config_dir / ".first_run"

        self.session = self.load_session()
        self.codebase = CodebaseManager(codebase_root)
        self.vibe_modes = {
            "creative": {"temp": 0.7, "desc": "🎨 Maximum innovation"},
            "focused": {"temp": 0.3, "desc": "🎯 Task-oriented"},
            "analytical": {"temp": 0.3, "desc": "🧠 Deep reasoning"},
            "rapid": {"temp": 0.5, "desc": "⚡ Speed-first"}
        }

        # Initialize VAMS Skill Manager
        if VAMS_AVAILABLE:
            try:
                self.skill_manager = GrokFlowSkillManager()
                console.print("[dim]✨ VAMS Skill Memory enabled[/dim]")
            except Exception as e:
                console.print(f"[dim yellow]⚠ VAMS not available: {str(e)}[/dim yellow]")
                self.skill_manager = None
        else:
            self.skill_manager = None

        # Initialize Constraint Manager
        if CONSTRAINTS_AVAILABLE:
            try:
                self.constraint_manager = ConstraintManager(self.config_dir)
            except Exception as e:
                console.print(f"[dim yellow]⚠ Constraints not available: {str(e)}[/dim yellow]")
                self.constraint_manager = None
        else:
            self.constraint_manager = None

        # Track recently used skills for feedback (Phase D2: Hebbian learning)
        self.recent_skill_ids = []

        # Show first-run welcome message
        self._show_first_run_welcome()

    def _show_first_run_welcome(self):
        """Show welcome message on first run"""
        if not self.first_run_file.exists():
            console.print()
            console.print(Panel.fit(
                "[bold cyan]Welcome to GrokFlow![/bold cyan]\n\n"
                "GrokFlow learns from your code to help you write\n"
                "better code faster over time.\n\n"
                "[yellow]✨ Key Features:[/yellow]\n"
                "• Learns patterns from successful code\n"
                "• Suggests improvements automatically\n"
                "• Never forgets - 100% retention\n"
                "• Works across all your projects\n\n"
                "[dim]Your code patterns will be learned automatically.[/dim]\n"
                "[dim]Run 'grokflow skill stats' to see your progress.[/dim]",
                border_style="cyan"
            ))
            console.print()

            # Create first_run file to mark as shown
            try:
                self.first_run_file.touch()
            except Exception:
                pass  # Silent fail if can't create marker

    def load_session(self) -> Dict:
        """Load existing session or create new one"""
        if self.session_file.exists():
            with open(self.session_file, 'r') as f:
                return json.load(f)
        return {
            "messages": [],
            "response_id": None,
            "vibe_mode": "creative",
            "project_context": "",
            "total_tokens": 0,
            "reasoning_tokens": 0,
            "completion_tokens": 0
        }
    
    def save_session(self):
        """Save current session"""
        with open(self.session_file, 'w') as f:
            json.dump(self.session, f, indent=2)
    
    def add_to_history(self, entry: Dict):
        """Add entry to history"""
        history = []
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                history = json.load(f)

        history.append({
            **entry,
            "timestamp": datetime.now().isoformat()
        })

        # Keep only last 100 entries
        history = history[-100:]

        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def _extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """Extract code blocks from markdown response"""
        blocks = []
        if "```" not in content:
            return blocks

        parts = content.split("```")
        for i, part in enumerate(parts):
            if i % 2 == 1:  # Code block
                lines = part.split('\n')
                lang = lines[0].strip() if lines else "python"
                code = '\n'.join(lines[1:])
                if code.strip():
                    blocks.append({"language": lang, "code": code})
        return blocks

    def _compress_reasoning(self, reasoning_text: str, max_tokens: int = 120) -> str:
        """Compress Grok-4 reasoning to 120-token limit"""
        # Simple compression: take first 120 words (rough token approximation)
        words = reasoning_text.split()
        compressed = ' '.join(words[:max_tokens])
        if len(words) > max_tokens:
            compressed += "..."
        return compressed

    def _extract_and_store_skill(self, prompt: str, response: str, reasoning_tokens: int = 0):
        """Extract code skill from successful generation and store in VAMS"""
        if not self.skill_manager:
            return

        # Extract code blocks
        code_blocks = self._extract_code_blocks(response)
        if not code_blocks:
            return  # No code to learn

        # For now, store the first significant code block as a skill
        for block in code_blocks:
            code = block['code'].strip()
            language = block['language'] or 'python'

            # Skip trivial code (< 3 lines)
            if len(code.split('\n')) < 3:
                continue

            # Generate skill metadata from prompt + code
            # Simple heuristic: extract key action words from prompt
            prompt_lower = prompt.lower()

            # Determine domain from keywords
            domain = "general"
            if any(word in prompt_lower for word in ['api', 'endpoint', 'fastapi', 'flask']):
                domain = "api"
            elif any(word in prompt_lower for word in ['test', 'pytest', 'unittest']):
                domain = "testing"
            elif any(word in prompt_lower for word in ['async', 'await', 'asyncio']):
                domain = "async"
            elif any(word in prompt_lower for word in ['database', 'sql', 'orm']):
                domain = "database"

            # Extract first sentence of prompt as description
            description_parts = prompt.split('.')
            description = description_parts[0].strip() if description_parts else prompt[:100]

            # Extract tags from prompt
            tags = []
            for word in prompt_lower.split():
                if len(word) > 4 and word.isalpha():  # Meaningful words only
                    tags.append(word)
            tags = list(set(tags[:5]))  # Dedupe, limit to 5

            # Generate name (first 5 words of prompt)
            name_words = prompt.split()[:5]
            name = ' '.join(name_words)

            # Compress reasoning (if available in future)
            reasoning_chain = self._compress_reasoning(
                f"Generated for: {prompt}",
                max_tokens=120
            )

            try:
                skill_id = self.skill_manager.register_skill(
                    skill_id="",  # Auto-generate from code hash
                    name=name,
                    description=description,
                    code=code,
                    language=language,
                    domain=domain,
                    vibe_mode=self.session.get("vibe_mode", "creative"),
                    reasoning_chain=reasoning_chain,
                    tags=tags
                )

                # Get total skill count for celebration
                total_skills = len(self.skill_manager.list_skills())

                # Prominent celebration message
                console.print()
                console.print(Panel.fit(
                    f"[bold green]🎉 New Pattern Learned![/bold green]\n\n"
                    f"[cyan]{name[:60]}[/cyan]\n"
                    f"[dim]• Domain: {domain.title()}[/dim]\n"
                    f"[dim]• Will help with: Future {domain} tasks[/dim]\n\n"
                    f"[yellow]Total skills: {total_skills}[/yellow] "
                    f"[dim](+1 today)[/dim]\n"
                    f"[dim]View details: grokflow skill last[/dim]",
                    border_style="green"
                ))
                console.print()

                # Add helpful tip for first skill
                if total_skills == 1:
                    console.print("[dim cyan]💡 Tip: Run tests to strengthen good patterns![/dim cyan]\n")

            except Exception as e:
                console.print(f"[yellow]⚠ Could not store skill: {str(e)}[/yellow]")

            break  # Store only the first significant block

    def chat(self, prompt: str, system_message: Optional[str] = None,
             stream: bool = True) -> Dict:
        """Send chat message to Grok-4"""

        # CHECK CONSTRAINTS BEFORE GENERATION (Phase 1: Constraint System)
        if self.constraint_manager:
            triggered_constraints = self.constraint_manager.check_constraints(prompt)

            if triggered_constraints:
                for constraint in triggered_constraints:
                    action = constraint["enforcement_action"]
                    message = constraint["enforcement_message"]

                    if action == "block":
                        console.print(f"\n[red]🚫 Blocked by constraint:[/red]")
                        console.print(f"[yellow]{message}[/yellow]\n")
                        return {"success": False, "error": "Blocked by constraint", "constraint": constraint}

                    elif action == "warn":
                        console.print(f"\n[yellow]⚠️  Constraint warning:[/yellow]")
                        console.print(f"[dim]{message}[/dim]\n")

                    elif action == "require_action":
                        console.print(f"\n[cyan]📋 Constraint requires action:[/cyan]")
                        console.print(f"[yellow]{message}[/yellow]")
                        console.print("[dim]Proceeding with caution...[/dim]\n")

        # Build messages
        messages = []

        # Add system message based on vibe mode
        vibe = self.session["vibe_mode"]
        base_system = f"You are an expert software engineer. {self.vibe_modes[vibe]['desc']}."

        if self.session["project_context"]:
            base_system += f"\n\nProject Context: {self.session['project_context']}"

        if system_message:
            base_system += f"\n\n{system_message}"

        # Inject relevant skills from VAMS memory (skill recall)
        if self.skill_manager:
            try:
                relevant_skills = self.skill_manager.find_skills(
                    query=prompt,
                    k=3,
                    vibe_mode=vibe  # Vibe-aware filtering
                )

                if relevant_skills:
                    skill_hints = "\n".join([
                        f"• {s['skill']['name']}: {s['skill']['description'][:80]}..."
                        for s in relevant_skills
                    ])
                    base_system += f"\n\n📚 Relevant patterns you've learned before:\n{skill_hints}"

                    # Show transparent skill recall
                    console.print()
                    console.print("[bold cyan]📚 Found relevant patterns from your past work:[/bold cyan]\n")

                    # Create table of recalled skills
                    skill_table = Table(box=box.SIMPLE, show_header=False)
                    skill_table.add_column("", style="dim")
                    skill_table.add_column("Pattern", style="cyan")
                    skill_table.add_column("Match", style="green")
                    skill_table.add_column("Quality", style="yellow")

                    for i, s in enumerate(relevant_skills, 1):
                        skill = s['skill']
                        confidence = s.get('confidence', 0) * 100

                        # Determine quality from success rate
                        usage = skill.get('usage_count', 0)
                        success = skill.get('success_count', 0)
                        if usage > 0:
                            success_rate = (success / usage) * 100
                            if success_rate >= 80:
                                quality = "[green]Excellent[/green]"
                            elif success_rate >= 60:
                                quality = "[yellow]Good[/yellow]"
                            else:
                                quality = "[dim]Fair[/dim]"
                        else:
                            quality = "[dim]New[/dim]"

                        # Truncate name
                        name = skill['name'][:35] + "..." if len(skill['name']) > 35 else skill['name']

                        skill_table.add_row(
                            f"{i}.",
                            name,
                            f"{confidence:.0f}% ✓",
                            quality
                        )

                    console.print(skill_table)
                    console.print()

                    # Track skill IDs for potential feedback (Phase D2)
                    self.recent_skill_ids = [s['skill']['skill_id'] for s in relevant_skills]
            except Exception as e:
                console.print(f"[dim yellow]⚠ Skill recall failed: {str(e)}[/dim yellow]")

        messages.append({"role": "system", "content": base_system})
        
        # Add conversation history (last 10 messages)
        messages.extend(self.session["messages"][-10:])
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        try:
            if stream:
                return self._chat_stream(messages)
            else:
                return self._chat_complete(messages)
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            return {"success": False, "error": str(e)}
    
    def _chat_stream(self, messages: List[Dict]) -> Dict:
        """Stream chat response"""
        # Show skill count if VAMS available
        skill_count_msg = ""
        if self.skill_manager:
            total_skills = len(self.skill_manager.list_skills())
            if total_skills > 0:
                skill_count_msg = f" [dim](using {total_skills} learned patterns)[/dim]"

        console.print(f"\n[cyan]🧠 Grok-4 is thinking...{skill_count_msg}[/cyan]\n")

        response_text = ""

        with console.status("[bold cyan]Generating response...") as status:
            stream = self.client.chat.completions.create(
                model="grok-4",
                messages=messages,
                temperature=self.vibe_modes[self.session["vibe_mode"]]["temp"],
                max_tokens=2000,
                stream=True
            )

            console.print("[green]Response:[/green]\n")

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response_text += content
                    console.print(content, end="")

            console.print("\n")

        # Update session
        self.session["messages"].append({"role": "user", "content": messages[-1]["content"]})
        self.session["messages"].append({"role": "assistant", "content": response_text})

        self.save_session()

        # Extract and store skills from code generation (VAMS skill learning)
        self._extract_and_store_skill(
            prompt=messages[-1]["content"],
            response=response_text,
            reasoning_tokens=0  # Not available in streaming mode
        )

        return {
            "success": True,
            "content": response_text
        }
    
    def _chat_complete(self, messages: List[Dict]) -> Dict:
        """Complete chat response (non-streaming)"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("🧠 Grok-4 is reasoning...", total=None)
            
            response = self.client.chat.completions.create(
                model="grok-4",
                messages=messages,
                temperature=self.vibe_modes[self.session["vibe_mode"]]["temp"],
                max_tokens=2000
            )
            
            progress.update(task, completed=True)
        
        content = response.choices[0].message.content
        usage = response.usage
        
        # Update session
        self.session["messages"].append({"role": "user", "content": messages[-1]["content"]})
        self.session["messages"].append({"role": "assistant", "content": content})
        self.session["reasoning_tokens"] += getattr(usage, 'reasoning_tokens', 0)
        self.session["completion_tokens"] += usage.completion_tokens
        self.session["total_tokens"] += usage.total_tokens

        self.save_session()

        # Extract and store skills from code generation (VAMS skill learning)
        self._extract_and_store_skill(
            prompt=messages[-1]["content"],
            response=content,
            reasoning_tokens=getattr(usage, 'reasoning_tokens', 0)
        )

        # Add to history
        self.add_to_history({
            "prompt": messages[-1]["content"],
            "response": content,
            "reasoning_tokens": getattr(usage, 'reasoning_tokens', 0),
            "completion_tokens": usage.completion_tokens
        })

        return {
            "success": True,
            "content": content,
            "usage": {
                "reasoning_tokens": getattr(usage, 'reasoning_tokens', 0),
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens
            }
        }
    
    def cmd_chat(self, args):
        """Interactive chat mode"""
        console.print(Panel.fit(
            "[bold cyan]🌊 GrokFlow Interactive Chat[/bold cyan]\n"
            f"Vibe Mode: {self.session['vibe_mode']} {self.vibe_modes[self.session['vibe_mode']]['desc']}\n"
            "Type 'exit' to quit, 'help' for commands",
            border_style="cyan"
        ))
        
        while True:
            try:
                prompt = Prompt.ask("\n[bold green]You[/bold green]")
                
                if prompt.lower() == 'exit':
                    break
                elif prompt.lower() == 'help':
                    self.show_help()
                    continue
                elif prompt.lower() == 'clear':
                    console.clear()
                    continue
                elif prompt.lower().startswith('/'):
                    self.handle_command(prompt)
                    continue
                
                result = self.chat(prompt, stream=True)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except EOFError:
                break
    
    def cmd_generate(self, args):
        """Generate code from description"""
        if args.file:
            with open(args.file, 'r') as f:
                prompt = f.read()
        else:
            prompt = args.prompt
        
        if not prompt:
            console.print("[red]Error: No prompt provided[/red]")
            return
        
        system_msg = "Generate clean, production-ready code. Include comments and error handling."
        
        result = self.chat(prompt, system_message=system_msg, stream=False)
        
        if result["success"]:
            # Display code with syntax highlighting
            console.print("\n[green]Generated Code:[/green]\n")
            
            # Try to extract code blocks
            content = result["content"]
            if "```" in content:
                # Extract code from markdown
                parts = content.split("```")
                for i, part in enumerate(parts):
                    if i % 2 == 1:  # Code block
                        lines = part.split('\n')
                        lang = lines[0].strip() if lines else "python"
                        code = '\n'.join(lines[1:])
                        syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
                        console.print(syntax)
                    else:
                        console.print(Markdown(part))
            else:
                console.print(Markdown(content))
            
            # Show metrics
            if "usage" in result:
                self.show_metrics(result["usage"])
            
            # Offer to save
            if args.output or Confirm.ask("\n[cyan]Save to file?[/cyan]"):
                output_file = args.output or Prompt.ask("Output filename")
                with open(output_file, 'w') as f:
                    f.write(content)
                console.print(f"[green]✓ Saved to {output_file}[/green]")
    
    def cmd_debug(self, args):
        """Debug code with reasoning"""
        if args.file:
            with open(args.file, 'r') as f:
                code = f.read()
        else:
            console.print("[yellow]Paste your code (Ctrl+D when done):[/yellow]")
            code = sys.stdin.read()
        
        prompt = f"Debug this code and explain the issues:\n\n```\n{code}\n```"
        
        if args.error:
            prompt += f"\n\nError message: {args.error}"
        
        result = self.chat(prompt, stream=False)
        
        if result["success"]:
            console.print("\n[green]Debug Analysis:[/green]\n")
            console.print(Markdown(result["content"]))
            
            if "usage" in result:
                self.show_metrics(result["usage"])
    
    def cmd_optimize(self, args):
        """Optimize code"""
        if args.file:
            with open(args.file, 'r') as f:
                code = f.read()
        else:
            console.print("[yellow]Paste your code (Ctrl+D when done):[/yellow]")
            code = sys.stdin.read()
        
        prompt = f"Optimize this code for performance and readability:\n\n```\n{code}\n```"
        
        result = self.chat(prompt, stream=False)
        
        if result["success"]:
            console.print("\n[green]Optimized Code:[/green]\n")
            console.print(Markdown(result["content"]))
            
            if "usage" in result:
                self.show_metrics(result["usage"])
    
    def cmd_vibe(self, args):
        """Set vibe mode"""
        if args.mode:
            if args.mode in self.vibe_modes:
                self.session["vibe_mode"] = args.mode
                self.save_session()
                console.print(f"[green]✓ Vibe mode set to: {args.mode} {self.vibe_modes[args.mode]['desc']}[/green]")
            else:
                console.print(f"[red]Invalid mode. Choose from: {', '.join(self.vibe_modes.keys())}[/red]")
        else:
            # Show current mode and options
            table = Table(title="Vibe Modes", box=box.ROUNDED)
            table.add_column("Mode", style="cyan")
            table.add_column("Description", style="white")
            table.add_column("Temperature", style="yellow")
            table.add_column("Current", style="green")
            
            for mode, config in self.vibe_modes.items():
                current = "✓" if mode == self.session["vibe_mode"] else ""
                table.add_row(mode, config["desc"], str(config["temp"]), current)
            
            console.print(table)
    
    def cmd_context(self, args):
        """Set project context"""
        if args.text:
            self.session["project_context"] = args.text
            self.save_session()
            console.print("[green]✓ Project context updated[/green]")
        else:
            if self.session["project_context"]:
                console.print(f"[cyan]Current context:[/cyan]\n{self.session['project_context']}")
            else:
                console.print("[yellow]No project context set[/yellow]")
    
    def cmd_stats(self, args):
        """Show session statistics"""
        table = Table(title="Session Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Messages", str(len(self.session["messages"])))
        table.add_row("Total Tokens", f"{self.session['total_tokens']:,}")
        table.add_row("Reasoning Tokens", f"{self.session['reasoning_tokens']:,}")
        table.add_row("Completion Tokens", f"{self.session['completion_tokens']:,}")
        
        if self.session["total_tokens"] > 0:
            ratio = self.session["reasoning_tokens"] / self.session["total_tokens"] * 100
            table.add_row("Reasoning Ratio", f"{ratio:.1f}%")
        
        table.add_row("Vibe Mode", self.session["vibe_mode"])
        
        console.print(table)
    
    def cmd_history(self, args):
        """Show conversation history"""
        if not self.history_file.exists():
            console.print("[yellow]No history yet[/yellow]")
            return
        
        with open(self.history_file, 'r') as f:
            history = json.load(f)
        
        limit = args.limit or 10
        
        for entry in history[-limit:]:
            console.print(Panel(
                f"[cyan]Prompt:[/cyan] {entry['prompt'][:100]}...\n"
                f"[green]Response:[/green] {entry['response'][:100]}...\n"
                f"[yellow]Tokens:[/yellow] {entry.get('reasoning_tokens', 0)} reasoning, "
                f"{entry.get('completion_tokens', 0)} completion",
                title=entry['timestamp'],
                border_style="blue"
            ))
    
    def cmd_clear(self, args):
        """Clear session"""
        if Confirm.ask("[yellow]Clear current session?[/yellow]"):
            self.session = {
                "messages": [],
                "response_id": None,
                "vibe_mode": "creative",
                "project_context": "",
                "total_tokens": 0,
                "reasoning_tokens": 0,
                "completion_tokens": 0
            }
            self.save_session()
            console.print("[green]✓ Session cleared[/green]")
    
    def cmd_scan(self, args):
        """Scan codebase"""
        console.print("[cyan]📂 Scanning codebase...[/cyan]\n")
        
        structure = self.codebase.scan_codebase(max_depth=args.depth or 3)
        
        self.codebase.display_file_stats(structure)
        
        if args.tree:
            console.print()
            self.codebase.display_tree(max_depth=args.depth or 2)
        
        # Save structure to session for context
        self.session['codebase_structure'] = structure
        self.save_session()
    
    def cmd_read(self, args):
        """Read file(s)"""
        if not args.file:
            console.print("[red]Error: No file specified[/red]")
            return
        
        content = self.codebase.read_file(args.file)
        
        if content:
            console.print(f"\n[cyan]📄 {args.file}[/cyan]\n")
            
            # Detect language from extension
            ext = Path(args.file).suffix
            lang_map = {
                '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                '.jsx': 'jsx', '.tsx': 'tsx', '.java': 'java',
                '.cpp': 'cpp', '.c': 'c', '.go': 'go', '.rs': 'rust',
                '.rb': 'ruby', '.php': 'php', '.sh': 'bash'
            }
            lang = lang_map.get(ext, 'text')
            
            syntax = Syntax(content, lang, theme="monokai", line_numbers=True)
            console.print(syntax)
            
            # Show analysis for Python files
            if ext == '.py' and args.analyze:
                console.print("\n[cyan]📊 File Analysis:[/cyan]\n")
                analysis = self.codebase.analyze_python_file(args.file)
                
                if 'error' not in analysis:
                    if analysis.get('functions'):
                        console.print(f"[green]Functions:[/green] {len(analysis['functions'])}")
                        for func in analysis['functions'][:5]:
                            console.print(f"  • {func['name']}({', '.join(func['args'])})")
                    
                    if analysis.get('classes'):
                        console.print(f"\n[green]Classes:[/green] {len(analysis['classes'])}")
                        for cls in analysis['classes']:
                            console.print(f"  • {cls['name']} ({len(cls['methods'])} methods)")
    
    def cmd_edit(self, args):
        """Edit file with Grok-4's help"""
        if not args.file:
            console.print("[red]Error: No file specified[/red]")
            return
        
        # Read current content
        current_content = self.codebase.read_file(args.file)
        
        if not current_content and not args.create:
            console.print(f"[red]File not found: {args.file}[/red]")
            console.print("[yellow]Use --create to create new file[/yellow]")
            return
        
        # Get edit instructions
        if args.instruction:
            instruction = args.instruction
        else:
            instruction = Prompt.ask("\n[cyan]What changes do you want to make?[/cyan]")
        
        # Build prompt for Grok-4
        if current_content:
            prompt = f"""I need to edit this file: {args.file}

Current content:
```
{current_content}
```

Instructions: {instruction}

Please provide the complete updated file content. Include all necessary imports and maintain the existing structure."""
        else:
            prompt = f"""Create a new file: {args.file}

Instructions: {instruction}

Please provide the complete file content with all necessary imports and proper structure."""
        
        # Get Grok-4's response
        result = self.chat(prompt, stream=False)
        
        if result["success"]:
            # Extract code from response
            content = result["content"]
            
            # Try to extract code block
            if "```" in content:
                parts = content.split("```")
                for i, part in enumerate(parts):
                    if i % 2 == 1:  # Code block
                        lines = part.split('\n')
                        code = '\n'.join(lines[1:])  # Skip language identifier
                        
                        # Show preview
                        console.print("\n[green]📝 Proposed changes:[/green]\n")
                        syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
                        console.print(syntax)
                        
                        # Confirm and save
                        if Confirm.ask("\n[cyan]Save these changes?[/cyan]"):
                            if self.codebase.write_file(args.file, code):
                                console.print(f"[green]✓ File updated: {args.file}[/green]")
                        break
            else:
                console.print("[yellow]No code block found in response[/yellow]")
                console.print(Markdown(content))
    
    def cmd_run(self, args):
        """Run file and show output"""
        if not args.file:
            console.print("[red]Error: No file specified[/red]")
            return

        console.print(f"[cyan]🚀 Running {args.file}...[/cyan]\n")

        # Execute file
        exit_code, stdout, stderr = self.codebase.execute_file(
            args.file,
            args.args.split() if args.args else None
        )

        # Display output
        if stdout:
            console.print("[green]Output:[/green]")
            console.print(Panel(stdout, border_style="green"))

        if stderr:
            console.print("[red]Errors:[/red]")
            console.print(Panel(stderr, border_style="red"))

        console.print(f"\n[yellow]Exit code:[/yellow] {exit_code}")

        # Phase D2: Hebbian Learning - Record skill feedback based on test results
        if self.skill_manager and self.recent_skill_ids:
            success = (exit_code == 0)

            # Record usage for all recently suggested skills
            for skill_id in self.recent_skill_ids:
                try:
                    self.skill_manager.record_usage(
                        skill_id=skill_id,
                        success=success,
                        context={
                            "file": args.file,
                            "exit_code": exit_code,
                            "feedback_type": "test_execution"
                        }
                    )
                except Exception as e:
                    # Silent fail - don't interrupt user flow
                    pass

            # Persist feedback to disk
            try:
                self.skill_manager.save()
            except Exception:
                pass

            if success:
                console.print(f"[dim green]✅ Skill feedback: {len(self.recent_skill_ids)} skills strengthened (Hebbian)[/dim green]")
            else:
                console.print(f"[dim yellow]⚠ Skill feedback: {len(self.recent_skill_ids)} skills weakened (anti-Hebbian)[/dim yellow]")

            # Clear tracked skills
            self.recent_skill_ids = []

        # If there were errors, offer to debug
        if exit_code != 0 and args.debug:
            if Confirm.ask("\n[cyan]Debug with Grok-4?[/cyan]"):
                debug_prompt = f"""This code failed with exit code {exit_code}:

File: {args.file}

Error output:
{stderr}

Please analyze the error and suggest fixes."""

                result = self.chat(debug_prompt, stream=False)

                if result["success"]:
                    console.print("\n[green]🧠 Grok-4 Analysis:[/green]\n")
                    console.print(Markdown(result["content"]))
    
    def cmd_search(self, args):
        """Search codebase"""
        if not args.query:
            console.print("[red]Error: No search query provided[/red]")
            return
        
        console.print(f"[cyan]🔍 Searching for: {args.query}[/cyan]\n")
        
        results = self.codebase.search_codebase(args.query, args.pattern or "*")
        
        if not results:
            console.print("[yellow]No results found[/yellow]")
            return
        
        # Display results
        console.print(f"[green]Found {len(results)} matches:[/green]\n")
        
        for result in results[:args.limit or 20]:
            console.print(Panel(
                f"[cyan]{result['file']}:{result['line']}[/cyan]\n{result['content']}",
                border_style="blue"
            ))
    
    def cmd_analyze(self, args):
        """Analyze codebase with Grok-4"""
        console.print("[cyan]🧠 Analyzing codebase with Grok-4...[/cyan]\n")

        # Scan codebase
        structure = self.codebase.scan_codebase()

        # Build context
        context = f"""Codebase Analysis:
- Total files: {structure['stats']['total_files']}
- Total lines: {structure['stats']['total_lines']:,}
- File types: {', '.join(structure['stats']['by_extension'].keys())}

Key files:
"""

        # Add summaries of key files
        for file_path in structure['files'][:10]:
            summary = self.codebase.get_file_summary(file_path)
            context += f"\n{summary}\n"

        # Ask Grok-4 for analysis
        prompt = f"""{context}

Please analyze this codebase and provide:
1. Overall architecture and structure
2. Main components and their purposes
3. Potential improvements or issues
4. Code quality assessment"""

        result = self.chat(prompt, stream=False)

        if result["success"]:
            console.print("\n[green]📊 Analysis Results:[/green]\n")
            console.print(Markdown(result["content"]))

    def cmd_skill(self, args):
        """Skill management commands"""
        if not self.skill_manager:
            console.print("[red]Error: VAMS Skill Manager not available[/red]")
            console.print("[yellow]Install required: pip install sentence-transformers torch[/yellow]")
            return

        subcommand = args.subcommand

        if subcommand == 'list':
            self._skill_list(args)
        elif subcommand == 'show':
            self._skill_show(args)
        elif subcommand == 'stats':
            self._skill_stats(args)
        elif subcommand == 'last':
            self._skill_last(args)
        elif subcommand == 'accept':
            self._skill_accept(args)
        elif subcommand == 'reject':
            self._skill_reject(args)
        else:
            console.print(f"[red]Unknown skill subcommand: {subcommand}[/red]")
            console.print("[yellow]Available: list, show, stats, last, accept, reject[/yellow]")

    def _skill_list(self, args):
        """List all learned skills"""
        all_skills = self.skill_manager.list_skills()

        if not all_skills:
            console.print("[yellow]No skills learned yet[/yellow]")
            console.print("[dim]Skills are learned automatically from code generations[/dim]")
            return

        # Filter by domain if specified
        if args.domain:
            all_skills = [s for s in all_skills if s.get('domain') == args.domain]

        # Filter by vibe if specified
        if args.vibe:
            all_skills = [s for s in all_skills if s.get('vibe_mode') == args.vibe]

        # Sort by usage or date
        sort_key = 'usage_count' if args.sort == 'usage' else 'created_at'
        all_skills = sorted(all_skills, key=lambda s: s.get(sort_key, 0), reverse=True)

        # Limit results
        limit = args.limit or 20
        all_skills = all_skills[:limit]

        # Display as table
        table = Table(title=f"Learned Skills ({len(all_skills)} shown)", box=box.ROUNDED)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("Domain", style="magenta")
        table.add_column("Vibe", style="yellow")
        table.add_column("Usage", style="green")
        table.add_column("Success", style="blue")

        for skill in all_skills:
            skill_id_short = skill['skill_id'][:8]
            name_short = skill['name'][:40] + "..." if len(skill['name']) > 40 else skill['name']
            domain = skill.get('domain', 'general')
            vibe = skill.get('vibe_mode', 'creative')
            usage = str(skill.get('usage_count', 0))

            success_count = skill.get('success_count', 0)
            usage_count = skill.get('usage_count', 0)
            success_rate = f"{success_count}/{usage_count}" if usage_count > 0 else "-"

            table.add_row(skill_id_short, name_short, domain, vibe, usage, success_rate)

        console.print(table)

        # Show summary stats
        total_skills = len(self.skill_manager.list_skills())
        console.print(f"\n[dim]Total skills in memory: {total_skills}[/dim]")
        console.print(f"[dim]Use 'grokflow skill show <id>' to see full details[/dim]")

    def _skill_show(self, args):
        """Show full details of a specific skill"""
        if not args.skill_id:
            console.print("[red]Error: Skill ID required[/red]")
            console.print("[yellow]Usage: grokflow skill show <skill_id>[/yellow]")
            return

        # Find skill (support partial ID match)
        all_skills = self.skill_manager.list_skills()
        matching_skills = [s for s in all_skills if s['skill_id'].startswith(args.skill_id)]

        if not matching_skills:
            console.print(f"[red]Skill not found: {args.skill_id}[/red]")
            console.print("[yellow]Use 'grokflow skill list' to see all skills[/yellow]")
            return

        if len(matching_skills) > 1:
            console.print(f"[yellow]Multiple skills match '{args.skill_id}':[/yellow]")
            for skill in matching_skills:
                console.print(f"  • {skill['skill_id'][:8]}... - {skill['name']}")
            console.print("\n[yellow]Please provide more characters[/yellow]")
            return

        skill = matching_skills[0]

        # Display full skill details
        console.print(Panel.fit(
            f"[bold cyan]{skill['name']}[/bold cyan]\n"
            f"[dim]ID: {skill['skill_id']}[/dim]",
            border_style="cyan"
        ))

        # Metadata table
        table = Table(box=box.SIMPLE)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Description", skill.get('description', 'N/A'))
        table.add_row("Language", skill.get('language', 'python'))
        table.add_row("Domain", skill.get('domain', 'general'))
        table.add_row("Vibe Mode", skill.get('vibe_mode', 'creative'))
        table.add_row("Created", skill.get('created_at', 'Unknown'))
        table.add_row("Updated", skill.get('updated_at', 'Unknown'))

        # Usage stats
        usage_count = skill.get('usage_count', 0)
        success_count = skill.get('success_count', 0)
        success_rate = (success_count / usage_count * 100) if usage_count > 0 else 0

        table.add_row("Usage Count", str(usage_count))
        table.add_row("Success Count", str(success_count))
        table.add_row("Success Rate", f"{success_rate:.1f}%")

        # Tags
        tags = skill.get('tags', [])
        table.add_row("Tags", ", ".join(tags) if tags else "None")

        console.print(table)

        # Show code
        if skill.get('code'):
            console.print("\n[cyan]Code:[/cyan]")
            lang = skill.get('language', 'python')
            syntax = Syntax(skill['code'], lang, theme="monokai", line_numbers=True)
            console.print(syntax)

        # Show reasoning chain
        if skill.get('reasoning_chain'):
            console.print(f"\n[cyan]Reasoning:[/cyan]")
            console.print(f"[dim]{skill['reasoning_chain']}[/dim]")

    def _skill_stats(self, args):
        """Show VAMS skill statistics"""
        stats = self.skill_manager.get_all_stats()

        # Main stats table
        table = Table(title="VAMS Skill Memory Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Total Skills", str(stats['total_skills']))
        table.add_row("Capacity", f"{stats['capacity_used_pct']:.2f}% ({stats['capacity_used']}/{stats['capacity_max']})")
        table.add_row("VAMS Directory", str(stats['vams_dir']))

        # Domain breakdown
        if stats.get('by_domain'):
            domain_str = ", ".join([f"{k}({v})" for k, v in stats['by_domain'].items()])
            table.add_row("By Domain", domain_str)

        # Vibe breakdown
        if stats.get('by_vibe'):
            vibe_str = ", ".join([f"{k}({v})" for k, v in stats['by_vibe'].items()])
            table.add_row("By Vibe", vibe_str)

        # Language breakdown
        if stats.get('by_language'):
            lang_str = ", ".join([f"{k}({v})" for k, v in stats['by_language'].items()])
            table.add_row("By Language", lang_str)

        # Usage stats
        total_usage = sum(s.get('usage_count', 0) for s in self.skill_manager.list_skills())
        total_successes = sum(s.get('success_count', 0) for s in self.skill_manager.list_skills())
        overall_success_rate = (total_successes / total_usage * 100) if total_usage > 0 else 0

        table.add_row("Total Usage", str(total_usage))
        table.add_row("Total Successes", str(total_successes))
        table.add_row("Overall Success Rate", f"{overall_success_rate:.1f}%")

        console.print(table)

        # Top skills by usage
        all_skills = self.skill_manager.list_skills()
        if all_skills:
            top_skills = sorted(all_skills, key=lambda s: s.get('usage_count', 0), reverse=True)[:5]

            if any(s.get('usage_count', 0) > 0 for s in top_skills):
                console.print("\n[cyan]Top 5 Most Used Skills:[/cyan]")
                for i, skill in enumerate(top_skills, 1):
                    usage = skill.get('usage_count', 0)
                    if usage > 0:
                        success_count = skill.get('success_count', 0)
                        success_rate = (success_count / usage * 100) if usage > 0 else 0
                        console.print(f"  {i}. {skill['name'][:50]}... (used {usage}x, {success_rate:.0f}% success)")

    def _skill_last(self, args):
        """Show most recently learned skill"""
        all_skills = self.skill_manager.list_skills()

        if not all_skills:
            console.print("[yellow]No skills learned yet[/yellow]")
            console.print("[dim]Skills are learned automatically from code generations[/dim]")
            return

        # Sort by created_at to get most recent
        sorted_skills = sorted(all_skills, key=lambda s: s.get('created_at', ''), reverse=True)
        last_skill = sorted_skills[0]

        # Display full skill details in a panel
        console.print()
        console.print(Panel.fit(
            f"[bold cyan]Last Learned Pattern[/bold cyan]\n\n"
            f"[yellow]{last_skill['name']}[/yellow]\n"
            f"[dim]Learned: {last_skill.get('created_at', 'Unknown')}[/dim]\n"
            f"[dim]ID: {last_skill['skill_id'][:12]}...[/dim]",
            border_style="cyan"
        ))

        # Metadata table
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Property", style="cyan", width=15)
        table.add_column("Value", style="white")

        table.add_row("Description", last_skill.get('description', 'N/A')[:60] + "...")
        table.add_row("Domain", last_skill.get('domain', 'general').title())
        table.add_row("Language", last_skill.get('language', 'python'))
        table.add_row("Vibe Mode", last_skill.get('vibe_mode', 'creative').title())

        # Usage stats
        usage_count = last_skill.get('usage_count', 0)
        success_count = last_skill.get('success_count', 0)

        if usage_count > 0:
            success_rate = (success_count / usage_count * 100)
            table.add_row("Usage", f"{usage_count} times, {success_rate:.0f}% success")
        else:
            table.add_row("Usage", "[dim]Not used yet[/dim]")

        console.print(table)

        # Show code preview (first 10 lines)
        if last_skill.get('code'):
            console.print("\n[cyan]Code Preview:[/cyan]")
            code_lines = last_skill['code'].split('\n')[:10]
            preview = '\n'.join(code_lines)
            if len(last_skill['code'].split('\n')) > 10:
                preview += "\n..."

            lang = last_skill.get('language', 'python')
            syntax = Syntax(preview, lang, theme="monokai", line_numbers=True)
            console.print(syntax)

        # Quick actions
        console.print()
        console.print("[dim]Actions:[/dim]")
        console.print(f"  [green]✓[/green] Accept:  grokflow skill accept {last_skill['skill_id'][:8]}")
        console.print(f"  [red]✗[/red] Reject:  grokflow skill reject {last_skill['skill_id'][:8]}")
        console.print(f"  [cyan]👁[/cyan]  View:    grokflow skill show {last_skill['skill_id'][:8]}")
        console.print()

    def _skill_accept(self, args):
        """Mark skill as accepted (explicit Hebbian feedback)"""
        if not args.skill_id:
            console.print("[red]Error: Skill ID required[/red]")
            console.print("[yellow]Usage: grokflow skill accept <skill_id>[/yellow]")
            return

        # Find skill
        all_skills = self.skill_manager.list_skills()
        matching_skills = [s for s in all_skills if s['skill_id'].startswith(args.skill_id)]

        if not matching_skills:
            console.print(f"[red]Skill not found: {args.skill_id}[/red]")
            return

        if len(matching_skills) > 1:
            console.print(f"[yellow]Multiple skills match '{args.skill_id}':[/yellow]")
            for skill in matching_skills:
                console.print(f"  • {skill['skill_id'][:8]}... - {skill['name']}")
            return

        skill = matching_skills[0]
        skill_id = skill['skill_id']

        # Record positive feedback
        try:
            self.skill_manager.record_usage(
                skill_id=skill_id,
                success=True,
                context={"feedback_type": "explicit_accept", "source": "cli"}
            )
            self.skill_manager.save()

            # Get updated stats
            stats = self.skill_manager.get_skill_stats(skill_id)

            console.print(f"[green]✅ Skill accepted (Hebbian strengthening)[/green]")
            console.print(f"[dim]{skill['name']}[/dim]")
            console.print(f"[dim]Usage: {stats['usage_count']} times, {stats['success_rate']:.0%} success rate[/dim]")

        except Exception as e:
            console.print(f"[red]Error recording feedback: {str(e)}[/red]")

    def _skill_reject(self, args):
        """Mark skill as rejected (explicit anti-Hebbian feedback)"""
        if not args.skill_id:
            console.print("[red]Error: Skill ID required[/red]")
            console.print("[yellow]Usage: grokflow skill reject <skill_id>[/yellow]")
            return

        # Find skill
        all_skills = self.skill_manager.list_skills()
        matching_skills = [s for s in all_skills if s['skill_id'].startswith(args.skill_id)]

        if not matching_skills:
            console.print(f"[red]Skill not found: {args.skill_id}[/red]")
            return

        if len(matching_skills) > 1:
            console.print(f"[yellow]Multiple skills match '{args.skill_id}':[/yellow]")
            for skill in matching_skills:
                console.print(f"  • {skill['skill_id'][:8]}... - {skill['name']}")
            return

        skill = matching_skills[0]
        skill_id = skill['skill_id']

        # Record negative feedback
        try:
            self.skill_manager.record_usage(
                skill_id=skill_id,
                success=False,
                context={"feedback_type": "explicit_reject", "source": "cli"}
            )
            self.skill_manager.save()

            # Get updated stats
            stats = self.skill_manager.get_skill_stats(skill_id)

            console.print(f"[yellow]⚠ Skill rejected (anti-Hebbian weakening)[/yellow]")
            console.print(f"[dim]{skill['name']}[/dim]")
            console.print(f"[dim]Usage: {stats['usage_count']} times, {stats['success_rate']:.0%} success rate[/dim]")

        except Exception as e:
            console.print(f"[red]Error recording feedback: {str(e)}[/red]")

    def cmd_constraint(self, args):
        """Constraint management commands"""
        if not self.constraint_manager:
            console.print("[red]Error: Constraint Manager not available[/red]")
            return

        subcommand = args.subcommand

        if subcommand == 'add':
            self._constraint_add(args)
        elif subcommand == 'list':
            self._constraint_list(args)
        elif subcommand == 'show':
            self._constraint_show(args)
        elif subcommand == 'remove':
            self._constraint_remove(args)
        elif subcommand == 'disable':
            self._constraint_disable(args)
        elif subcommand == 'enable':
            self._constraint_enable(args)
        elif subcommand == 'stats':
            self._constraint_stats(args)
        else:
            console.print(f"[red]Unknown constraint subcommand: {subcommand}[/red]")
            console.print("[yellow]Available: add, list, show, remove, disable, enable, stats[/yellow]")

    def _constraint_add(self, args):
        """Add a new constraint"""
        description = args.description
        keywords = [k.strip() for k in args.keywords.split(',')]
        action = args.action or 'warn'
        message = args.message

        try:
            constraint_id = self.constraint_manager.add_constraint(
                description=description,
                trigger_keywords=keywords,
                enforcement_action=action,
                enforcement_message=message
            )

            console.print(f"[green]✅ Constraint added[/green]")
            console.print(f"[dim]ID: {constraint_id}[/dim]")
            console.print(f"[dim]Description: {description}[/dim]")
            console.print(f"[dim]Keywords: {', '.join(keywords)}[/dim]")
            console.print(f"[dim]Action: {action}[/dim]")

        except Exception as e:
            console.print(f"[red]Error adding constraint: {str(e)}[/red]")

    def _constraint_list(self, args):
        """List all constraints"""
        enabled_only = args.enabled if hasattr(args, 'enabled') else False
        constraints = self.constraint_manager.list_constraints(enabled_only=enabled_only)

        if not constraints:
            console.print("[yellow]No constraints defined[/yellow]")
            console.print("[dim]Add constraints with: grokflow constraint add[/dim]")
            return

        # Display as table
        table = Table(title=f"Constraints ({len(constraints)} total)", box=box.ROUNDED)
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Action", style="yellow")
        table.add_column("Keywords", style="magenta")
        table.add_column("Triggered", style="green")
        table.add_column("Status", style="blue")

        for constraint in constraints:
            constraint_id = constraint['constraint_id'][:8]
            desc = constraint['description'][:40] + "..." if len(constraint['description']) > 40 else constraint['description']
            action = constraint['enforcement_action']
            keywords = ', '.join(constraint['trigger_keywords'][:3])
            if len(constraint['trigger_keywords']) > 3:
                keywords += "..."
            triggered = str(constraint.get('triggered_count', 0))
            status = "✓" if constraint.get('enabled', True) else "[dim]disabled[/dim]"

            table.add_row(constraint_id, desc, action, keywords, triggered, status)

        console.print(table)
        console.print(f"\n[dim]Use 'grokflow constraint show <id>' for details[/dim]")

    def _constraint_show(self, args):
        """Show full details of a constraint"""
        if not args.constraint_id:
            console.print("[red]Error: Constraint ID required[/red]")
            console.print("[yellow]Usage: grokflow constraint show <id>[/yellow]")
            return

        constraint = self.constraint_manager.get_constraint(args.constraint_id)

        if not constraint:
            console.print(f"[red]Constraint not found: {args.constraint_id}[/red]")
            return

        # Display full details
        console.print(Panel.fit(
            f"[bold cyan]{constraint['description']}[/bold cyan]\n"
            f"[dim]ID: {constraint['constraint_id']}[/dim]",
            border_style="cyan"
        ))

        # Metadata table
        table = Table(box=box.SIMPLE)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Enforcement Action", constraint['enforcement_action'])
        table.add_row("Enforcement Message", constraint['enforcement_message'])
        table.add_row("Trigger Keywords", ", ".join(constraint['trigger_keywords']))
        table.add_row("Created", constraint.get('created', 'Unknown'))
        table.add_row("Triggered Count", str(constraint.get('triggered_count', 0)))
        table.add_row("Last Triggered", constraint.get('last_triggered', 'Never'))
        table.add_row("Enabled", "Yes" if constraint.get('enabled', True) else "No")

        console.print(table)

    def _constraint_remove(self, args):
        """Remove a constraint"""
        if not args.constraint_id:
            console.print("[red]Error: Constraint ID required[/red]")
            console.print("[yellow]Usage: grokflow constraint remove <id>[/yellow]")
            return

        if self.constraint_manager.remove_constraint(args.constraint_id):
            console.print(f"[green]✅ Constraint removed: {args.constraint_id}[/green]")
        else:
            console.print(f"[red]Constraint not found: {args.constraint_id}[/red]")

    def _constraint_disable(self, args):
        """Disable a constraint"""
        if not args.constraint_id:
            console.print("[red]Error: Constraint ID required[/red]")
            console.print("[yellow]Usage: grokflow constraint disable <id>[/yellow]")
            return

        if self.constraint_manager.disable_constraint(args.constraint_id):
            console.print(f"[yellow]⚠ Constraint disabled: {args.constraint_id}[/yellow]")
        else:
            console.print(f"[red]Constraint not found: {args.constraint_id}[/red]")

    def _constraint_enable(self, args):
        """Enable a constraint"""
        if not args.constraint_id:
            console.print("[red]Error: Constraint ID required[/red]")
            console.print("[yellow]Usage: grokflow constraint enable <id>[/yellow]")
            return

        if self.constraint_manager.enable_constraint(args.constraint_id):
            console.print(f"[green]✅ Constraint enabled: {args.constraint_id}[/green]")
        else:
            console.print(f"[red]Constraint not found: {args.constraint_id}[/red]")

    def _constraint_stats(self, args):
        """Show constraint statistics"""
        stats = self.constraint_manager.get_stats()

        table = Table(title="Constraint System Statistics", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Total Constraints", str(stats['total_constraints']))
        table.add_row("Enabled Constraints", str(stats['enabled_constraints']))
        table.add_row("Total Triggers", str(stats['total_triggers']))

        console.print(table)

        # Show most triggered constraint
        if stats.get('most_triggered'):
            console.print("\n[cyan]Most Triggered Constraint:[/cyan]")
            mt = stats['most_triggered']
            console.print(f"  {mt['description']}")
            console.print(f"  [dim]ID: {mt['constraint_id']}, Triggered: {mt['triggered_count']} times[/dim]")

    def show_metrics(self, usage: Dict):
        """Display token usage metrics"""
        table = Table(box=box.SIMPLE)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="yellow")
        
        table.add_row("Reasoning Tokens", f"{usage['reasoning_tokens']:,}")
        table.add_row("Completion Tokens", f"{usage['completion_tokens']:,}")
        table.add_row("Total Tokens", f"{usage['total_tokens']:,}")
        
        if usage['total_tokens'] > 0:
            ratio = usage['reasoning_tokens'] / usage['total_tokens'] * 100
            table.add_row("Reasoning Ratio", f"{ratio:.1f}%")
        
        console.print("\n", table)
    
    def show_help(self):
        """Show help message"""
        help_text = """
# GrokFlow CLI Commands

## Chat Commands
- `exit` - Exit interactive chat
- `clear` - Clear screen
- `/help` - Show this help

## CLI Commands
- `grokflow chat` - Interactive chat mode
- `grokflow generate <prompt>` - Generate code
- `grokflow debug <file>` - Debug code
- `grokflow optimize <file>` - Optimize code
- `grokflow vibe [mode]` - Set/view vibe mode
- `grokflow context [text]` - Set/view project context
- `grokflow stats` - Show session statistics
- `grokflow history` - Show conversation history
- `grokflow clear` - Clear session

## Vibe Modes
- `creative` - Maximum innovation (temp: 0.7)
- `focused` - Task-oriented (temp: 0.3)
- `analytical` - Deep reasoning (temp: 0.3)
- `rapid` - Speed-first (temp: 0.5)
        """
        console.print(Markdown(help_text))
    
    def handle_command(self, cmd: str):
        """Handle slash commands in chat"""
        parts = cmd[1:].split()
        command = parts[0] if parts else ""
        
        if command == "vibe" and len(parts) > 1:
            self.session["vibe_mode"] = parts[1]
            self.save_session()
            console.print(f"[green]✓ Vibe mode: {parts[1]}[/green]")
        elif command == "stats":
            self.cmd_stats(None)
        elif command == "clear":
            self.cmd_clear(None)
        else:
            console.print(f"[red]Unknown command: {command}[/red]")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="🌊 GrokFlow - Ultimate Vibe Coding with Grok-4-fast",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Global flags
    parser.add_argument('--no-vams', action='store_true', help='Disable VAMS skill memory for this request')

    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Interactive chat mode')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate code')
    gen_parser.add_argument('prompt', nargs='?', help='Code description')
    gen_parser.add_argument('-f', '--file', help='Read prompt from file')
    gen_parser.add_argument('-o', '--output', help='Output file')
    
    # Debug command
    debug_parser = subparsers.add_parser('debug', help='Debug code')
    debug_parser.add_argument('-f', '--file', help='Code file to debug')
    debug_parser.add_argument('-e', '--error', help='Error message')
    
    # Optimize command
    opt_parser = subparsers.add_parser('optimize', help='Optimize code')
    opt_parser.add_argument('-f', '--file', help='Code file to optimize')
    
    # Vibe command
    vibe_parser = subparsers.add_parser('vibe', help='Set vibe mode')
    vibe_parser.add_argument('mode', nargs='?', choices=['creative', 'focused', 'analytical', 'rapid'])
    
    # Context command
    ctx_parser = subparsers.add_parser('context', help='Set project context')
    ctx_parser.add_argument('text', nargs='?', help='Project context')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    
    # History command
    hist_parser = subparsers.add_parser('history', help='Show history')
    hist_parser.add_argument('-n', '--limit', type=int, help='Number of entries')
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear session')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan codebase')
    scan_parser.add_argument('-d', '--depth', type=int, help='Max depth to scan')
    scan_parser.add_argument('-t', '--tree', action='store_true', help='Show tree view')
    
    # Read command
    read_parser = subparsers.add_parser('read', help='Read file')
    read_parser.add_argument('file', help='File to read')
    read_parser.add_argument('-a', '--analyze', action='store_true', help='Analyze Python files')
    
    # Edit command
    edit_parser = subparsers.add_parser('edit', help='Edit file with Grok-4')
    edit_parser.add_argument('file', help='File to edit')
    edit_parser.add_argument('-i', '--instruction', help='Edit instructions')
    edit_parser.add_argument('-c', '--create', action='store_true', help='Create if not exists')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run file')
    run_parser.add_argument('file', help='File to run')
    run_parser.add_argument('-a', '--args', help='Arguments to pass')
    run_parser.add_argument('-d', '--debug', action='store_true', help='Auto-debug on error')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search codebase')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('-p', '--pattern', help='File pattern (e.g., *.py)')
    search_parser.add_argument('-n', '--limit', type=int, help='Max results')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze codebase with Grok-4')

    # Skill command (Phase D1: CLI commands for skill management)
    skill_parser = subparsers.add_parser('skill', help='Manage learned skills')
    skill_subparsers = skill_parser.add_subparsers(dest='subcommand', help='Skill subcommands')

    # skill list
    skill_list_parser = skill_subparsers.add_parser('list', help='List learned skills')
    skill_list_parser.add_argument('-d', '--domain', help='Filter by domain (api, testing, async, database, validation)')
    skill_list_parser.add_argument('-v', '--vibe', help='Filter by vibe (creative, focused, analytical, rapid)')
    skill_list_parser.add_argument('-s', '--sort', choices=['usage', 'date'], default='usage', help='Sort by usage or date')
    skill_list_parser.add_argument('-n', '--limit', type=int, help='Limit results (default: 20)')

    # skill show
    skill_show_parser = skill_subparsers.add_parser('show', help='Show skill details')
    skill_show_parser.add_argument('skill_id', nargs='?', help='Skill ID (supports partial match)')

    # skill stats
    skill_stats_parser = skill_subparsers.add_parser('stats', help='Show VAMS statistics')

    # skill last
    skill_last_parser = skill_subparsers.add_parser('last', help='Show most recently learned skill')

    # skill accept
    skill_accept_parser = skill_subparsers.add_parser('accept', help='Accept skill (Hebbian feedback)')
    skill_accept_parser.add_argument('skill_id', nargs='?', help='Skill ID (supports partial match)')

    # skill reject
    skill_reject_parser = skill_subparsers.add_parser('reject', help='Reject skill (anti-Hebbian feedback)')
    skill_reject_parser.add_argument('skill_id', nargs='?', help='Skill ID (supports partial match)')

    # Constraint command (Phase 1: Constraint System)
    constraint_parser = subparsers.add_parser('constraint', help='Manage behavior constraints')
    constraint_subparsers = constraint_parser.add_subparsers(dest='subcommand', help='Constraint subcommands')

    # constraint add
    constraint_add_parser = constraint_subparsers.add_parser('add', help='Add constraint')
    constraint_add_parser.add_argument('description', help='Constraint description')
    constraint_add_parser.add_argument('-k', '--keywords', required=True, help='Comma-separated trigger keywords')
    constraint_add_parser.add_argument('-a', '--action', choices=['warn', 'block', 'require_action'], default='warn', help='Enforcement action (default: warn)')
    constraint_add_parser.add_argument('-m', '--message', help='Custom enforcement message')

    # constraint list
    constraint_list_parser = constraint_subparsers.add_parser('list', help='List all constraints')
    constraint_list_parser.add_argument('-e', '--enabled', action='store_true', help='Show only enabled constraints')

    # constraint show
    constraint_show_parser = constraint_subparsers.add_parser('show', help='Show constraint details')
    constraint_show_parser.add_argument('constraint_id', nargs='?', help='Constraint ID (supports partial match)')

    # constraint remove
    constraint_remove_parser = constraint_subparsers.add_parser('remove', help='Remove constraint')
    constraint_remove_parser.add_argument('constraint_id', nargs='?', help='Constraint ID (supports partial match)')

    # constraint disable
    constraint_disable_parser = constraint_subparsers.add_parser('disable', help='Disable constraint')
    constraint_disable_parser.add_argument('constraint_id', nargs='?', help='Constraint ID (supports partial match)')

    # constraint enable
    constraint_enable_parser = constraint_subparsers.add_parser('enable', help='Enable constraint')
    constraint_enable_parser.add_argument('constraint_id', nargs='?', help='Constraint ID (supports partial match)')

    # constraint stats
    constraint_stats_parser = constraint_subparsers.add_parser('stats', help='Show constraint statistics')

    args = parser.parse_args()

    # Show help if no command
    if not args.command:
        parser.print_help()
        return

    # Initialize CLI
    cli = GrokFlowCLI()

    # Disable VAMS if --no-vams flag is set
    if args.no_vams and cli.skill_manager:
        console.print("[yellow]⚠ VAMS disabled for this request (--no-vams flag)[/yellow]")
        cli.skill_manager = None  # Temporarily disable

    # Route to command
    command_map = {
        'chat': cli.cmd_chat,
        'generate': cli.cmd_generate,
        'debug': cli.cmd_debug,
        'optimize': cli.cmd_optimize,
        'vibe': cli.cmd_vibe,
        'context': cli.cmd_context,
        'stats': cli.cmd_stats,
        'history': cli.cmd_history,
        'clear': cli.cmd_clear,
        'scan': cli.cmd_scan,
        'read': cli.cmd_read,
        'edit': cli.cmd_edit,
        'run': cli.cmd_run,
        'search': cli.cmd_search,
        'analyze': cli.cmd_analyze,
        'skill': cli.cmd_skill,
        'constraint': cli.cmd_constraint
    }
    
    if args.command in command_map:
        command_map[args.command](args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
