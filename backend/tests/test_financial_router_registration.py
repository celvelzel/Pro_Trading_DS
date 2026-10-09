"""The typed financial API is additive to the existing General agent router."""

from fastapi.routing import APIRoute

from main import app


def test_financial_routes_are_registered_without_replacing_general_routes():
    operations = {
        (route.path, method)
        for route in app.routes
        if isinstance(route, APIRoute)
        for method in route.methods
    }

    assert {
        ("/api/financial/market-investigations", "POST"),
        ("/api/financial/portfolio-reviews", "POST"),
        ("/api/financial/combined-reviews", "POST"),
        ("/api/financial/runs/{run_id}", "GET"),
        ("/api/financial/runs/{run_id}/approve", "POST"),
        ("/api/financial/runs/{run_id}/pause", "POST"),
        ("/api/financial/runs/{run_id}/resume", "POST"),
        ("/api/financial/runs/{run_id}/cancel", "POST"),
    } <= operations
    assert ("/api/agent/runs", "POST") in operations
    assert ("/api/agent/runs/{run_id}/events", "GET") in operations
