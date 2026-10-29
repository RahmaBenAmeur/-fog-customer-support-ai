"""Agent de métriques : à copier sur les 3 nœuds (racine du dépôt sur le nœud 2, C:\\llm_node, C:\\gateway).

Expose :
  GET /metrics : CPU, RAM, réseau, processus principaux de la machine
  GET /events  : derniers événements applicatifs (durées par étape)

Usage dans un service FastAPI :
    from metrics import router, record
    app.include_router(router)
    record("chat", duree_ms, state="ok")
"""
import socket
import time
from collections import deque

import psutil
from fastapi import APIRouter

router = APIRouter()

EVENTS = deque(maxlen=300)
WATCH = ("ollama", "python", "uvicorn", "streamlit")

psutil.cpu_percent(percpu=True)  # amorce le calcul du CPU


def record(kind: str, ms: float, **extra) -> None:
    """Enregistre un événement (kind = transcribe, chat, llm_call, llm_error, llm...).

    On ne stocke que des durées et des états, jamais le contenu des messages."""
    EVENTS.append({"t": time.time(), "kind": kind, "ms": round(ms), **extra})


def _processes():
    out = []
    for p in psutil.process_iter(["name", "cpu_percent", "memory_info"]):
        try:
            name = (p.info["name"] or "").lower()
            if any(k in name for k in WATCH):
                out.append(
                    {
                        "name": name,
                        "pid": p.pid,
                        "cpu": round(p.info["cpu_percent"] or 0, 1),  # % d'un coeur
                        "ram_mb": round(p.info["memory_info"].rss / 1e6),
                    }
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(out, key=lambda x: -x["ram_mb"])[:8]


@router.get("/metrics")
def metrics():
    vm = psutil.virtual_memory()
    net = psutil.net_io_counters()
    return {
        "host": socket.gethostname(),
        "ts": time.time(),
        "cpu_percent": psutil.cpu_percent(),
        "cpu_per_core": psutil.cpu_percent(percpu=True),
        "cpu_count": psutil.cpu_count(),
        "ram_percent": vm.percent,
        "ram_used_gb": round(vm.used / 1e9, 2),
        "ram_total_gb": round(vm.total / 1e9, 2),
        "net_sent": net.bytes_sent,
        "net_recv": net.bytes_recv,
        "processes": _processes(),
    }


@router.get("/events")
def events():
    return list(EVENTS)
