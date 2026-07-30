import collections, json, platform, re, threading, time
from pathlib import Path
try: import psutil
except: psutil = None
from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

import requests

import config

console = Console(highlight=False)
SAMPLES = collections.deque(maxlen=10)
HISTORY = collections.deque(maxlen=100)
STREAK_TYPE = [None]
STREAK_CNT = [0]
START_TIME = time.time()

# --- Web server ---
web_app = FastAPI()
conns = []
PAUSED = False
STOPPED = False
IS_RUNNING = False

@web_app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept(); conns.append(ws)
    try:
        while True:
            d = await ws.receive_text()
            if d == "ping": await ws.send_text("pong")
    except WebSocketDisconnect: pass
    finally:
        if ws in conns: conns.remove(ws)

@web_app.get("/api/config")
async def get_config(): return config.load_config_dict()

@web_app.post("/api/config")
async def post_config(data: dict):
    config.save_config_dict(data)
    return {"status": "ok"}

@web_app.get("/api/status")
async def get_status():
    return {"paused": PAUSED, "stopped": STOPPED, "is_running": IS_RUNNING}

@web_app.post("/api/control/{action}")
async def control(action: str):
    global PAUSED, STOPPED
    if action == "pause": PAUSED = True
    elif action == "resume": PAUSED = False
    elif action == "stop": STOPPED, PAUSED = True, False
    return {"status": action + "d" if action != "stop" else "stopped"}

@web_app.post("/update")
async def update(data: dict):
    for c in conns:
        try: await c.send_text(json.dumps(data))
        except: pass
    return {"status": "ok"}

@web_app.get("/")
async def root():
    return HTMLResponse(Path("templates/index.html").read_text())

def start_server():
    uvicorn.run(web_app, host="0.0.0.0", port=8000, log_level="error")

# --- Color helpers ---
def _sc(p):
    if p < 25: r, g = 255, int(165 * p / 25)
    elif p < 50: r, g = 255, int(165 + 90 * (p - 25) / 25)
    elif p < 75: r, g = int(255 * (1 - (p - 50) / 25)), 255
    else: r, g = 0, int(255 - 155 * (p - 75) / 25)
    return f"#{r:02x}{g:02x}00"

def _ec(i, t):
    if t <= 0: return "#00f"
    p = i / t
    if p <= 0.05:
        x = p / 0.05
        if x < 0.5: return f"#{int(128*x/0.5):02x}00{int(255-127*x/0.5):02x}"
        return f"#{int(128+127*(x-0.5)/0.5):02x}00{int(128-128*(x-0.5)/0.5):02x}"
    p = (p - 0.05) / 0.95
    if p < 0.25: return f"#ff{int(165*p/0.25):02x}00"
    if p < 0.5: return f"#ff{int(165+90*(p-0.25)/0.25):02x}00"
    if p < 0.75: return f"#{int(255*(1-(p-0.5)/0.25)):02x}ff00"
    return f"#00{int(255-155*(p-0.75)/0.25):02x}00"

SPECTRUM = [(0,255,255,0),(100,0,255,0),(200,0,100,0),(250,0,0,139),(300,0,0,255),
    (400,75,0,130),(500,128,0,128),(600,255,140,0),(700,255,165,0),
    (800,255,0,0),(900,255,255,0),(1000,0,128,128),(1100,238,130,238)]

def _yc(v):
    if v >= SPECTRUM[-1][0]: r,g,b = SPECTRUM[-1][1:]
    else:
        for i in range(len(SPECTRUM)-1):
            if v <= SPECTRUM[i+1][0]:
                lo, hi = SPECTRUM[i], SPECTRUM[i+1]
                t = (v - lo[0]) / (hi[0] - lo[0])
                r = int(lo[1] + (hi[1] - lo[1]) * t)
                g = int(lo[2] + (hi[2] - lo[2]) * t)
                b = int(lo[3] + (hi[3] - lo[3]) * t)
                break
    return f"#{r:02x}{g:02x}{b:02x}"

def _panel(title, info, bs):
    t = Table(show_header=False, box=None, padding=(0,1), expand=True)
    t.add_column(justify="left", style="white", ratio=1)
    for k,v in info: t.add_row(f"[bold]{k}[/]\n{v}")
    return Panel(t, title=f"[bold]{title}[/]", border_style=bs, expand=True)

# --- Display ---
def _rv(v):
    return "\U0001f4af" if v == 100 else str(v)

def print_launcher(tasks, proxies, workers, shuffle, ip_score):
    tp = f"~{int((60 / ((config.MIN_DELAY + config.MAX_DELAY) / 2)) * workers)} URLs/min"
    try:
        _cpu = f"[white]{psutil.cpu_percent()}% / RAM {psutil.virtual_memory().percent}%[/]"
    except: _cpu = "N/A"
    marks = "\n".join(f"{m[1]} {int(m[0])}%" for m in
        [(0,"\U0001f7e5"),(10,"\U0001f534"),(20,"\u2764\ufe0f "),(25,"\U0001f7e7"),(35,"\U0001f7e0"),
         (45,"\U0001f9e1"),(50,"\U0001f7e8"),(60,"\U0001f7e1"),(70,"\U0001f49b"),(75,"\U0001f7e9"),
         (85,"\U0001f7e2"),(95,"\U0001f49a"),(100,"\U0001f49a")])
    legend = "\u2705 OK\n\U0001f47b 404\n\U0001f6ab 403\n\U0001f69a 301\n\U0001f4e1 101\n\u2601\ufe0f 503\n\U0001f40c Lag\n\U0001f4c9 Track"
    mid = Table.grid(expand=True)
    mid.add_column(ratio=1); mid.add_column(width=14); mid.add_column(width=14)
    top = Table.grid(expand=True)
    top.add_column(ratio=1); top.add_column(ratio=1); top.add_column(ratio=1)
    top.add_row(
        _panel("\u26a1 PERFORMANCE", [("Concurrency", f"[yellow]{workers} Workers[/]"),
            ("Throughput", f"[green]{tp}[/]"),("Delays", f"[green]{config.MIN_DELAY}-{config.MAX_DELAY}s[/]"),
            ("Timeout", f"[green]{config.TIMEOUT}s[/]")], "bright_cyan"),
        _panel("\U0001f310 INFRASTRUCTURE", [("Proxy Pool", f"[green]{proxies} Active[/]"),
            ("Proxy Logic", "[magenta]Sticky-Session[/]")], "bright_cyan"),
        _panel("\U0001f4cb JOB", [("URLs Queued", f"[yellow]{tasks}[/]"),
            ("Shuffle", f"[green]{'Yes' if shuffle else 'No'}[/]")], "bright_magenta"))
    top.add_row(
        _panel("\U0001f4bb ENVIRONMENT", [("OS", f"[white]{platform.system()}[/]"),
            ("Py Version", f"[white]{platform.python_version()}[/]")], "bright_cyan"),
        _panel("\U0001f4ca SYSTEM HEALTH", [("CPU", _cpu),
            ("Uptime", f"[white]{time.strftime('%H:%M:%S', time.gmtime(time.time() - START_TIME))}[/]")], "bright_cyan"),
        _panel("\U0001f6e1\ufe0f SECURITY", [("Auth User", f"[magenta]{config.UI_USER}[/]"),
            ("SSL Check", "[green]Disabled[/]"),("IP Reputation", f"[yellow]{ip_score}/100[/]")], "bright_red"))
    mid.add_row(top, Panel(Text(marks, justify="left"), title="[bold]HEALTH[/]", border_style="white", width=14, height=20),
        Panel(Text(legend, style="white"), title="[bold]ERRORS[/]", border_style="grey58", width=14, height=20))
    console.print(Panel(Group(mid, Panel(Align.center(f"[bold white]User Agent Identity[/]\n[yellow]{config.USER_AGENT}[/]"),
        title="[bold]\U0001f575\ufe0f USER AGENT[/]", border_style="bright_white", expand=True)),
        title="[bold white]\U0001f680 Bonus Scraper Engine v5.0[/]", border_style="bright_white", padding=(1,1)))
    console.print(Panel(Align.center("[bold white]\U0001f4e1 COMMAND DASHBOARD ACTIVE :[/][bold cyan] http://127.0.0.1:8000[/]"),
        border_style="bright_white", style="on blue", padding=(0,1)))
    console.print(Align.center("[bold red]\u25cf[/][bold white] SYSTEM READY [/][bold cyan]PRESS [CTRL+C] TO TERMINATE[/]"))

def update_display(d):
    global STREAK_TYPE, STREAK_CNT
    idx, url = d["index"], d["site_url"].replace("https://","").replace("www.","")
    msg, total = d["status_message"], d.get("N",0)
    site_new, total_new = int(d.get("site_new_bonuses",0)), int(d.get("total_new_bonuses",0))
    elapsed, nw = d.get("elapsed",0), int(d.get("nw",1))
    SAMPLES.append(elapsed)
    est = ((total - idx) * (sum(SAMPLES)/len(SAMPLES) + (config.MIN_DELAY + config.MAX_DELAY) / 2)) / max(nw, 1)
    time_str = f"{int(est//60)}m{est%60:06.3f}s"
    ok = 1 if msg.startswith("\u2705") else 0
    HISTORY.append(ok)
    if STREAK_TYPE[0] is None or STREAK_TYPE[0] != bool(ok): STREAK_TYPE[0], STREAK_CNT[0] = bool(ok), 1
    else: STREAK_CNT[0] += 1
    r = list(HISTORY)
    r5 = int(sum(r[-5:])/max(len(r[-5:]),1)*100) if r else 0
    r10 = int(sum(r[-10:])/max(len(r[-10:]),1)*100) if len(r)>=10 else r5
    r20 = int(sum(r[-20:])/max(len(r[-20:]),1)*100) if len(r)>=20 else r10
    r50 = int(sum(r[-50:])/max(len(r[-50:]),1)*100) if len(r)>=50 else r20
    r100 = int(sum(r[-100:])/max(len(r[-100:]),1)*100) if len(r)>=100 else r50
    rate = (d["successes"]/idx*100) if idx>0 else 0
    yield_v = (total_new/idx*100) if idx>0 else 0
    if msg.startswith("\u2705"): sfmt, col = "\u2705DONE\u2705", "bright_green"
    else:
        m = re.search(r"E(\d+)", msg)
        if m:
            c = m.group(1)
            icon = "\U0001f69a" if c=="301" else "\U0001f4e1" if c=="101" else "\U0001f4bb"
            sfmt, col = f"{icon}E{c}\u274c", "red" if c!="301" else "cyan"
        else: sfmt, col = "\u274cFAIL\u274c", "red"
    line = (f"[{_ec(idx,total)}]{idx:03d}[/][{col}]{sfmt}[/][{col}]{STREAK_CNT[0]:02d}[/] "
        f"[{_sc(r5)}]{_rv(r5)}[/] [{_sc(r10)}]{_rv(r10)}[/] [{_sc(r20)}]{_rv(r20)}[/] [{_sc(r50)}]{_rv(r50)}[/] [{_sc(r100)}]{_rv(r100)}[/] [{_sc(rate)}]{int(rate):03d}[/] "
        f"[{_yc(yield_v)}]{yield_v:05.1f}[/]\U0001f48e{site_new:02d}|{total_new:02d} "
        f"\u23f1\ufe0f[{_ec(idx,total)}]{time_str}[/]\U0001f310{url}")
    console.print(line)
    try: requests.post("http://localhost:8000/update", json=d, timeout=0.1)
    except: pass

def print_completion(stats):
    elapsed = time.strftime("%H:%M:%S", time.gmtime(time.time() - START_TIME))
    total = stats["successes"] + stats["failures"]
    rate = (stats["successes"] / total * 100) if total > 0 else 0
    lines = [
        "[bold green]Scraping Complete[/]",
        f"  [white]Sites Scraped:[/]  [yellow]{total}[/]",
        f"  [white]Successful:[/]    [green]{stats['successes']}[/]",
        f"  [white]Failed:[/]        [red]{stats['failures']}[/]",
        f"  [white]Success Rate:[/]  [cyan]{rate:.1f}%[/]",
        f"  [white]Bonuses Found:[/] [yellow]{stats['total_bonuses']}[/]",
        f"  [white]New Bonuses:[/]   [magenta]{stats['new_bonuses']}[/]",
        f"  [white]Elapsed:[/]       [green]{elapsed}[/]"]
    panel = Panel("\n".join(lines), title="[bold]\U0001f3c1 RESULTS[/]", border_style="green", expand=True)
    console.print()
    console.print(Panel(Align.center(panel), border_style="bright_green", padding=(1, 1)))
    console.print(Align.center("[bold yellow]\u25cf[/][bold white] Dashboard at [bold cyan]http://127.0.0.1:8000[/]"))
