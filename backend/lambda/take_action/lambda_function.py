import json
import boto3
import datetime
import uuid

def lambda_handler(event, context):
    """
    Tool: take_action
    Purpose: Execute safe remediation actions on AWS resources
    Called by: Bedrock Agent
    """

    print("EVENT RECEIVED:")
    print(json.dumps(event))

    # Convert Bedrock parameters list into dictionary
    parameters = {}

    for param in event.get("parameters", []):
        parameters[param["name"]] = param["value"]

    # Extract parameters safely
    severity = parameters.get("severity", "LOW")
    resource_type = parameters.get("resource_type", "UNKNOWN")
    resource_id = parameters.get("resource_id", "UNKNOWN")
    action_type = parameters.get("action_type", "RECOMMENDATION_ONLY")
    reason = parameters.get("reason", "No reason provided")

    print("ACTION:", action_type)
    print("RESOURCE:", resource_id)

    # Simulated remediation action
    action_status = "SUCCESS"

    # Build result
    result = {
        "success": True,
        "action_taken": action_type,
        "resource_id": resource_id,
        "resource_type": resource_type,
        "severity": severity,
        "reason": reason,
        "status": action_status,
        "timestamp": str(datetime.datetime.utcnow())
    }

    # Bedrock Agent compatible response
    return {
        "messageVersion": "1.0",
        "response": {
            "actionGroup": event.get("actionGroup", ""),
            "function": event.get("function", ""),
            "functionResponse": {
                "responseBody": {
                    "TEXT": {
                        "body": json.dumps(result) if result else "Action completed successfully"
                    }
                }
            }
        }
    }
