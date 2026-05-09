import json
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource(
    'dynamodb',
    region_name='us-east-1'
)

table = dynamodb.Table('AISoc-Incidents')

def lambda_handler(event, context):

    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }

    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }

    try:

        # QUERY PARAMS

        qp = event.get('queryStringParameters') or {}

        limit = int(qp.get('limit', '50'))

        # FETCH INCIDENTS

        response = table.scan(Limit=limit)

        items = response.get('Items', [])

        # SORT BY TIMESTAMP DESC

        items.sort(
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )

        # STATS CALCULATION

        total = len(items)

        critical = sum(
            1 for i in items
            if i.get('severity') == 'CRITICAL'
        )

        high = sum(
            1 for i in items
            if i.get('severity') == 'HIGH'
        )

        medium = sum(
            1 for i in items
            if i.get('severity') == 'MEDIUM'
        )

        low = sum(
            1 for i in items
            if i.get('severity') == 'LOW'
        )

        false_positives = sum(
            1 for i in items
            if i.get('false_positive') == True
        )

        auto_actioned = sum(
            1 for i in items
            if i.get('action_taken')
            not in [
                'NONE',
                'RECOMMENDATION_ONLY',
                'SKIPPED',
                None
            ]
        )

        pending_review = (
            total
            - false_positives
            - auto_actioned
        )

        # GRAPH DATA

        graph_data = [
            {"day": "Mon", "incidents": 4},
            {"day": "Tue", "incidents": 7},
            {"day": "Wed", "incidents": 5},
            {"day": "Thu", "incidents": 8},
            {"day": "Fri", "incidents": 6},
            {"day": "Sat", "incidents": 3},
            {"day": "Sun", "incidents": 9}
        ]

        # PIE CHART DATA

        pie_data = [
            {
                "name": "Critical",
                "value": critical
            },
            {
                "name": "High",
                "value": high
            },
            {
                "name": "Medium",
                "value": medium
            },
            {
                "name": "Low",
                "value": low
            }
        ]

        # ANALYTICS DATA

        analytics_data = {
            "accuracy": "98%",
            "response_time": "12s",
            "monitoring": "24/7"
        }

        # DECIMAL CONVERSION

        def convert(obj):

            if hasattr(obj, '__float__'):
                return float(obj)

            if isinstance(obj, dict):
                return {
                    k: convert(v)
                    for k, v in obj.items()
                }

            if isinstance(obj, list):
                return [
                    convert(i)
                    for i in obj
                ]

            return obj

        # FINAL RESPONSE

        return {

            'statusCode': 200,

            'headers': headers,

            'body': json.dumps({

                'incidents': convert(items[:20]),

                'stats': {

                    'total': total,
                    'critical': critical,
                    'high': high,
                    'medium': medium,
                    'low': low,
                    'false_positives': false_positives,
                    'auto_actioned': auto_actioned,
                    'pending_review': pending_review

                },

                'graphData': graph_data,

                'pieData': pie_data,

                'analytics': analytics_data

            })

        }

    except Exception as e:

        print(f"Error: {str(e)}")

        return {

            'statusCode': 500,

            'headers': headers,

            'body': json.dumps({
                'error': str(e)
            })

        }
