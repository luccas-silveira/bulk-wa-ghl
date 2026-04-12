import re
from prometheus_client import Counter, Gauge, Histogram

api_request_latency = Histogram(
    "api_request_latency_seconds",
    "API request latency in seconds",
    ["method", "path"],
)

api_request_errors = Counter(
    "api_request_errors_total",
    "Total API request errors",
    ["method", "path", "status"],
)

scheduler_jobs_gauge = Gauge(
    "campaign_scheduler_jobs",
    "Number of scheduled campaign jobs",
)

campaign_queue_gauge = Gauge(
    "campaign_queue_size",
    "Number of campaigns queued for execution",
)

messages_sent_total = Counter(
    "messages_sent_total",
    "Total messages sent by the campaign executor",
    ["status"],  # status: sent | failed
)

campaigns_active_gauge = Gauge(
    "campaigns_active",
    "Number of campaigns currently in executing state",
)

# --- Pool metrics (updated on each /metrics scrape) ---
db_pool_size_gauge = Gauge(
    "db_pool_size",
    "Configured SQLAlchemy pool size",
)

db_pool_checkedout_gauge = Gauge(
    "db_pool_checkedout",
    "SQLAlchemy connections currently checked out from pool",
)

db_pool_queue_size_gauge = Gauge(
    "db_pool_queue_size",
    "SQLAlchemy connections currently idle in pool",
)

_POOL_SIZE_RE = re.compile(r"Pool size:\s*(\d+)")
_CHECKED_OUT_RE = re.compile(r"Current Checked out connections:\s*(\d+)")
_IN_POOL_RE = re.compile(r"Connections in pool:\s*(\d+)")


def update_pool_metrics(engine) -> None:
    """Parse engine.pool.status() and update Prometheus Gauges."""
    try:
        status_str = engine.pool.status()
        m_size = _POOL_SIZE_RE.search(status_str)
        m_out = _CHECKED_OUT_RE.search(status_str)
        m_idle = _IN_POOL_RE.search(status_str)
        if m_size:
            db_pool_size_gauge.set(int(m_size.group(1)))
        if m_out:
            db_pool_checkedout_gauge.set(int(m_out.group(1)))
        if m_idle:
            db_pool_queue_size_gauge.set(int(m_idle.group(1)))
    except Exception:
        pass  # Never crash a metrics scrape
