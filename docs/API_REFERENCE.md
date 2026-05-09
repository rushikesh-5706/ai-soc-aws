# 📡 API Reference — AI SOC for AWS

> **Project Space 8.0 | Team 14**  
> Complete REST API documentation for the AI SOC backend

---

## Base URL

```
https://1wls2elsr0.execute-api.us-east-1.amazonaws.com/prod
```

---

## Endpoints

### `GET /incidents`

Fetches all security incidents from DynamoDB along with computed statistics, chart data, and analytics.

**Request:**
```http
GET /prod/incidents
Content-Type: application/json
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | `50` | Maximum number of incidents to return |

**Response (200 OK):**
```json
{
  "incidents": [
    {
      "incident_id": "INC-A1B2C3D4",
      "timestamp": "2025-05-09T10:30:00Z",
      "alert_type": "UnauthorizedAccess:EC2/SSHBruteForce",
      "resource_id": "i-0abc123mock456",
      "resource_type": "EC2",
      "source_ip": "185.220.101.34",
      "severity": "HIGH",
      "agent_reasoning": "Confirmed SSH brute force from Tor exit node. 300 attempts in 5 minutes.",
      "action_taken": "QUARANTINE_TAG_APPLIED",
      "action_result": "Tag SOC-Quarantine=true applied to i-0abc123mock456",
      "false_positive": false,
      "status": "INVESTIGATING",
      "created_by": "AI-SOC-ARIA"
    }
  ],
  "stats": {
    "total": 12,
    "critical": 2,
    "high": 4,
    "medium": 3,
    "low": 1,
    "false_positives": 2,
    "auto_actioned": 6,
    "pending_review": 4
  },
  "graphData": [
    { "day": "Mon", "incidents": 4 },
    { "day": "Tue", "incidents": 7 },
    { "day": "Wed", "incidents": 5 },
    { "day": "Thu", "incidents": 8 },
    { "day": "Fri", "incidents": 6 },
    { "day": "Sat", "incidents": 3 },
    { "day": "Sun", "incidents": 9 }
  ],
  "pieData": [
    { "name": "Critical", "value": 2 },
    { "name": "High",     "value": 4 },
    { "name": "Medium",   "value": 3 },
    { "name": "Low",      "value": 1 }
  ],
  "analytics": {
    "accuracy": "98%",
    "response_time": "12s",
    "monitoring": "24/7"
  }
}
```

**Error Responses:**

| Code | Description |
|------|-------------|
| `500` | Internal server error — check CloudWatch logs for AISoc-GetIncidents |

---

### `POST /chat`

Sends a message to ARIA (the Bedrock AI Agent) and returns her analysis response.

**Request:**
```http
POST /prod/chat
Content-Type: application/json

{
  "message": "Investigate this alert: SSH brute force on i-0abc123 from 185.220.101.34",
  "session_id": "chat-abc12345"
}
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | ✅ Yes | The question or alert to send to ARIA |
| `session_id` | string | ❌ No | Session ID for conversation continuity. Auto-generated if not provided. |

**Response (200 OK):**
```json
{
  "response": "=== ARIA INCIDENT ANALYSIS REPORT ===\n\nAlert Type: UnauthorizedAccess:EC2/SSHBruteForce\nResource: i-0abc123\nSource IP: 185.220.101.34\nSeverity: HIGH\nFalse Positive: NO\nAction Taken: QUARANTINE_TAG_APPLIED\n\nSummary:\nSSH brute force attack confirmed from known Tor exit node 185.220.101.34. CloudTrail logs show 300 login attempts in 5 minutes. Quarantine tag applied to EC2 instance. Recommend blocking IP at security group level.\n\nStatus: OPEN",
  "session_id": "chat-abc12345"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `response` | string | ARIA's full incident analysis report |
| `session_id` | string | Session ID for follow-up queries |

**Error Responses:**

| Code | Reason | Description |
|------|--------|-------------|
| `400` | `No message provided` | Request body missing `message` field |
| `500` | Exception string | Bedrock invocation failed — check CloudWatch |

---

## Bedrock Action Group Payloads (Internal)

These are the internal payloads exchanged between ARIA and the Lambda tools. Not called directly by the frontend.

### `get_logs`

```json
{
  "actionGroup": "soc-tools",
  "function": "get_logs",
  "parameters": [
    { "name": "resource_id",       "value": "i-0abc123mock456" },
    { "name": "resource_type",     "value": "EC2" },
    { "name": "time_window_hours", "value": "24" }
  ]
}
```

**Returns:**
```json
{
  "resource_id": "i-0abc123mock456",
  "resource_type": "EC2",
  "time_window_hours": 24,
  "log_count": 3,
  "recent_events": [
    {
      "event_name": "AuthorizeSecurityGroupIngress",
      "event_time": "2025-05-09T08:30:00",
      "username": "admin-user",
      "source_ip": "203.0.113.45",
      "event_source": "ec2.amazonaws.com",
      "data_source": "cloudtrail"
    }
  ],
  "pattern_analysis": {
    "pattern": "SUSPICIOUS",
    "total_events": 3,
    "unique_external_ips": ["203.0.113.45"],
    "suspicious_indicators": ["Privileged action: AuthorizeSecurityGroupIngress at 2025-05-09T08:30:00"],
    "summary": "3 events found. Suspicious activity detected."
  }
}
```

### `take_action`

```json
{
  "actionGroup": "soc-tools",
  "function": "take_action",
  "parameters": [
    { "name": "action_type",   "value": "apply_quarantine_tag" },
    { "name": "resource_id",   "value": "i-0abc123mock456" },
    { "name": "resource_type", "value": "EC2" },
    { "name": "severity",      "value": "HIGH" },
    { "name": "reason",        "value": "SSH brute force from Tor exit node confirmed in CloudTrail logs" }
  ]
}
```

**Returns:**
```json
{
  "success": true,
  "action_taken": "apply_quarantine_tag",
  "resource_id": "i-0abc123mock456",
  "resource_type": "EC2",
  "severity": "HIGH",
  "status": "SUCCESS",
  "timestamp": "2025-05-09 10:30:00"
}
```

### `save_incident`

```json
{
  "actionGroup": "soc-tools",
  "function": "save_incident",
  "parameters": [
    { "name": "incident_id",      "value": "INC-A1B2C3D4" },
    { "name": "alert_type",       "value": "UnauthorizedAccess:EC2/SSHBruteForce" },
    { "name": "severity",         "value": "HIGH" },
    { "name": "resource_id",      "value": "i-0abc123mock456" },
    { "name": "resource_type",    "value": "EC2" },
    { "name": "source_ip",        "value": "185.220.101.34" },
    { "name": "agent_reasoning",  "value": "Brute force confirmed. 300 attempts in 5 minutes from Tor node." },
    { "name": "action_taken",     "value": "QUARANTINE_TAG_APPLIED" },
    { "name": "action_result",    "value": "Tag applied successfully" },
    { "name": "false_positive",   "value": "false" }
  ]
}
```

**Returns:**
```json
{
  "status": "SAVED",
  "incident_id": "INC-A1B2C3D4",
  "timestamp": "2025-05-09T10:30:00.000Z",
  "message": "Incident INC-A1B2C3D4 successfully logged to DynamoDB"
}
```

---

## Mock Event Schema (EventBridge)

Use this schema to inject test events via AWS CLI:

```json
{
  "source": "custom.aisoc.mock",
  "detail-type": "MockSecurityAlert",
  "detail": {
    "alert_type": "UnauthorizedAccess:EC2/SSHBruteForce",
    "resource_id": "i-0abc123mock456",
    "resource_type": "EC2",
    "severity": 7.0,
    "source_ip": "185.220.101.34",
    "region": "us-east-1",
    "timestamp": "2025-05-09T10:30:00Z",
    "description": "300 SSH login attempts in 5 minutes",
    "account_id": "123456789012"
  }
}
```

---

*— AI SOC for AWS · Project Space 8.0 · Team 14 —*
