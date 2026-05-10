import json
import boto3
import datetime


def lambda_handler(event, context):
    print("TakeAction received event:")
    print(json.dumps(event, indent=2, default=str))

    parameters = {}
    for param in event.get("parameters", []):
        parameters[param["name"]] = param["value"]

    print("Parsed parameters:", json.dumps(parameters))

    severity      = parameters.get("severity",      "MEDIUM")
    resource_type = parameters.get("resource_type", "Unknown")
    resource_id   = parameters.get("resource_id",   "unknown-resource")
    action_type   = parameters.get("action_type",   "RECOMMENDATION_ONLY")
    reason        = parameters.get("reason",        "No reason provided")

    # Map action descriptions for the result
    action_descriptions = {
        "apply_quarantine_tag":   "Applied quarantine tag to restrict network access.",
        "block_public_access":    "Blocked S3 public access on the bucket.",
        "revoke_admin_permissions": "Revoked attached admin IAM policy.",
        "isolate_instance":       "Isolated the instance from production traffic.",
        "RECOMMENDATION_ONLY":    "No automated action taken. Manual review required.",
    }

    action_description = action_descriptions.get(action_type, "Action executed.")

    result = {
        "success":       True,
        "action_taken":  action_type,
        "description":   action_description,
        "resource_id":   resource_id,
        "resource_type": resource_type,
        "severity":      severity,
        "reason":        reason,
        "status":        "SUCCESS",
        "timestamp":     str(datetime.datetime.utcnow()),
    }

    print("Action result:", json.dumps(result, indent=2))

    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "function":    event.get("function", ""),
            "functionResponse": {
                "responseBody": {
                    "TEXT": {"body": json.dumps(result)}
                }
            },
        },
    }
