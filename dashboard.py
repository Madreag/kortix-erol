#!/usr/bin/env python3
# Run with: python3 dashboard.py  OR  ./dashboard.py
"""
Kortix Suna - Ultimate Terminal Dashboard

A beautiful, feature-rich terminal dashboard with:
- Live service status with uptime tracking
- Daytona sandbox visualization with usage bars
- System resource monitoring (CPU, RAM, Disk)
- Real-time log streaming with error highlighting
- Animated indicators and progress bars

Run: python scripts/dashboard.py
"""

import os
import sys
import subprocess
import socket
import asyncio
import psutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
import time
import re

# Check and install dependencies
def check_deps():
    required = ["textual", "rich", "psutil"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Installing: {', '.join(missing)}...")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing + ["--quiet"])
    return True

check_deps()

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer, Grid
from textual.widgets import Header, Footer, Static, Button, Log, ProgressBar, Label, Rule, Sparkline, DataTable
from textual.reactive import reactive
from textual.timer import Timer
from textual import work
from textual.css.query import NoMatches
from textual.widget import Widget

from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.console import Console, Group
from rich.style import Style
from rich.align import Align
from rich.box import ROUNDED, DOUBLE, HEAVY, SIMPLE
from rich.progress import BarColumn, Progress, TextColumn
from rich.columns import Columns

# Configuration
PROJECT_DIR = Path(__file__).parent
BACKEND_DIR = PROJECT_DIR / "backend"
FRONTEND_DIR = PROJECT_DIR / "apps" / "frontend"
LOG_DIR = PROJECT_DIR / "logs"
PID_DIR = PROJECT_DIR / ".pids"
SCRIPTS_DIR = PROJECT_DIR / "scripts"

# Get external IP for remote access
def get_external_ip() -> str:
    """Get the machine's external IP address."""
    try:
        result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            return result.stdout.strip().split()[0]
    except Exception:
        pass
    return ""

EXTERNAL_IP = get_external_ip()

# Ensure directories exist
LOG_DIR.mkdir(exist_ok=True)
PID_DIR.mkdir(exist_ok=True)

# Daytona Free Tier Limits
DAYTONA_LIMITS = {
    "disk_gb": 30,
    "memory_gb": 10,
    "sandboxes": 5,
    "compute_credits": 200,
}

# Service definitions
SERVICES = {
    "redis": {
        "name": "Redis",
        "icon": "🔴",
        "port": 6379,
        "pid_file": "redis.pid",
        "log_file": "redis.log",
        "description": "Cache & Pub/Sub",
        "color": "red",
    },
    "backend": {
        "name": "Backend",
        "icon": "⚡",
        "port": 8000,
        "pid_file": "backend.pid",
        "log_file": "backend.log",
        "description": "FastAPI Server",
        "color": "green",
        "url": "http://localhost:8000",
        "external_url": f"http://{EXTERNAL_IP}:8000" if EXTERNAL_IP else None,
    },
    "frontend": {
        "name": "Frontend",
        "icon": "🌐",
        "port": 3000,
        "pid_file": "frontend.pid",
        "log_file": "frontend.log",
        "description": "Next.js Web UI",
        "color": "blue",
        "url": "http://localhost:3000",
        "external_url": f"http://{EXTERNAL_IP}:3000" if EXTERNAL_IP else None,
    },
}

# Track service start times for uptime
service_start_times: Dict[str, Optional[datetime]] = {k: None for k in SERVICES}

@dataclass
class SandboxInfo:
    """Information about a Daytona sandbox."""
    id: str
    state: str
    created: str = ""
    cpu: int = 1
    memory: int = 2
    disk: int = 6


def check_port(port: int, host: str = "localhost", timeout: float = 0.3) -> bool:
    """Check if a port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def get_pid(service_id: str) -> Optional[int]:
    """Get PID from pid file."""
    pid_file = PID_DIR / SERVICES[service_id]["pid_file"]
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError):
            pass
    return None


def get_log_tail(service_id: str, lines: int = 30) -> str:
    """Get last N lines of log file."""
    log_file = LOG_DIR / SERVICES[service_id]["log_file"]
    if log_file.exists():
        try:
            with open(log_file, "r") as f:
                all_lines = f.readlines()
                return "".join(all_lines[-lines:])
        except Exception:
            pass
    return "No logs available"


def get_recent_errors(lines: int = 5) -> List[Tuple[str, str]]:
    """Get recent errors from all log files."""
    errors = []
    for service_id, service in SERVICES.items():
        log_file = LOG_DIR / service["log_file"]
        if log_file.exists():
            try:
                with open(log_file, "r") as f:
                    for line in f.readlines()[-100:]:
                        if "ERROR" in line.upper() or "EXCEPTION" in line.upper():
                            errors.append((service_id, line.strip()[:80]))
            except Exception:
                pass
    return errors[-lines:]


def get_sandboxes() -> Tuple[List[SandboxInfo], Dict[str, Any]]:
    """Get detailed sandbox information from Daytona."""
    sandboxes = []
    stats = {"total": 0, "running": 0, "stopped": 0, "archived": 0, "disk_used": 0, "memory_used": 0}
    
    try:
        result = subprocess.run(
            ["uv", "run", "python", "-c", """
import os
import json
from dotenv import load_dotenv
load_dotenv()
from daytona_sdk import Daytona, DaytonaConfig
config = DaytonaConfig(api_key=os.environ.get('DAYTONA_API_KEY'), api_url=os.environ.get('DAYTONA_SERVER_URL'), target=os.environ.get('DAYTONA_TARGET'))
daytona = Daytona(config)
sandboxes = daytona.list().items
output = []
for sb in sandboxes:
    output.append({
        "id": sb.id[:12] if sb.id else "unknown",
        "state": str(sb.state.value) if hasattr(sb.state, 'value') else str(sb.state),
    })
print(json.dumps(output))
"""],
            cwd=str(BACKEND_DIR),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout.strip())
            for item in data:
                sb = SandboxInfo(
                    id=item["id"],
                    state=item["state"],
                )
                sandboxes.append(sb)
                stats["total"] += 1
                state_lower = item["state"].lower()
                if "started" in state_lower or "running" in state_lower:
                    stats["running"] += 1
                    stats["memory_used"] += 2  # 2GB per running sandbox
                elif "stopped" in state_lower:
                    stats["stopped"] += 1
                elif "archived" in state_lower:
                    stats["archived"] += 1
                stats["disk_used"] += 6  # 6GB per sandbox
    except Exception as e:
        pass
    
    return sandboxes, stats


def get_system_stats() -> Dict[str, float]:
    """Get system resource usage."""
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "memory_used_gb": psutil.virtual_memory().used / (1024**3),
        "memory_total_gb": psutil.virtual_memory().total / (1024**3),
        "disk_percent": psutil.disk_usage("/").percent,
        "disk_used_gb": psutil.disk_usage("/").used / (1024**3),
        "disk_total_gb": psutil.disk_usage("/").total / (1024**3),
    }


def format_uptime(start_time: Optional[datetime]) -> str:
    """Format uptime as human readable string."""
    if not start_time:
        return "—"
    delta = datetime.now() - start_time
    if delta.days > 0:
        return f"{delta.days}d {delta.seconds // 3600}h"
    elif delta.seconds >= 3600:
        return f"{delta.seconds // 3600}h {(delta.seconds % 3600) // 60}m"
    elif delta.seconds >= 60:
        return f"{delta.seconds // 60}m {delta.seconds % 60}s"
    else:
        return f"{delta.seconds}s"


CSS = """
Screen {
    background: #0a0e17;
}

Header {
    background: #1a1f2e;
    color: #e2e8f0;
}

Footer {
    background: #1a1f2e;
}

#main-grid {
    layout: grid;
    grid-size: 2 2;
    grid-columns: 1fr 1fr;
    grid-rows: 1fr 1fr;
    padding: 1;
    height: 100%;
}

.panel {
    background: #141925;
    border: solid #2d3748;
    padding: 0 1;
    margin: 0;
}

.panel-title {
    text-style: bold;
    color: #e2e8f0;
    margin-bottom: 0;
}

#services-panel {
    row-span: 1;
}

#daytona-panel {
    row-span: 1;
}

#logs-panel {
    column-span: 1;
}

#logs-panel Horizontal {
    height: 3;
    margin-bottom: 0;
}

#system-panel {
    column-span: 1;
    overflow: hidden;
    padding: 0;
}

.service-row {
    height: 2;
    margin-bottom: 0;
    padding: 0 1;
    background: #1a1f2e;
}

.service-row.running {
    background: #0f2d1f;
    border-left: thick #22c55e;
}

.service-row.stopped {
    background: #2d1f1f;
    border-left: thick #ef4444;
}

.service-row.starting {
    background: #2d2a1f;
    border-left: thick #f59e0b;
}

.progress-bar {
    height: 1;
    margin: 0;
}

.sandbox-item {
    height: 2;
    padding: 0 1;
    margin-bottom: 0;
}

.sandbox-running {
    color: #22c55e;
}

.sandbox-stopped {
    color: #f59e0b;
}

.sandbox-archived {
    color: #64748b;
}

#action-bar {
    height: 3;
    background: #1a1f2e;
    border: solid #2d3748;
    padding: 0 1;
    dock: bottom;
}

.action-btn {
    margin: 0;
    width: 30%;
    height: 3;
}

.btn-start { background: #22c55e; color: #000; }
.btn-stop { background: #ef4444; color: #fff; }
.btn-restart { background: #f59e0b; color: #000; }
.btn-cleanup { background: #8b5cf6; color: #fff; }
.btn-cache { background: #06b6d4; color: #000; }
.btn-refresh { background: #3b82f6; color: #fff; }

Button:focus {
    text-style: bold reverse;
    border: tall white;
}

Button:hover {
    text-style: bold;
}

Log {
    background: #0a0e17;
    color: #94a3b8;
    height: 100%;
}

DataTable {
    background: #141925;
    height: auto;
}

DataTable > .datatable--header {
    background: #1a1f2e;
    color: #e2e8f0;
}

DataTable > .datatable--cursor {
    background: #2d3748;
}

.stat-value {
    text-style: bold;
    color: #3b82f6;
}

.stat-label {
    color: #64748b;
}

.usage-good { color: #22c55e; }
.usage-warning { color: #f59e0b; }
.usage-critical { color: #ef4444; }

#status-line {
    height: 1;
    background: #1a1f2e;
    color: #64748b;
    padding: 0 2;
    dock: bottom;
}

.spinner {
    color: #3b82f6;
}

Horizontal {
    height: auto;
    width: 100%;
}

#system-panel Horizontal {
    height: 3;
    margin-bottom: 0;
}

"""


class UsageBar(Static):
    """A visual usage bar with percentage."""
    
    can_focus = False
    
    value = reactive(0.0)
    max_value = reactive(100.0)
    label = reactive("")
    
    def __init__(self, label: str = "", value: float = 0, max_value: float = 100, unit: str = "", **kwargs):
        super().__init__(**kwargs)
        self.label = label
        self.value = value
        self.max_value = max_value
        self.unit = unit
    
    def render(self) -> Text:
        pct = (self.value / self.max_value * 100) if self.max_value > 0 else 0
        bar_width = 20
        filled = int(bar_width * pct / 100)
        
        # Color based on usage
        if pct < 60:
            color = "green"
            bar_char = "█"
        elif pct < 80:
            color = "yellow"
            bar_char = "█"
        else:
            color = "red"
            bar_char = "█"
        
        bar = f"[{color}]{bar_char * filled}[/][dim]{'░' * (bar_width - filled)}[/]"
        
        text = Text()
        text.append(f"{self.label:12} ", style="dim")
        text.append_text(Text.from_markup(bar))
        text.append(f" {self.value:.1f}/{self.max_value:.0f}{self.unit} ", style="white")
        text.append(f"({pct:.0f}%)", style=color)
        
        return text
    
    def update_value(self, value: float, max_value: Optional[float] = None):
        self.value = value
        if max_value is not None:
            self.max_value = max_value
        self.refresh()


class ServiceStatus(Static):
    """Service status display with uptime."""
    
    can_focus = False
    
    def __init__(self, service_id: str, **kwargs):
        super().__init__(**kwargs)
        self.service_id = service_id
        self.service = SERVICES[service_id]
    
    def render(self) -> Text:
        port_open = check_port(self.service["port"])
        pid = get_pid(self.service_id)
        
        # Track uptime
        global service_start_times
        if port_open:
            if service_start_times[self.service_id] is None:
                service_start_times[self.service_id] = datetime.now()
            status_icon = "●"
            status_color = "green"
            status_text = "RUNNING"
            self.remove_class("stopped", "starting")
            self.add_class("running")
        elif pid:
            status_icon = "◐"
            status_color = "yellow"
            status_text = "STARTING"
            self.remove_class("running", "stopped")
            self.add_class("starting")
        else:
            service_start_times[self.service_id] = None
            status_icon = "○"
            status_color = "red"
            status_text = "STOPPED"
            self.remove_class("running", "starting")
            self.add_class("stopped")
        
        uptime = format_uptime(service_start_times[self.service_id])
        
        text = Text()
        text.append(f" {self.service['icon']} ", style="bold")
        text.append(f"{self.service['name']:10}", style="bold white")
        text.append(f" {status_icon} ", style=status_color)
        text.append(f"{status_text:10}", style=f"bold {status_color}")
        text.append(f"│ ", style="dim")
        text.append(f":{self.service['port']}", style="cyan")
        text.append(f"  ⏱ {uptime:>8}", style="dim")
        if pid:
            text.append(f"  PID:{pid}", style="dim")
        
        return text


class SandboxList(Static):
    """Display list of sandboxes with visual states."""
    
    can_focus = False
    
    sandboxes: List[SandboxInfo] = []
    stats: Dict[str, Any] = {}
    
    def update_sandboxes(self, sandboxes: List[SandboxInfo], stats: Dict[str, Any]):
        self.sandboxes = sandboxes
        self.stats = stats
        self.refresh()
    
    def render(self) -> Text:
        text = Text()
        
        if not self.sandboxes:
            text.append("  No sandboxes found\n", style="dim italic")
            return text
        
        # Group by state
        running = [s for s in self.sandboxes if "started" in s.state.lower() or "running" in s.state.lower()]
        stopped = [s for s in self.sandboxes if "stopped" in s.state.lower()]
        archived = [s for s in self.sandboxes if "archived" in s.state.lower()]
        other = [s for s in self.sandboxes if s not in running + stopped + archived]
        
        # Running sandboxes with animation
        for sb in running:
            text.append("  ▶ ", style="bold green")
            text.append(f"{sb.id} ", style="green")
            text.append("RUNNING", style="bold green")
            text.append(f" (2GB RAM, 6GB disk)\n", style="dim")
        
        # Stopped
        for sb in stopped:
            text.append("  ⏸ ", style="yellow")
            text.append(f"{sb.id} ", style="yellow")
            text.append("STOPPED\n", style="yellow")
        
        # Archived
        for sb in archived:
            text.append("  📦 ", style="dim")
            text.append(f"{sb.id} ", style="dim")
            text.append("ARCHIVED\n", style="dim")
        
        # Other states
        for sb in other:
            text.append(f"  ? {sb.id} {sb.state}\n", style="dim")
        
        return text


class LogViewer(Log):
    """Enhanced log viewer with syntax highlighting."""
    
    can_focus = False  # Prevent focus from getting stuck on logs
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs, highlight=True)
        self.current_service = "backend"
    
    def set_service(self, service_id: str) -> None:
        self.current_service = service_id
        self.clear()
        self.refresh_logs()
    
    def refresh_logs(self) -> None:
        logs = get_log_tail(self.current_service, lines=50)
        self.clear()
        for line in logs.split("\n"):
            if line.strip():
                self.write_line(line)
    
    def _style_log_line(self, line: str) -> Text:
        """Apply syntax highlighting to log line."""
        text = Text()
        
        # Timestamp pattern
        timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})', line)
        if timestamp_match:
            text.append(timestamp_match.group(1) + " ", style="dim cyan")
            line = line[len(timestamp_match.group(0)):]
        
        # Color based on level
        line_upper = line.upper()
        if "ERROR" in line_upper or "EXCEPTION" in line_upper or "CRITICAL" in line_upper:
            text.append(line, style="bold red")
        elif "WARNING" in line_upper or "WARN" in line_upper:
            text.append(line, style="yellow")
        elif "INFO" in line_upper:
            text.append(line, style="green")
        elif "DEBUG" in line_upper:
            text.append(line, style="dim")
        else:
            text.append(line, style="white")
        
        return text


class SunaDashboard(App):
    """Kortix Suna Ultimate Terminal Dashboard."""
    
    CSS = CSS
    TITLE = "🚀 Kortix Suna Dashboard"
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "start_all", "Start"),
        ("x", "stop_all", "Stop"),
        ("r", "restart_all", "Restart"),
        ("c", "cleanup", "Cleanup"),
        ("f", "clear_cache", "Flush"),
        ("1", "log_redis", "Redis Log"),
        ("2", "log_backend", "Backend Log"),
        ("3", "log_frontend", "Frontend Log"),
        ("space", "refresh", "Refresh"),
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Prev"),
        ("up", "focus_previous", "Up"),
        ("down", "focus_next", "Down"),
        ("left", "focus_previous", "Left"),
        ("right", "focus_next", "Right"),
        ("enter", "select_focused", "Select"),
    ]
    
    current_log = reactive("backend")
    refresh_count = reactive(0)
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with Grid(id="main-grid"):
            # Services Panel
            with Vertical(id="services-panel", classes="panel"):
                yield Static(Text("📊 SERVICES", style="bold white"), classes="panel-title")
                for service_id in SERVICES:
                    yield ServiceStatus(service_id, classes="service-row")
                yield Static("", id="services-spacer")
                
                # Quick Stats
                yield Static(Text("\n💻 SYSTEM", style="bold white"))
                yield UsageBar("CPU", 0, 100, "%", id="cpu-bar", classes="progress-bar")
                yield UsageBar("Memory", 0, 100, "%", id="mem-bar", classes="progress-bar")
            
            # Daytona Panel
            with Vertical(id="daytona-panel", classes="panel"):
                yield Static(Text("🐳 DAYTONA FREE TIER", style="bold white"), classes="panel-title")
                yield UsageBar("Sandboxes", 0, 5, "", id="sandbox-bar", classes="progress-bar")
                yield UsageBar("Disk", 0, 30, "GB", id="disk-bar", classes="progress-bar")
                yield UsageBar("Memory", 0, 10, "GB", id="daytona-mem-bar", classes="progress-bar")
                yield Static(Text("\n📋 ACTIVE SANDBOXES", style="bold white"))
                yield SandboxList(id="sandbox-list")
            
            # Logs Panel
            with Vertical(id="logs-panel", classes="panel"):
                yield Static(Text("📜 LOGS — Backend", style="bold white"), id="log-title", classes="panel-title")
                with Horizontal():
                    yield Button("Redis", id="btn-log-redis", classes="action-btn")
                    yield Button("Backend", id="btn-log-backend", classes="action-btn")
                    yield Button("Frontend", id="btn-log-frontend", classes="action-btn")
                yield LogViewer(id="log-viewer")
            
            # Actions Panel  
            with Vertical(id="system-panel", classes="panel"):
                yield Static(Text("🔧 ACTIONS", style="bold white"), classes="panel-title")
                with Horizontal():
                    yield Button("Start", id="btn-start", classes="action-btn btn-start")
                    yield Button("Stop", id="btn-stop", classes="action-btn btn-stop")
                    yield Button("Restart", id="btn-restart", classes="action-btn btn-restart")
                with Horizontal():
                    yield Button("Cleanup", id="btn-cleanup", classes="action-btn btn-cleanup")
                    yield Button("Cache", id="btn-cache", classes="action-btn btn-cache")
                    yield Button("Refresh", id="btn-refresh", classes="action-btn btn-refresh")
        
        yield Static(id="status-line")
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize timers."""
        self.refresh_all()
        self.set_interval(2, self.refresh_services)
        self.set_interval(5, self.refresh_logs)
        self.set_interval(10, self.refresh_sandboxes)
        self.set_interval(1, self.refresh_system)
    
    def refresh_all(self) -> None:
        """Refresh everything."""
        self.refresh_services()
        self.refresh_sandboxes()
        self.refresh_logs()
        self.refresh_system()
        self._update_status_line()
    
    def refresh_services(self) -> None:
        """Refresh service status displays."""
        for service_id in SERVICES:
            try:
                for widget in self.query(ServiceStatus):
                    widget.refresh()
            except NoMatches:
                pass
        self._update_status_line()
    
    def refresh_system(self) -> None:
        """Refresh system stats."""
        stats = get_system_stats()
        try:
            self.query_one("#cpu-bar", UsageBar).update_value(stats["cpu_percent"], 100)
            self.query_one("#mem-bar", UsageBar).update_value(stats["memory_percent"], 100)
        except NoMatches:
            pass
    
    @work(exclusive=True, thread=True)
    def refresh_sandboxes(self) -> None:
        """Refresh sandbox information."""
        sandboxes, stats = get_sandboxes()
        self.call_from_thread(self._update_sandbox_display, sandboxes, stats)
    
    def _update_sandbox_display(self, sandboxes: List[SandboxInfo], stats: Dict[str, Any]) -> None:
        """Update sandbox display."""
        try:
            self.query_one("#sandbox-bar", UsageBar).update_value(stats["total"], 5)
            self.query_one("#disk-bar", UsageBar).update_value(stats["disk_used"], 30)
            self.query_one("#daytona-mem-bar", UsageBar).update_value(stats["memory_used"], 10)
            self.query_one("#sandbox-list", SandboxList).update_sandboxes(sandboxes, stats)
        except NoMatches:
            pass
    
    def refresh_logs(self) -> None:
        """Refresh log viewer."""
        try:
            self.query_one("#log-viewer", LogViewer).refresh_logs()
        except NoMatches:
            pass
    
    def _update_status_line(self) -> None:
        """Update status line."""
        self.refresh_count += 1
        now = datetime.now().strftime("%H:%M:%S")
        running = sum(1 for s in SERVICES if check_port(SERVICES[s]["port"]))
        
        text = Text()
        text.append(f" 🕐 {now}", style="dim")
        text.append(f"  │  ", style="dim")
        text.append(f"Services: ", style="dim")
        color = "green" if running == len(SERVICES) else "yellow" if running > 0 else "red"
        text.append(f"{running}/{len(SERVICES)}", style=color)
        if EXTERNAL_IP:
            text.append(f"  │  ", style="dim")
            text.append(f"External: ", style="dim")
            text.append(f"{EXTERNAL_IP}", style="cyan")
        text.append(f"  │  ", style="dim")
        text.append(f"Log: {self.current_log}", style="dim")
        text.append(f"  │  ", style="dim")
        text.append("Press ", style="dim")
        text.append("?", style="bold cyan")
        text.append(" for help", style="dim")
        
        try:
            self.query_one("#status-line", Static).update(text)
        except NoMatches:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        btn_id = event.button.id
        
        actions = {
            "btn-start": self.action_start_all,
            "btn-stop": self.action_stop_all,
            "btn-restart": self.action_restart_all,
            "btn-cleanup": self.action_cleanup,
            "btn-cache": self.action_clear_cache,
            "btn-refresh": self.action_refresh,
            "btn-log-redis": self.action_log_redis,
            "btn-log-backend": self.action_log_backend,
            "btn-log-frontend": self.action_log_frontend,
        }
        
        if btn_id in actions:
            actions[btn_id]()
    
    @work(exclusive=True, thread=True)
    def action_start_all(self) -> None:
        self.call_from_thread(self.notify, "Starting all services...", severity="information")
        subprocess.run(["bash", str(SCRIPTS_DIR / "start.sh")], capture_output=True)
        self.call_from_thread(self.notify, "Services started!", severity="information")
        self.call_from_thread(self.refresh_services)
    
    @work(exclusive=True, thread=True)
    def action_stop_all(self) -> None:
        self.call_from_thread(self.notify, "Stopping all services...", severity="warning")
        subprocess.run(["bash", str(SCRIPTS_DIR / "stop.sh")], capture_output=True)
        self.call_from_thread(self.notify, "Services stopped", severity="information")
        self.call_from_thread(self.refresh_services)
    
    @work(exclusive=True, thread=True)
    def action_restart_all(self) -> None:
        self.call_from_thread(self.notify, "Restarting services...", severity="warning")
        subprocess.run(["bash", str(SCRIPTS_DIR / "restart.sh")], capture_output=True)
        self.call_from_thread(self.notify, "Services restarted!", severity="information")
        self.call_from_thread(self.refresh_services)
    
    @work(exclusive=True, thread=True)
    def action_cleanup(self) -> None:
        self.call_from_thread(self.notify, "Cleaning up sandboxes...", severity="information")
        try:
            subprocess.run(["uv", "run", "python", "scripts/cleanup_sandboxes.py"], cwd=str(BACKEND_DIR), capture_output=True, timeout=30)
            self.call_from_thread(self.notify, "Cleanup complete!", severity="information")
        except Exception:
            self.call_from_thread(self.notify, "Cleanup failed", severity="error")
        self.refresh_sandboxes()
    
    @work(exclusive=True, thread=True)
    def action_clear_cache(self) -> None:
        self.call_from_thread(self.notify, "Clearing Redis cache...", severity="warning")
        try:
            subprocess.run(["redis-cli", "FLUSHALL"], capture_output=True, timeout=5)
            self.call_from_thread(self.notify, "Cache cleared!", severity="information")
        except Exception:
            self.call_from_thread(self.notify, "Failed to clear cache", severity="error")
    
    def action_refresh(self) -> None:
        self.notify("Refreshing...", severity="information")
        self.refresh_all()
    
    def action_log_redis(self) -> None:
        self._switch_log("redis", "Redis")
    
    def action_log_backend(self) -> None:
        self._switch_log("backend", "Backend")
    
    def action_log_frontend(self) -> None:
        self._switch_log("frontend", "Frontend")
    
    def _switch_log(self, service_id: str, name: str) -> None:
        self.current_log = service_id
        try:
            self.query_one("#log-viewer", LogViewer).set_service(service_id)
            self.query_one("#log-title", Static).update(Text(f"📜 LOGS — {name}", style="bold white"))
        except NoMatches:
            pass
    
    def action_select_focused(self) -> None:
        """Activate the currently focused button."""
        focused = self.focused
        if focused is not None and isinstance(focused, Button):
            focused.press()


def main():
    """Run the dashboard."""
    app = SunaDashboard()
    app.run()


if __name__ == "__main__":
    main()
