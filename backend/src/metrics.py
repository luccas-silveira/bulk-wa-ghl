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
