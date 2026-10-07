package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestRunHealthCheck_Healthy(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(HealthResponse{
			Status:   "ok",
			Service:  "self-healing-k8s-service",
			Version:  "1.0.0",
			Degraded: false,
		})
	}))
	defer server.Close()

	res := runHealthCheck(server.URL, 2*time.Second)

	if !res.Healthy {
		t.Fatalf("expected healthy true, got false. Error: %s", res.Error)
	}
	if res.HTTPStatus != http.StatusOK {
		t.Fatalf("expected status 200, got %d", res.HTTPStatus)
	}
	if res.Body == nil || res.Body.Status != "ok" {
		t.Fatalf("expected response body status 'ok', got %+v", res.Body)
	}
	if res.Latency.TotalRoundTrip <= 0 {
		t.Fatalf("expected round trip latency > 0, got %v", res.Latency.TotalRoundTrip)
	}
}

func TestRunHealthCheck_UnhealthyStatus(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	defer server.Close()

	res := runHealthCheck(server.URL, 2*time.Second)

	if res.Healthy {
		t.Fatalf("expected healthy false for 503 status, got true")
	}
	if res.HTTPStatus != http.StatusServiceUnavailable {
		t.Fatalf("expected status 503, got %d", res.HTTPStatus)
	}
}

func TestRunHealthCheck_TimeoutOrConnectionRefused(t *testing.T) {
	res := runHealthCheck("http://127.0.0.1:59999/health", 100*time.Millisecond)
	if res.Healthy {
		t.Fatalf("expected unhealthy for invalid host, got healthy")
	}
	if res.Error == "" {
		t.Fatalf("expected non-empty error message")
	}
}
