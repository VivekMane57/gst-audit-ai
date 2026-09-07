"""
backend/app/telemetry/tracker.py
Observability metrics tracking P50/P95 latencies and token cost
"""
from collections import deque
import numpy as np
from datetime import datetime


class TelemetryCollector:
    def __init__(self, max_samples: int = 1000):
        self.latencies = deque(maxlen=max_samples)
        self.request_logs = deque(maxlen=max_samples)
        # Pricing reference for Azure GPT-4o-mini ($0.15/1M input, $0.60/1M output)
        self.cost_per_input_token = 0.00000015
        self.cost_per_output_token = 0.00000060

    def record_llm_execution(self, feature_name: str, duration_ms: float, input_tokens: int = 180, output_tokens: int = 80):
        cost = (input_tokens * self.cost_per_input_token) + (output_tokens * self.cost_per_output_token)
        self.latencies.append(duration_ms)
        self.request_logs.append({
            "feature": feature_name,
            "duration_ms": round(duration_ms, 2),
            "estimated_cost_usd": round(cost, 6),
            "timestamp": datetime.now().isoformat()
        })

    def get_metrics_summary(self) -> dict:
        if not self.latencies:
            return {
                "total_requests": 0,
                "p50_latency_ms": 0.0,
                "p95_latency_ms": 0.0,
                "p99_latency_ms": 0.0,
                "avg_cost_per_query_usd": 0.0
            }

        lat_array = np.array(self.latencies)
        costs = [log["estimated_cost_usd"] for log in self.request_logs]

        return {
            "total_requests": len(self.latencies),
            "p50_latency_ms": round(float(np.percentile(lat_array, 50)), 2),
            "p95_latency_ms": round(float(np.percentile(lat_array, 95)), 2),
            "p99_latency_ms": round(float(np.percentile(lat_array, 99)), 2),
            "avg_cost_per_query_usd": round(float(np.mean(costs)), 6),
            "recent_traces": list(self.request_logs)[-5:]
        }


telemetry_collector = TelemetryCollector()