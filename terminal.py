import collections, platform, re, threading, time
try:
    import psutil
except Exception:
    psutil = None
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
import requests
import config

console = Console(highlight=False)
SAMPLES = collections.deque(maxlen=10)
HISTORY = collections.deque(maxlen=100)
STREAK_TYPE = [None]
STREAK_CNT = [0]
START_TIME = time.time()

def get_streak_color(percentage):
    if percentage < 25:
        red, green = 255, int(165 * percentage / 25)
    elif percentage < 50:
        red, green = 255, int(165 + 90 * (percentage - 25) / 25)
    elif percentage < 75:
        red, green = int(255 * (1 - (percentage - 50) / 25)), 255
    else:
        red, green = 0, int(255 - 155 * (percentage - 75) / 25)
    return f"#{red:02x}{green:02x}00"

def get_elapsed_color(index, total):
    if total <= 0:
        return "#00f"
    percentage = index / total
    if percentage <= 0.05:
        ratio = percentage / 0.05
        if ratio < 0.5:
            return f"#{int(128 * ratio / 0.5):02x}00{int(255 - 127 * ratio / 0.5):02x}"
        return f"#{int(128 + 127 * (ratio - 0.5) / 0.5):02x}00{int(128 - 128 * (ratio - 0.5) / 0.5):02x}"
        
    percentage = (percentage - 0.05) / 0.95
    if percentage < 0.25:
        return f"#ff{int(165 * percentage / 0.25):02x}00"
    if percentage < 0.5:
        return f"#ff{int(165 + 90 * (percentage - 0.25) / 0.25):02x}00"
    if percentage < 0.75:
        return f"#{int(255 * (1 - (percentage - 0.5) / 0.25)):02x}ff00"
    return f"#00{int(255 - 155 * (percentage - 0.75) / 0.25):02x}00"

SPECTRUM = [
    (0, 255, 255, 0), (100, 0, 255, 0), (200, 0, 100, 0),
    (250, 0, 0, 139), (300, 0, 0, 255), (400, 75, 0, 130),
    (500, 128, 0, 128), (600, 255, 140, 0), (700, 255, 165, 0),
    (800, 255, 0, 0), (900, 255, 255, 0), (1000, 0, 128, 128),
    (1100, 238, 130, 238)
]

def get_yield_color(value):
    if value >= SPECTRUM[-1][0]:
        red, green, blue = SPECTRUM[-1][1:]
    else:
        for i in range(len(SPECTRUM) - 1):
            if value <= SPECTRUM[i + 1][0]:
                low, high = SPECTRUM[i], SPECTRUM[i + 1]
                ratio = (value - low[0]) / (high[0] - low[0])
                red = int(low[1] + (high[1] - low[1]) * ratio)
                green = int(low[2] + (high[2] - low[2]) * ratio)
                blue = int(low[3] + (high[3] - low[3]) * ratio)
                break
    return f"#{red:02x}{green:02x}{blue:02x}"

def build_panel(title, info_list, border_style):
    table = Table(show_header=False, box=None, padding=(0, 1), expand=True)
    table.add_column(justify="left", style="white", ratio=1)
    for key, value in info_list:
        table.add_row(f"[bold]{key}[/]\n{value}")
    return Panel(table, title=f"[bold]{title}[/]", border_style=border_style, expand=True)

def format_percentage(value):
    return "\U0001f4af" if value == 100 else str(value)

def print_launcher(tasks, proxies, workers, shuffle, ip_score):
    global START_TIME
    START_TIME = time.time()
    throughput = f"~{int((60 / ((config.MIN_DELAY + config.MAX_DELAY) / 2)) * workers)} URLs/min"
    
    try:
        cpu_stats = f"[white]{psutil.cpu_percent()}% / RAM {psutil.virtual_memory().percent}%[/]"
    except Exception:
        cpu_stats = "N/A"
        
    marks = "\n".join(f"{mark[1]} {int(mark[0])}%" for mark in [
        (0, "\U0001f7e5"), (10, "\U0001f534"), (20, "\u2764\ufe0f "), (25, "\U0001f7e7"),
        (35, "\U0001f7e0"), (45, "\U0001f9e1"), (50, "\U0001f7e8"), (60, "\U0001f7e1"),
        (70, "\U0001f49b"), (75, "\U0001f7e9"), (85, "\U0001f7e2"), (95, "\U0001f49a"), (100, "\U0001f49a")
    ])
    
    legend = "\u2705 OK\n\U0001f47b 404\n\U0001f6ab 403\n\U0001f69a 301\n\U0001f4e1 101\n\u2601\ufe0f 503\n\U0001f40c Lag\n\U0001f4c9 Track"
    
    mid_table = Table.grid(expand=True)
    mid_table.add_column(ratio=1)
    mid_table.add_column(width=14)
    
    top_table = Table.grid(expand=True)
    top_table.add_column(ratio=1)
    top_table.add_column(ratio=1)
    top_table.add_column(ratio=1)
    
    top_table.add_row(
        build_panel("\u26a1 PERFORMANCE", [("Concurrency", f"[yellow]{workers} Workers[/]"),
            ("Throughput", f"[green]{throughput}[/]"), ("Delays", f"[green]{config.MIN_DELAY}-{config.MAX_DELAY}s[/]"),
            ("Timeout", f"[green]{config.TIMEOUT}s[/]")], "bright_cyan"),
        build_panel("\U0001f310 INFRASTRUCTURE", [("Proxy Pool", f"[green]{proxies} Active[/]"),
            ("Proxy Logic", "[magenta]Per-Worker Pool[/]")], "bright_cyan"),
        build_panel("\U0001f4cb JOB", [("URLs Queued", f"[yellow]{tasks}[/]"),
            ("Shuffle", f"[green]{'Yes' if shuffle else 'No'}[/]")], "bright_magenta")
    )
    
    top_table.add_row(
        build_panel("\U0001f4bb ENVIRONMENT", [("OS", f"[white]{platform.system()}[/]"),
            ("Py Version", f"[white]{platform.python_version()}[/]")], "bright_cyan"),
        build_panel("\U0001f4ca SYSTEM HEALTH", [("Status", marks)], "bright_cyan"),
        build_panel("\U0001f6e1\ufe0f SECURITY", [("Auth User", f"[magenta]{config.UI_USER}[/]"),
            ("SSL Check", "[green]Disabled[/]"), ("IP Reputation", f"[yellow]{ip_score}/100[/]")], "bright_red")
    )
    
    mid_table.add_row(
        top_table, 
        Panel(Text(legend, style="white"), title="[bold]ERRORS[/]", border_style="grey58", width=14, height=20)
    )
    
    console.print(Panel(Group(mid_table, Panel(Align.center(f"[bold white]User Agent Identity[/]\n[yellow]{config.USER_AGENT}[/]"),
        title="[bold]\U0001f575\ufe0f USER AGENT[/]", border_style="bright_white", expand=True)),
        title="[bold white]\U0001f680 Bonus Scraper Engine v5.0[/]", border_style="bright_white", padding=(1, 1)))
        
    console.print(Panel(Align.center("[bold white]\U0001f4e1 COMMAND DASHBOARD ACTIVE :[/][bold cyan] http://127.0.0.1:8000[/]"),
        border_style="bright_white", style="on blue", padding=(0, 1)))
        
    console.print(Align.center("[bold red]\u25cf[/][bold white] SYSTEM READY [/][bold cyan]PRESS [CTRL+C] TO TERMINATE[/]"))

def update_display(data_dict):
    global STREAK_TYPE, STREAK_CNT
    index = data_dict["index"]
    url = data_dict["site_url"].replace("https://", "").replace("www.", "")
    message = data_dict["status_message"]
    total = data_dict.get("N", 0)
    site_new = int(data_dict.get("site_new_bonuses", 0))
    total_new = int(data_dict.get("total_new_bonuses", 0))
    elapsed_time = data_dict.get("elapsed", 0)
    num_workers = int(data_dict.get("nw", 1))
    
    SAMPLES.append(elapsed_time)
    
    avg_sample_time = sum(SAMPLES) / max(len(SAMPLES), 1)
    delay_avg = (config.MIN_DELAY + config.MAX_DELAY) / 2
    estimated_seconds = ((total - index) * (avg_sample_time + delay_avg)) / max(num_workers, 1)
    time_string = f"{int(estimated_seconds // 60)}m{estimated_seconds % 60:06.3f}s"
    
    is_success = 1 if message.startswith("\u2705") else 0
    HISTORY.append(is_success)
    
    if STREAK_TYPE[0] is None or STREAK_TYPE[0] != bool(is_success):
        STREAK_TYPE[0] = bool(is_success)
        STREAK_CNT[0] = 1
    else:
        STREAK_CNT[0] += 1
        
    recent = list(HISTORY)
    rate_5 = int(sum(recent[-5:]) / max(len(recent[-5:]), 1) * 100) if recent else 0
    rate_10 = int(sum(recent[-10:]) / max(len(recent[-10:]), 1) * 100) if len(recent) >= 10 else rate_5
    rate_20 = int(sum(recent[-20:]) / max(len(recent[-20:]), 1) * 100) if len(recent) >= 20 else rate_10
    rate_50 = int(sum(recent[-50:]) / max(len(recent[-50:]), 1) * 100) if len(recent) >= 50 else rate_20
    rate_100 = int(sum(recent[-100:]) / max(len(recent[-100:]), 1) * 100) if len(recent) >= 100 else rate_50
    
    success_rate = (data_dict["successes"] / index * 100) if index > 0 else 0
    yield_value = (total_new / index * 100) if index > 0 else 0
    
    if message.startswith("\u2705"):
        status_format, color = "\u2705DONE\u2705", "bright_green"
    else:
        error_match = re.search(r"E(\d+)", message)
        if error_match:
            error_code = error_match.group(1)
            icon = "\U0001f69a" if error_code == "301" else "\U0001f4e1" if error_code == "101" else "\U0001f4bb"
            status_format, color = f"{icon}E{error_code}\u274c", "red" if error_code != "301" else "cyan"
        else:
            status_format, color = "\u274cFAIL\u274c", "red"
            
    line = (
        f"[{get_elapsed_color(index, total)}]{index:03d}[/][{color}]{status_format}[/][{color}]{STREAK_CNT[0]:02d}[/] "
        f"[{get_streak_color(rate_5)}]{format_percentage(rate_5)}[/] "
        f"[{get_streak_color(rate_10)}]{format_percentage(rate_10)}[/] "
        f"[{get_streak_color(rate_20)}]{format_percentage(rate_20)}[/] "
        f"[{get_streak_color(rate_50)}]{format_percentage(rate_50)}[/] "
        f"[{get_streak_color(rate_100)}]{format_percentage(rate_100)}[/] "
        f"[{get_streak_color(success_rate)}]{int(success_rate):03d}[/] "
        f"[{get_yield_color(yield_value)}]{yield_value:05.1f}[/]\U0001f48e{site_new:02d}|{total_new:02d} "
        f"\u23f1\ufe0f[{get_elapsed_color(index, total)}]{time_string}[/]\U0001f310{url}"
    )
    
    console.print(line)
    
    try:
        requests.post("http://localhost:8000/update", json=data_dict, timeout=0.1)
    except Exception:
        pass

def print_completion(stats):
    elapsed_time = time.strftime("%H:%M:%S", time.gmtime(time.time() - START_TIME))
    total_sites = stats["successes"] + stats["failures"]
    success_rate = (stats["successes"] / total_sites * 100) if total_sites > 0 else 0
    
    lines = [
        "[bold green]Scraping Complete[/]",
        f"  [white]Sites Scraped:[/]  [yellow]{total_sites}[/]",
        f"  [white]Successful:[/]    [green]{stats['successes']}[/]",
        f"  [white]Failed:[/]        [red]{stats['failures']}[/]",
        f"  [white]Success Rate:[/]  [cyan]{success_rate:.1f}%[/]",
        f"  [white]Bonuses Found:[/] [yellow]{stats['total_bonuses']}[/]",
        f"  [white]New Bonuses:[/]   [magenta]{stats['new_bonuses']}[/]",
        f"  [white]Elapsed:[/]       [green]{elapsed_time}[/]"
    ]
    
    panel = Panel("\n".join(lines), title="[bold]\U0001f3c1 RESULTS[/]", border_style="green", expand=True)
    console.print()
    console.print(Panel(Align.center(panel), border_style="bright_green", padding=(1, 1)))
    console.print(Align.center("[bold yellow]\u25cf[/][bold white] Dashboard at [bold cyan]http://127.0.0.1:8000[/]"))
