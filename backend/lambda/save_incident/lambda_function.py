import json
import boto3
import datetime
import uuid


dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table = dynamodb.Table("AISoc-Incidents")


def lambda_handler(event, context):
    print(f"SaveIncident invoked with event: {json.dumps(event)}")

    parameters = {}
    if "parameters" in event:
        for param in event["parameters"]:
            parameters[param["name"]] = param["value"]

    incident_id = parameters.get("incident_id", "INC-" + str(uuid.uuid4())[:8].upper())
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    action_taken = parameters.get("action_taken", "NONE")

    if action_taken in ("NONE", "RECOMMEND_ONLY", "RECOMMENDATION_ONLY"):
        status = "OPEN"
    elif action_taken in ("QUARANTINE_TAG_APPLIED", "IAM_KEY_FLAGGED_FOR_REVIEW"):
        status = "INVESTIGATING"
    else:
        status = "OPEN"

    item = {
        "incident_id": incident_id,
        "timestamp": timestamp,
        "alert_type": parameters.get("alert_type", "UNKNOWN"),
        "severity": parameters.get("severity", "MEDIUM"),
        "resource_id": parameters.get("resource_id", "unknown"),
        "resource_type": parameters.get("resource_type", "UNKNOWN"),
        "source_ip": parameters.get("source_ip", "unknown"),
        "agent_reasoning": parameters.get("agent_reasoning", "No reasoning provided"),
        "action_taken": action_taken,
        "action_result": parameters.get("action_result", "N/A"),
        "false_positive": parameters.get("false_positive", "false").lower() == "true",
        "status": status,
        "raw_alert": parameters.get("raw_alert", "{}"),
        "created_by": "AI-SOC-ARIA",
        "ttl": int((datetime.datetime.utcnow() + datetime.timedelta(days=90)).timestamp()),
    }

    try:
        table.put_item(Item=item)
        print("Successfully saved incident " + incident_id)
        result = {
            "status": "SAVED",
            "incident_id": incident_id,
            "timestamp": timestamp,
            "message": "Incident " + incident_id + " successfully logged to DynamoDB",
        }

    except Exception as e:
        print("Error saving to DynamoDB: " + str(e))
        result = {
            "status": "SAVE_FAILED",
            "incident_id": incident_id,
            "error": str(e),
            "message": "Failed to save. Check Lambda role has dynamodb:PutItem permission.",
        }

    return {
        "statusCode": 200,
        "body": json.dumps(result),
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "function": event.get("function", ""),
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": json.dumps(result, indent=2)
                    }
                }
            },
        },
    }
