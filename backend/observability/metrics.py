"""Dependency-free, low-cardinality Prometheus text metrics."""

from __future__ import annotations

from collections import Counter, defaultdict


class Metrics:
    def __init__(self) -> None:
        self.requests = Counter()
        self.errors = Counter()
        self.duration_sum = defaultdict(float)

    def observe(self, method: str, route: str, status_code: int, duration_seconds: float) -> None:
        key = (method.upper(), route)
        self.requests[key] += 1
        self.duration_sum[key] += duration_seconds
        if status_code >= 400:
            self.errors[key] += 1

    def render(self) -> str:
        lines = [
            "# HELP pro_trading_ds_http_requests_total HTTP requests by method and route.",
            "# TYPE pro_trading_ds_http_requests_total counter",
        ]
        for (method, route), count in sorted(self.requests.items()):
            labels = f'method="{method}",route="{route}"'
            lines.append(f"pro_trading_ds_http_requests_total{{{labels}}} {count}")
        lines.extend([
            "# HELP pro_trading_ds_http_errors_total HTTP responses with status >= 400.",
            "# TYPE pro_trading_ds_http_errors_total counter",
        ])
        for (method, route), count in sorted(self.errors.items()):
            labels = f'method="{method}",route="{route}"'
            lines.append(f"pro_trading_ds_http_errors_total{{{labels}}} {count}")
        lines.extend([
            "# HELP pro_trading_ds_http_duration_seconds_sum Request duration sum.",
            "# TYPE pro_trading_ds_http_duration_seconds_sum counter",
        ])
        for (method, route), total in sorted(self.duration_sum.items()):
            labels = f'method="{method}",route="{route}"'
            lines.append(f"pro_trading_ds_http_duration_seconds_sum{{{labels}}} {total:.6f}")
        return "\n".join(lines) + "\n"


metrics = Metrics()


def observe_request(method: str, route: str, status_code: int, duration_seconds: float) -> None:
    metrics.observe(method, route, status_code, duration_seconds)
