# Production Monitoring, Log Aggregation & APM Setup

This document provides complete instructions for aggregating logs and configuring APM error tracking for the Prashant Group platform using **Sentry**, **AWS CloudWatch**, and **Datadog**.

---

## 1. Sentry Error Tracking & APM (Configured in Application)

The backend is pre-wired with native Sentry SDK integration (`backend/main.py`).

### How to Activate:
1. Sign up / log in to [sentry.io](https://sentry.io)
2. Create a new project: **Python / FastAPI**
3. Copy your project DSN: `https://<key>@<org>.ingest.sentry.io/<project_id>`
4. Add the DSN to `.env.production`:
   ```bash
   SENTRY_DSN="https://YOUR_KEY@YOUR_ORG.ingest.sentry.io/YOUR_PROJECT_ID"
   ```
5. When `SENTRY_DSN` is set and `ENVIRONMENT=production`:
   - Any unhandled 500 error or exception is captured automatically with full stack traces, request parameters, and user context.
   - Sentry Tracing automatically records API endpoint latency and database query spans.

---

## 2. AWS CloudWatch Log Aggregation

When deployed on AWS (EC2 / ECS / Lightsail), logs output by `uvicorn` are automatically structured in JSON format:

```json
{
  "timestamp": "2026-11-13 17:47:35",
  "level": "INFO",
  "logger": "prashant_group",
  "message": "GET /api/v1/admin/analytics status=200 duration_ms=46.9",
  "environment": "production"
}
```

### Setup via AWS CloudWatch Agent:
Install the CloudWatch agent:
```bash
sudo amazon-linux-extras install -y collectd
sudo yum install -y amazon-cloudwatch-agent
```

Configure `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`:
```json
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/nginx/prashant_access.log",
            "log_group_name": "/prashant-group/nginx/access",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/nginx/prashant_error.log",
            "log_group_name": "/prashant-group/nginx/error",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/prashant_app.log",
            "log_group_name": "/prashant-group/backend/application",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
```
Start the agent:
```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
```

---

## 3. Datadog Log Aggregation & APM

If using Datadog:
1. Install Datadog Agent:
   ```bash
   DD_API_KEY=YOUR_DD_API_KEY DD_SITE="datadoghq.com" bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"
   ```
2. Enable log collection in `/etc/datadog-agent/datadog.yaml`:
   ```yaml
   logs_enabled: true
   ```
3. Create `/etc/datadog-agent/conf.d/python.d/conf.yaml`:
   ```yaml
   logs:
     - type: file
       path: /var/log/prashant_app.log
       service: prashant-group-backend
       source: python
       sourcecategory: backend
   ```
4. Restart agent:
   ```bash
   sudo systemctl restart datadog-agent
   ```

---

## 4. Production Health Monitoring Alert Rules

Recommended alert thresholds:

| Metric | Warning Threshold | Critical Threshold | Action |
|--------|-------------------|--------------------|--------|
| HTTP 5xx Error Rate | > 1% of total reqs | > 5% of total reqs | Sentry / Slack alert |
| `/health` Status | Non-200 for 1 minute | Non-200 for 3 minutes | Auto-restart container |
| DB Connections | > 70 active | > 90 active | Scale pool or tune timeouts |
| Disk Free (Backups) | < 20% remaining | < 10% remaining | Purge old backups |
