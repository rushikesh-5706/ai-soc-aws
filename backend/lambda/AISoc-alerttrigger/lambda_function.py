import json
import boto3
import uuid
import os

def lambda_handler(event, context):

    print("EVENT RECEIVED:")
    print(json.dumps(event))

    # Region from environment variable with safe fallback
    AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

    bedrock_agent_runtime = boto3.client(
        'bedrock-agent-runtime',
        region_name=AWS_REGION
    )

    # Agent IDs from environment variables with safe fallback
    AGENT_ID = os.environ.get("AGENT_ID", "UOSNOXLWJD")
    AGENT_ALIAS_ID = os.environ.get("AGENT_ALIAS_ID", "02PQZAH3MY")

    # Extract EventBridge detail payload
    if 'detail' in event:
        alert_data = event['detail']
    else:
        alert_data = event

    alert_text = json.dumps(alert_data)

    session_id = f"session-{uuid.uuid4()}"

    try:

        print("INVOKING BEDROCK AGENT...")

        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=alert_text,
            enableTrace=True
        )

        final_response = ""

        # Process streaming response properly
        for event_stream in response.get("completion", []):

            print("STREAM EVENT:")
            print(event_stream)

            # Agent response chunks
            if "chunk" in event_stream:

                chunk = event_stream["chunk"]

                if "bytes" in chunk:
                    decoded_chunk = chunk["bytes"].decode("utf-8")
                    final_response += decoded_chunk

            # Trace events help Bedrock complete orchestration
            if "trace" in event_stream:
                print("TRACE EVENT DETECTED")

        print("FINAL RESPONSE:")
        print(final_response)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'SUCCESS',
                'session_id': session_id,
                'agent_response': final_response
            })
        }

    except Exception as e:

        print("ERROR OCCURRED:")
        print(str(e))

        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'FAILED',
                'error': str(e)
            })
        }
