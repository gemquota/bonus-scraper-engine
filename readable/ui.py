"""
ui.py - Terminal User Interface

Provides real-time progress display with color-coded status indicators.
"""

import re
import bisect
import collections
import datetime
import threading
import requests

import config
import network_health
import error_definitions

from rich.console import Console

# Rich console for formatted output
console = Console(highlight=False)

# Recent request durations for ETA calculation
RECENT_DURATIONS = collections.deque(maxlen=10)

# Thread lock for console output
UI_LOCK = threading.Lock()

# Verbosity level: "min", "med", or "max"
VERBOSITY = "min"

# Map success rate percentage to emoji symbols
# Format: (threshold, emoji)
SYMBOL_MAP = [
    (0.0, "🟥"),    # 0%
    (10.0, "🔴"),   # 10%
    (20.0, "❤️"),   # 20%
    (25.0, "🟧"),   # 25%
    (35.0, "🟠"),   # 35%
    (45.0, "🧡"),   # 45%
    (50.0, "🟨"),   # 50%
    (60.0, "🟡"),   # 60%
    (70.0, "💛"),   # 70%
    (75.0, "🟩"),   # 75%
    (85.0, "🟢"),   # 85%
    (95.0, "💚"),   # 95%
    (100.0, "👑"),  # 100%
]


def get_rate_symbol(rate):
    """
    Get emoji symbol for a success rate percentage.

    Args:
        rate: Success rate as percentage (0-100)

    Returns:
        str: Emoji symbol representing the rate
    """
    idx = bisect.bisect_right(SYMBOL_MAP, (rate, "zzzz")) - 1
    return SYMBOL_MAP[max(0, idx)][1]


def get_color(percentage):
    """
    Get hex color for a percentage (red -> yellow -> green gradient).

    Args:
        percentage: Value from 0-100

    Returns:
        str: Hex color code (e.g., "#ff8000")
    """
    if percentage < 50:
        # Red to Yellow: Red stays 255, Green increases
        red = 255
        green = int(255 * (percentage / 50))
    else:
        # Yellow to Green: Green stays 255, Red decreases
        green = 255
        red = int(255 * ((100 - percentage) / 50))

    return f"#{red:02x}{green:02x}00"


def update(data):
    """
    Print a formatted status line to the console.

    Also broadcasts the update to the web dashboard via HTTP POST.

    Args:
        data: Dictionary containing:
            - index: Current task index
            - successes: Success count
            - failures: Failure count
            - total_bonuses: Total bonuses found
            - site_url: Current site URL
            - status_message: Status ("✅" or "E301" etc.)
            - site_bonuses_gt_zero: Bonuses found on this site
            - N: Total task count
            - elapsed: Time taken for this task
            - is_expiring: True if site has expiring bonuses
            - ip_score: IP health score
            - error_details: (optional) Error details for verbose mode
    """
    # Extract values from data
    index = data['index']
    successes = data['successes']
    total_bonuses = data['total_bonuses']
    site_url = data['site_url'].replace('https://', '').replace('www.', '')
    status_message = data['status_message']
    total_count = data.get('N', 0)
    elapsed = data.get('elapsed', 0)

    # Track recent durations for ETA calculation
    RECENT_DURATIONS.append(elapsed)
    avg_duration = sum(RECENT_DURATIONS) / len(RECENT_DURATIONS) if RECENT_DURATIONS else 0

    # Calculate ETA
    avg_delay = (config.MIN_DELAY + config.MAX_DELAY) / 2
    remaining = total_count - index
    estimated_seconds = remaining * (avg_duration + avg_delay)

    # Format ETA
    remaining_timedelta = datetime.timedelta(seconds=int(estimated_seconds))
    tz = datetime.timezone(datetime.timedelta(hours=10))
    finish_time = (datetime.datetime.now(tz) + remaining_timedelta).strftime("%H:%M")

    hours, remainder = divmod(int(estimated_seconds), 3600)
    minutes = remainder // 60
    duration_str = f"{hours}h{minutes}m" if hours > 0 else f"{minutes}m"

    # Calculate success rate
    success_rate = (successes / index * 100) if index > 0 else 0
    success_symbol = get_rate_symbol(success_rate)
    site_bonus_count = int(data.get("site_bonuses_gt_zero", 0))
    color_var = get_color(success_rate)

    # Format status message
    verbose_message = ""
    if status_message.startswith("✅"):
        status_text = "DONE"
        icon = "✅"
        status_color = "green"
    else:
        match = re.search(r"E(\d+)", status_message)
        if match:
            error_code = int(match.group(1))
            error_info = error_definitions.get_error_info(error_code)

            if VERBOSITY == "min":
                status_text = f"E{error_code}"
            elif VERBOSITY == "med":
                status_text = f"E{error_code}: {error_info['brief']}"
            else:  # max
                status_text = f"E{error_code}: {error_info['brief']}"
                verbose_message = f"\n  [dim italic]└─ {error_info['verbose']}[/]"
                if data.get('error_details'):
                    verbose_message += f"\n  [dim]└─ Raw: {data.get('error_details')}[/]"

            icon = "⛔"
            status_color = "red"
        else:
            status_text = "FAIL"
            icon = "⛔"
            status_color = "red"

    # Format ETA string
    eta_str = f"[dim]{finish_time}/{duration_str}[/]"

    # Expiring indicator
    expiring_icon = "⏳" if data.get('is_expiring') else ""

    # IP health indicator
    ip_score = data.get('ip_score', 0)
    health_text, health_color = network_health.get_health_status(ip_score)

    # Broadcast to web dashboard (non-blocking)
    try:
        requests.post('http://localhost:8000/update', json=data, timeout=0.1)
    except Exception:
        pass

    # Print formatted status line
    with UI_LOCK:
        console.print(
            f"[{health_color}]{health_text}[/] "
            f"{index:03d} {success_symbol} "
            f"[bright_cyan]{site_bonus_count:03d}[/]/[dodger_blue1]{total_bonuses:03d}[/] "
            f"[{color_var}]{int(success_rate):03d}%[/] {success_symbol} "
            f"[{status_color}]{status_text}[/] {icon} "
            f"{eta_str} 🌐 [bright_white]{site_url}[/]"
            f"{verbose_message}"
        )
