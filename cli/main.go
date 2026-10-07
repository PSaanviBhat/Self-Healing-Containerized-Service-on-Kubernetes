package main

import (
	"context"
	"crypto/tls"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"net/http/httptrace"
	"os"
	"time"
)

type HealthResponse struct {
	Status   string `json:"status"`
	Service  string `json:"service"`
	Version  string `json:"version"`
	Degraded bool   `json:"degraded"`
}

type LatencyTrace struct {
	DNSLookupDuration time.Duration `json:"dns_lookup_ms"`
	TCPConnectDuration time.Duration `json:"tcp_connect_ms"`
	TLSHandshakeDuration time.Duration `json:"tls_handshake_ms"`
	TotalRoundTrip    time.Duration `json:"total_round_trip_ms"`
}

type CheckResult struct {
	Endpoint   string          `json:"endpoint"`
	HTTPStatus int             `json:"http_status"`
	Healthy    bool            `json:"healthy"`
	Latency    LatencyTrace    `json:"latency"`
	Body       *HealthResponse `json:"body,omitempty"`
	Error      string          `json:"error,omitempty"`
}

func main() {
	endpoint := flag.String("url", "http://localhost:8000/health", "Target service health endpoint URL")
	timeout := flag.Duration("timeout", 5*time.Second, "Timeout for health check probe")
	jsonOutput := flag.Bool("json", false, "Output results in JSON format")
	flag.Parse()

	result := runHealthCheck(*endpoint, *timeout)

	if *jsonOutput {
		enc := json.NewEncoder(os.Stdout)
		enc.SetIndent("", "  ")
		_ = enc.Encode(result)
	} else {
		printHumanResult(result)
	}

	if !result.Healthy {
		os.Exit(1)
	}
}

func runHealthCheck(endpoint string, timeout time.Duration) CheckResult {
	result := CheckResult{
		Endpoint: endpoint,
	}

	var dnsStart, dnsDone time.Time
	var connStart, connDone time.Time
	var tlsStart, tlsDone time.Time

	ctx, cancel := context.WithTimeout(context.Background(), timeout)
	defer cancel()

	trace := &httptrace.ClientTrace{
		DNSStart: func(_ httptrace.DNSStartInfo) { dnsStart = time.Now() },
		DNSDone:  func(_ httptrace.DNSDoneInfo) { dnsDone = time.Now() },
		ConnectStart: func(_, _ string) { connStart = time.Now() },
		ConnectDone:  func(_, _ string, _ error) { connDone = time.Now() },
		TLSHandshakeStart: func() { tlsStart = time.Now() },
		TLSHandshakeDone:  func(_ tls.ConnectionState, _ error) { tlsDone = time.Now() },
	}

	req, err := http.NewRequestWithContext(httptrace.WithClientTrace(ctx, trace), http.MethodGet, endpoint, nil)
	if err != nil {
		result.Error = fmt.Sprintf("Failed to build HTTP request: %v", err)
		return result
	}

	client := &http.Client{}
	start := time.Now()
	resp, err := client.Do(req)
	totalDuration := time.Since(start)

	if !dnsStart.IsZero() && !dnsDone.IsZero() {
		result.Latency.DNSLookupDuration = dnsDone.Sub(dnsStart)
	}
	if !connStart.IsZero() && !connDone.IsZero() {
		result.Latency.TCPConnectDuration = connDone.Sub(connStart)
	}
	if !tlsStart.IsZero() && !tlsDone.IsZero() {
		result.Latency.TLSHandshakeDuration = tlsDone.Sub(tlsStart)
	}
	result.Latency.TotalRoundTrip = totalDuration

	if err != nil {
		result.Error = fmt.Sprintf("HTTP request failed: %v", err)
		return result
	}
	defer resp.Body.Close()

	result.HTTPStatus = resp.StatusCode

	bodyBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		result.Error = fmt.Sprintf("Failed reading response payload: %v", err)
		return result
	}

	var health HealthResponse
	if err := json.Unmarshal(bodyBytes, &health); err == nil {
		result.Body = &health
	}

	if resp.StatusCode == http.StatusOK && (health.Status == "ok" || health.Status == "ready") {
		result.Healthy = true
	} else {
		result.Healthy = false
	}

	return result
}

func printHumanResult(r CheckResult) {
	fmt.Println("==================================================")
	fmt.Println("       SERVICE HEALTH INSPECTION PROBE            ")
	fmt.Println("==================================================")
	fmt.Printf("Endpoint:       %s\n", r.Endpoint)
	fmt.Printf("HTTP Status:    %d\n", r.HTTPStatus)

	if r.Healthy {
		fmt.Printf("Health State:   \033[32m[HEALTHY]\033[0m\n")
	} else {
		fmt.Printf("Health State:   \033[31m[UNHEALTHY]\033[0m\n")
	}

	if r.Body != nil {
		fmt.Printf("Service Name:   %s\n", r.Body.Service)
		fmt.Printf("Version:        %s\n", r.Body.Version)
		fmt.Printf("Degraded:       %t\n", r.Body.Degraded)
	}

	fmt.Println("----------------- Latency Breakdown -------------")
	fmt.Printf("Total RTT:      %v\n", r.Latency.TotalRoundTrip)
	if r.Latency.DNSLookupDuration > 0 {
		fmt.Printf("DNS Lookup:     %v\n", r.Latency.DNSLookupDuration)
	}
	if r.Latency.TCPConnectDuration > 0 {
		fmt.Printf("TCP Connect:    %v\n", r.Latency.TCPConnectDuration)
	}
	if r.Error != "" {
		fmt.Printf("Error Details:  %s\n", r.Error)
	}
	fmt.Println("==================================================")
}
