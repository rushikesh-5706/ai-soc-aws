import json
import boto3
import datetime
import os

def lambda_handler(event, context):
    print(f"GetLogs invoked with event: {json.dumps(event)}")

    parameters = {}
    if "parameters" in event:
        for param in event["parameters"]:
            parameters[param["name"]] = param["value"]

    resource_id        = parameters.get("resource_id", "unknown")
    resource_type      = parameters.get("resource_type", "EC2")
    time_window_hours  = int(parameters.get("time_window_hours", "24"))

    print(f"Fetching logs for resource: {resource_id}, type: {resource_type}")

    logs = []
    try:
        cloudtrail_client = boto3.client("cloudtrail", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        end_time   = datetime.datetime.utcnow()
        start_time = end_time - datetime.timedelta(hours=time_window_hours)

        response = cloudtrail_client.lookup_events(
            LookupAttributes=[
                {"AttributeKey": "ResourceName", "AttributeValue": resource_id}
            ],
            StartTime=start_time,
            EndTime=end_time,
            MaxResults=20,
        )

        for ct_event in response.get("Events", []):
            logs.append({
                "event_name":   ct_event.get("EventName", "Unknown"),
                "event_time":   ct_event.get("EventTime", "").isoformat()
                                if ct_event.get("EventTime") else "",
                "username":     ct_event.get("Username", "Unknown"),
                "event_source": ct_event.get("EventSource", "Unknown"),
                "data_source":  "cloudtrail",
            })

        print(f"Found {len(logs)} real CloudTrail events")

    except Exception as e:
        print(f"CloudTrail lookup failed (using mock data): {str(e)}")
        logs = []

    if not logs:
        logs = generate_mock_logs(resource_id, resource_type)

    analysis = analyze_log_patterns(logs, resource_id, resource_type)

    result = {
        "resource_id":       resource_id,
        "resource_type":     resource_type,
        "time_window_hours": time_window_hours,
        "log_count":         len(logs),
        "recent_events":     logs[:10],
        "pattern_analysis":  analysis,
        "data_source":       "cloudtrail" if logs and logs[0].get("data_source") == "cloudtrail"
                             else "mock_data",
    }

    return {
        "statusCode": 200,
        "body": json.dumps(result),
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "function":    event.get("function", ""),
            "functionResponse": {
                "responseBody": {
                    "TEXT": {"body": json.dumps(result) if result else "Action completed successfully"}
                }
            },
        },
    }


def generate_mock_logs(resource_id, resource_type):
    now = datetime.datetime.utcnow()

    if resource_type == "IAM":
        return [
            {"event_name": "CreateAccessKey",  "event_time": (now - datetime.timedelta(hours=1)).isoformat(),    "username": "suspicious-user", "source_ip": "185.220.101.34", "event_source": "iam.amazonaws.com", "data_source": "mock"},
            {"event_name": "AttachUserPolicy", "event_time": (now - datetime.timedelta(minutes=30)).isoformat(), "username": "suspicious-user", "source_ip": "185.220.101.34", "event_source": "iam.amazonaws.com", "data_source": "mock"},
            {"event_name": "CreateUser",       "event_time": (now - datetime.timedelta(minutes=15)).isoformat(), "username": "suspicious-user", "source_ip": "185.220.101.34", "event_source": "iam.amazonaws.com", "data_source": "mock"},
        ]

    if resource_type == "S3":
        return [
            {"event_name": "GetObject", "event_time": (now - datetime.timedelta(hours=3)).isoformat(), "username": "unknown", "source_ip": "198.51.100.22", "event_source": "s3.amazonaws.com", "data_source": "mock"},
        ]

    # Default: EC2
    return [
        {"event_name": "AuthorizeSecurityGroupIngress", "event_time": (now - datetime.timedelta(hours=2)).isoformat(),  "username": "admin-user",       "source_ip": "203.0.113.45", "event_source": "ec2.amazonaws.com", "data_source": "mock"},
        {"event_name": "DescribeInstances",             "event_time": (now - datetime.timedelta(hours=4)).isoformat(),  "username": "readonly-bot",      "source_ip": "10.0.1.100",  "event_source": "ec2.amazonaws.com", "data_source": "mock"},
        {"event_name": "StartInstances",                "event_time": (now - datetime.timedelta(hours=48)).isoformat(), "username": "deployment-user",   "source_ip": "10.0.0.50",   "event_source": "ec2.amazonaws.com", "data_source": "mock"},
    ]


def analyze_log_patterns(logs, resource_id, resource_type):
    if not logs:
        return {
            "pattern":               "NO_LOGS",
            "summary":               "No log data available for this resource.",
            "suspicious_indicators": [],
            "recommendation":        "Assess alert on its own merits.",
        }

    suspicious_indicators = []
    external_ips = set()

    PRIVILEGED_ACTIONS = {
        "CreateAccessKey", "AttachUserPolicy", "AuthorizeSecurityGroupIngress",
        "CreateRole", "PutUserPolicy", "CreateUser", "DeleteTrail",
        "StopLogging", "ModifyDBInstance",
    }

    for log in logs:
        ip = log.get("source_ip", "")
        if ip and not (
            ip.startswith("10.")
            or ip.startswith("192.168.")
            or ip.startswith("172.")
            or ip in ("", "Unknown", "AWS Internal")
        ):
            external_ips.add(ip)

        if log.get("event_name") in PRIVILEGED_ACTIONS:
            suspicious_indicators.append(
                f"Privileged action: {log.get('event_name')} at {log.get('event_time')}"
            )

    if len(external_ips) > 1:
        suspicious_indicators.append(f"Multiple external IPs: {list(external_ips)}")

    return {
        "pattern":               "SUSPICIOUS" if suspicious_indicators else "NORMAL",
        "total_events":          len(logs),
        "unique_external_ips":   list(external_ips),
        "suspicious_indicators": suspicious_indicators,
        "summary": (
            f"{len(logs)} events found. "
            + ("Suspicious activity detected." if suspicious_indicators
               else "No obvious suspicious patterns.")
        ),
    }
