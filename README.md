# Self-Healing Containerized Service on Kubernetes

A resilient microservice architecture designed for automated fault-recovery, horizontal scalability, and continuous observability on Kubernetes.

## Core Capabilities
- **Resilient Microservice**: High-throughput batch ETL processing service with exponential backoff and structured telemetry.
- **Self-Healing Orchestration**: Kubernetes health probes and auto-recovery mechanisms for handling unhandled failures and deadlocks.
- **Zero-Trust Containerization**: Multi-stage, minimal attack-surface container running as an unprivileged user.
- **Synthetic Monitoring**: Go-based health inspection CLI with latency tracing.
- **Infrastructure as Code**: Modular Terraform definitions targeting local clusters and cloud environments.
- **Host Configuration**: Automated node prerequisite configuration via Ansible.
- **Observability**: Prometheus metric instrumentation and Grafana dashboard visualization.
- **Continuous Delivery**: Automated CI/CD pipeline with unit testing and container image publishing.
