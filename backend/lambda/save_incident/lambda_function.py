import json
import boto3
import datetime
import uuid
import os

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = os.environ.get("DYNAMODB_TABLE", "AISoc-Incidents")

dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table(TABLE_NAME)


def normalize(value, default):
    if value is None:
        return default
    value = str(value).strip()
    if value == "" or value.upper() in ("UNKNOWN", "NONE", "N/A", "NULL", "RECOMMEND_ONLY", "RECOMMENDATION_ONLY"):
        return default
    return value


def map_action(alert_type):
    mapping = {
        "UnauthorizedAccess:EC2/SSHBruteForce":              "apply_quarantine_tag",
        "Recon:S3/BucketPublicAccessGranted":                "block_public_access",
        "PrivilegeEscalation:IAMUser/AdminPolicyAttached":   "revoke_admin_permissions",
        "CryptoCurrency:EC2/BitcoinTool":                    "isolate_instance",
        "UnauthorizedAccess:RDS/MultipleFailedLogins":       "isolate_instance",
    }
    return mapping.get(alert_type, "RECOMMENDATION_ONLY")


def map_recommendation(alert_type):
    mapping = {
        "UnauthorizedAccess:EC2/SSHBruteForce":             "Quarantine the EC2 instance and investigate SSH access.",
        "Recon:S3/BucketPublicAccessGranted":               "Disable public access and review bucket policies.",
        "PrivilegeEscalation:IAMUser/AdminPolicyAttached":  "Remove the attached admin policy and review IAM permissions.",
        "CryptoCurrency:EC2/BitcoinTool":                   "Isolate the instance and terminate unauthorized mining software.",
        "UnauthorizedAccess:RDS/MultipleFailedLogins":      "Investigate repeated login failures and review database access.",
    }
    return mapping.get(alert_type, "Review the affected resource and investigate suspicious activity.")


def determine_status(action_taken):
    if action_taken in (
        "apply_quarantine_tag", "block_public_access",
        "revoke_admin_permissions", "isolate_instance",
    ):
        return "INVESTIGATING"
    return "OPEN"


def lambda_handler(event, context):
    print("SaveIncident received event:")
    print(json.dumps(event, indent=2, default=str))

    # Parse Bedrock parameters list into a dict
    parameters = {}
    for param in event.get("parameters", []):
        parameters[param["name"]] = param["value"]

    print("Parsed parameters:", json.dumps(parameters))

    # Extract with explicit fallbacks — fields should now be populated by ARIA
    alert_type    = normalize(parameters.get("alert_type"),    "UnknownAlert")
    resource_id   = normalize(parameters.get("resource_id"),   "unknown-resource")
    resource_type = normalize(parameters.get("resource_type"), "Unknown")
    severity      = normalize(parameters.get("severity"),      "MEDIUM")
    source_ip     = normalize(parameters.get("source_ip"),     "unknown")
    action_result = normalize(parameters.get("action_result"), "N/A")

    action_taken    = normalize(parameters.get("action_taken"),    map_action(alert_type))
    recommendation  = normalize(parameters.get("recommendation"),  map_recommendation(alert_type))
    agent_reasoning = normalize(parameters.get("agent_reasoning"),  "Automated analysis completed by ARIA.")

    false_positive = str(parameters.get("false_positive", "false")).lower() == "true"
    incident_id    = parameters.get("incident_id", "INC-" + str(uuid.uuid4())[:8].upper())
    timestamp      = datetime.datetime.utcnow().isoformat() + "Z"
    status         = determine_status(action_taken)

    raw_alert = (
        f"{alert_type} detected on {resource_type} resource {resource_id}. "
        f"Severity: {severity}. Source IP: {source_ip}."
    )

    item = {
        "incident_id":    incident_id,
        "timestamp":      timestamp,
        "alert_type":     alert_type,
        "severity":       severity,
        "resource_id":    resource_id,
        "resource_type":  resource_type,
        "source_ip":      source_ip,
        "agent_reasoning": agent_reasoning,
        "action_taken":   action_taken,
        "recommendation": recommendation,
        "action_result":  action_result,
        "false_positive": false_positive,
        "status":         status,
        "raw_alert":      raw_alert,
        "created_by":     "AI-SOC-ARIA",
        "ttl": int(
            (datetime.datetime.utcnow() + datetime.timedelta(days=90)).timestamp()
        ),
    }

    print("Saving item to DynamoDB:")
    print(json.dumps(item, indent=2))

    try:
        table.put_item(Item=item)
        print("Saved incident:", incident_id)

        result = {
            "status":         "SAVED",
            "incident_id":    incident_id,
            "timestamp":      timestamp,
            "alert_type":     alert_type,
            "resource_id":    resource_id,
            "resource_type":  resource_type,
            "severity":       severity,
            "source_ip":      source_ip,
            "action_taken":   action_taken,
            "recommendation": recommendation,
            "message":        f"Incident {incident_id} successfully logged to DynamoDB",
        }

    except Exception as e:
        print("DynamoDB error:", str(e))
        result = {
            "status":      "SAVE_FAILED",
            "incident_id": incident_id,
            "error":       str(e),
            "message":     "Failed to save. Check Lambda role has dynamodb:PutItem permission.",
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
                    "TEXT": {"body": json.dumps(result, indent=2)}
                }
            },
        },
    }
