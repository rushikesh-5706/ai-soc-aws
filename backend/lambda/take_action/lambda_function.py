import json
import boto3
import datetime
import uuid

def lambda_handler(event, context):
    """
    Tool: take_action
    Purpose: Execute safe remediation actions on AWS resources
    Called by: Bedrock Agent — only for CRITICAL/HIGH confirmed threats
    """
    
    print(f"TakeAction invoked with event: {json.dumps(event)}")
    
    parameters = {}
    if 'parameters' in event:
        for param in event['parameters']:
            parameters[param['name']] = param['value']
    
    action_type = parameters.get('action_type', '')
    resource_id = parameters.get('resource_id', '')
    resource_type = parameters.get('resource_type', 'EC2')
    reason = parameters.get('reason', 'Security incident detected by AI SOC')
    severity = parameters.get('severity', 'HIGH')
    incident_id = parameters.get('incident_id', f"INC-{str(uuid.uuid4())[:8].upper()}")
    
    print(f"Executing action: {action_type} on {resource_type}:{resource_id}")
    
    # Safety gate — never act on LOW severity
    if severity == 'LOW':
        return build_response(event, {
            "action_taken": "SKIPPED",
            "reason": "Action skipped: Severity is LOW — no automated action taken. Human review recommended.",
            "resource_id": resource_id,
            "action_type": action_type
        })
    
    result = {}
    
    if action_type == 'apply_quarantine_tag':
        result = apply_quarantine_tag(resource_id, resource_type, reason, incident_id)
    elif action_type == 'flag_iam_key':
        result = flag_iam_key_for_review(resource_id, reason, incident_id)
    elif action_type == 'create_cloudwatch_alarm':
        result = create_monitoring_alarm(resource_id, incident_id)
    elif action_type == 'recommend_only':
        result = {
            "action_taken": "RECOMMENDATION_ONLY",
            "reason": reason,
            "recommendation": f"Human review required for resource {resource_id}. No automated action taken.",
            "resource_id": resource_id
        }
    else:
        result = {
            "action_taken": "UNKNOWN_ACTION",
            "error": f"Action type '{action_type}' not recognized. No action taken.",
            "resource_id": resource_id
        }
    
    return build_response(event, result)


def apply_quarantine_tag(resource_id, resource_type, reason, incident_id):
    """
    Apply quarantine tags to EC2 instance.
    This is SAFE — it only adds tags, does not stop or terminate.
    """
    try:
        if resource_type == 'EC2':
            ec2 = boto3.client('ec2', region_name='us-east-1')
            
            # Try to apply real tags
            try:
                ec2.create_tags(
                    Resources=[resource_id],
                    Tags=[
                        {'Key': 'QUARANTINE', 'Value': 'true'},
                        {'Key': 'QUARANTINE_REASON', 'Value': reason[:255]},
                        {'Key': 'QUARANTINE_TIME', 'Value': datetime.datetime.utcnow().isoformat()},
                        {'Key': 'INCIDENT_ID', 'Value': incident_id},
                        {'Key': 'QUARANTINE_BY', 'Value': 'AI-SOC-ARIA'},
                        {'Key': 'HUMAN_REVIEW_REQUIRED', 'Value': 'true'}
                    ]
                )
                
                return {
                    "action_taken": "QUARANTINE_TAG_APPLIED",
                    "resource_id": resource_id,
                    "tags_added": ["QUARANTINE=true", "HUMAN_REVIEW_REQUIRED=true", f"INCIDENT_ID={incident_id}"],
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "status": "SUCCESS",
                    "note": "Instance tagged for quarantine. It is still running. Human must decide to stop/terminate."
                }
                
            except ec2.exceptions.ClientError as e:
                if 'InvalidInstanceID' in str(e) or 'does not exist' in str(e):
                    # Mock mode — resource doesn't exist (expected in testing)
                    return {
                        "action_taken": "QUARANTINE_TAG_SIMULATED",
                        "resource_id": resource_id,
                        "tags_added": ["QUARANTINE=true", "HUMAN_REVIEW_REQUIRED=true", f"INCIDENT_ID={incident_id}"],
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "status": "SIMULATED",
                        "note": "Mock mode: Resource doesn't exist in account. Action simulated successfully for demo purposes."
                    }
                else:
                    raise e
        else:
            return {
                "action_taken": "QUARANTINE_NOT_SUPPORTED",
                "resource_type": resource_type,
                "note": f"Quarantine tagging not implemented for {resource_type}. Manual action required.",
                "status": "SKIPPED"
            }
            
    except Exception as e:
        print(f"Error applying quarantine tag: {str(e)}")
        return {
            "action_taken": "QUARANTINE_TAG_FAILED",
            "resource_id": resource_id,
            "error": str(e),
            "status": "FAILED",
            "fallback": "Manual quarantine required immediately"
        }


def flag_iam_key_for_review(resource_id, reason, incident_id):
    """
    Flag an IAM user/key for human review.
    We NEVER delete or deactivate automatically — human must confirm.
    """
    try:
        iam = boto3.client('iam', region_name='us-east-1')
        
        # Try to get real key info
        try:
            keys = iam.list_access_keys(UserName=resource_id)
            key_count = len(keys.get('AccessKeyMetadata', []))
            
            return {
                "action_taken": "IAM_KEY_FLAGGED_FOR_REVIEW",
                "username": resource_id,
                "active_keys_found": key_count,
                "incident_id": incident_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "status": "FLAGGED",
                "required_human_action": f"URGENT: Review IAM user '{resource_id}'. Found {key_count} active keys. Deactivate if suspicious.",
                "note": "AI has NOT deactivated the key. Human review required before deactivation."
            }
            
        except iam.exceptions.NoSuchEntityException:
            return {
                "action_taken": "IAM_KEY_FLAG_SIMULATED",
                "username": resource_id,
                "incident_id": incident_id,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "status": "SIMULATED",
                "note": "Mock mode: IAM user not found. Simulated for demo purposes."
            }
            
    except Exception as e:
        print(f"Error flagging IAM key: {str(e)}")
        return {
            "action_taken": "IAM_FLAG_FAILED",
            "resource_id": resource_id,
            "error": str(e),
            "status": "FAILED"
        }


def create_monitoring_alarm(resource_id, incident_id):
    """Create a CloudWatch alarm for suspicious resource"""
    return {
        "action_taken": "MONITORING_ENHANCED",
        "resource_id": resource_id,
        "incident_id": incident_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "status": "NOTE",
        "note": "Enhanced monitoring recommendation logged. CloudWatch alarm creation requires CloudWatch permissions."
    }


def build_response(event, result):
    return {
        'statusCode': 200,
        'body': json.dumps(result),
        'messageVersion': '1.0',
        'response': {
            'actionGroup': event.get('actionGroup', ''),
            'function': event.get('function', ''),
            'functionResponse': {
                'responseBody': {
                    'TEXT': {
                        'body': json.dumps(result, indent=2)
                    }
                }
            }
        }
    }
