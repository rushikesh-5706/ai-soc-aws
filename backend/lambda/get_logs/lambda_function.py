import json
import boto3
import datetime
import random

def lambda_handler(event, context):
    """
    Tool: get_logs
    Purpose: Retrieve CloudTrail events and context for a given resource
    Called by: Bedrock Agent as an action group tool
    """
    
    print(f"GetLogs invoked with event: {json.dumps(event)}")
    
    # Extract parameters from Bedrock Agent action group call
    parameters = {}
    if 'parameters' in event:
        for param in event['parameters']:
            parameters[param['name']] = param['value']
    
    resource_id = parameters.get('resource_id', 'unknown')
    resource_type = parameters.get('resource_type', 'EC2')
    time_window_hours = int(parameters.get('time_window_hours', '24'))
    
    print(f"Fetching logs for resource: {resource_id}, type: {resource_type}")
    
    # Try real CloudTrail first
    logs = []
    try:
        cloudtrail_client = boto3.client('cloudtrail', region_name='us-east-1')
        end_time = datetime.datetime.utcnow()
        start_time = end_time - datetime.timedelta(hours=time_window_hours)
        
        response = cloudtrail_client.lookup_events(
            LookupAttributes=[
                {
                    'AttributeKey': 'ResourceName',
                    'AttributeValue': resource_id
                }
            ],
            StartTime=start_time,
            EndTime=end_time,
            MaxResults=20
        )
        
        for event in response.get('Events', []):
            logs.append({
                'event_name': event.get('EventName', 'Unknown'),
                'event_time': event.get('EventTime', '').isoformat() if event.get('EventTime') else '',
                'username': event.get('Username', 'Unknown'),
                'source_ip': event.get('CloudTrailEvent', '{}'),
                'event_source': event.get('EventSource', 'Unknown')
            })
        
        print(f"Found {len(logs)} real CloudTrail events")
        
    except Exception as e:
        print(f"CloudTrail lookup failed (expected for mock): {str(e)}")
        logs = []
    
    # If no real logs found, generate contextual mock data
    if not logs:
        logs = generate_mock_logs(resource_id, resource_type)
    
    # Analyze patterns in logs
    analysis = analyze_log_patterns(logs, resource_id, resource_type)
    
    result = {
        "resource_id": resource_id,
        "resource_type": resource_type,
        "time_window_hours": time_window_hours,
        "log_count": len(logs),
        "recent_events": logs[:10],  # Last 10 events
        "pattern_analysis": analysis,
        "data_source": "cloudtrail" if len(logs) > 0 and 'mock' not in str(logs[0]) else "mock_data"
    }
    
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


def generate_mock_logs(resource_id, resource_type):
    """Generate realistic mock log data for testing"""
    now = datetime.datetime.utcnow()
    
    if resource_type == 'EC2':
        return [
            {
                'event_name': 'AuthorizeSecurityGroupIngress',
                'event_time': (now - datetime.timedelta(hours=2)).isoformat(),
                'username': 'admin-user',
                'source_ip': '203.0.113.45',
                'event_source': 'ec2.amazonaws.com',
                'data_source': 'mock'
            },
            {
                'event_name': 'DescribeInstances',
                'event_time': (now - datetime.timedelta(hours=4)).isoformat(),
                'username': 'readonly-bot',
                'source_ip': '10.0.1.100',
                'event_source': 'ec2.amazonaws.com',
                'data_source': 'mock'
            },
            {
                'event_name': 'StartInstances',
                'event_time': (now - datetime.timedelta(hours=48)).isoformat(),
                'username': 'deployment-user',
                'source_ip': '10.0.0.50',
                'event_source': 'ec2.amazonaws.com',
                'data_source': 'mock'
            }
        ]
    elif resource_type == 'IAM':
        return [
            {
                'event_name': 'CreateAccessKey',
                'event_time': (now - datetime.timedelta(hours=1)).isoformat(),
                'username': 'suspicious-user',
                'source_ip': '185.220.101.34',
                'event_source': 'iam.amazonaws.com',
                'data_source': 'mock'
            },
            {
                'event_name': 'AttachUserPolicy',
                'event_time': (now - datetime.timedelta(minutes=30)).isoformat(),
                'username': 'suspicious-user',
                'source_ip': '185.220.101.34',
                'event_source': 'iam.amazonaws.com',
                'data_source': 'mock'
            },
            {
                'event_name': 'ListUsers',
                'event_time': (now - datetime.timedelta(minutes=20)).isoformat(),
                'username': 'suspicious-user',
                'source_ip': '185.220.101.34',
                'event_source': 'iam.amazonaws.com',
                'data_source': 'mock'
            }
        ]
    else:
        return [
            {
                'event_name': 'GetObject',
                'event_time': (now - datetime.timedelta(hours=3)).isoformat(),
                'username': 'unknown',
                'source_ip': '198.51.100.22',
                'event_source': 's3.amazonaws.com',
                'data_source': 'mock'
            }
        ]


def analyze_log_patterns(logs, resource_id, resource_type):
    """Analyze logs to detect suspicious patterns"""
    if not logs:
        return {
            "pattern": "NO_LOGS",
            "summary": "No log data available for this resource in the specified time window",
            "suspicious_indicators": [],
            "recommendation": "Proceed with caution - assess alert on its own merits"
        }
    
    suspicious_indicators = []
    external_ips = set()
    
    for log in logs:
        ip = log.get('source_ip', '')
        # Check for external IPs (not RFC 1918 private)
        if ip and not (
            ip.startswith('10.') or 
            ip.startswith('192.168.') or 
            ip.startswith('172.') or
            ip in ['', 'Unknown', 'AWS Internal']
        ):
            external_ips.add(ip)
    
    if len(external_ips) > 2:
        suspicious_indicators.append(f"Multiple external IPs detected: {list(external_ips)}")
    
    privileged_actions = ['CreateAccessKey', 'AttachUserPolicy', 'AuthorizeSecurityGroupIngress', 
                          'CreateRole', 'PutUserPolicy', 'CreateUser']
    
    for log in logs:
        if log.get('event_name') in privileged_actions:
            suspicious_indicators.append(f"Privileged action detected: {log.get('event_name')} at {log.get('event_time')}")
    
    return {
        "pattern": "SUSPICIOUS" if suspicious_indicators else "NORMAL",
        "total_events": len(logs),
        "unique_source_ips": list(external_ips),
        "suspicious_indicators": suspicious_indicators,
        "summary": f"Found {len(logs)} events. {'Multiple suspicious indicators detected.' if suspicious_indicators else 'No obvious suspicious patterns in recent activity.'}"
    }
