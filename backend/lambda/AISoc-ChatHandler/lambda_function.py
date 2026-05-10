import json
import boto3
import uuid
import os

def lambda_handler(event, context):

    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }

    # Handle CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }

    try:

        # Parse frontend request
        body = json.loads(event.get('body', '{}'))

        user_message = body.get('message', '')
        session_id = body.get(
            'session_id',
            f"chat-{str(uuid.uuid4())[:8]}"
        )

        if not user_message:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'No message provided'
                })
            }

        # Bedrock Runtime Client
        bedrock_agent_runtime = boto3.client(
            'bedrock-agent-runtime',
            region_name=os.environ.get('AWS_REGION', 'us-east-1')
        )

        # Agent Details
        AGENT_ID = os.environ.get(
            'AGENT_ID',
            'UOSNOXLWJD'
        )

        AGENT_ALIAS_ID = os.environ.get(
            'AGENT_ALIAS_ID',
            '0YQZSD4HA6'
        )

        # Invoke Agent
        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=user_message
        )

        print("FULL BEDROCK RESPONSE")
        print(response)

        # Read Streaming Response
        full_response = ""

        for event_chunk in response.get('completion', []):

            print("EVENT CHUNK:")
            print(event_chunk)

            if 'chunk' in event_chunk:

                chunk_data = event_chunk['chunk']

                if 'bytes' in chunk_data:

                    decoded_chunk = chunk_data['bytes'].decode('utf-8')

                    print("DECODED CHUNK:")
                    print(decoded_chunk)

                    full_response += decoded_chunk

        # Empty response fallback
        if not full_response.strip():
            full_response = "AI could not generate a response."

        print("FINAL AI RESPONSE")
        print(full_response)

        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'response': full_response,
                'session_id': session_id
            })
        }

    except Exception as e:

        print("ERROR OCCURRED")
        print(str(e))

        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': str(e)
            })
        }
