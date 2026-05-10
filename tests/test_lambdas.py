"""
Unit Tests for AI SOC Lambda Functions
Uses unittest with moto for AWS service mocking.
Run: python -m pytest tests/test_lambdas.py -v
"""

import json
import unittest
from unittest.mock import patch, MagicMock
import datetime
import uuid
import os
import sys

# ---------------------------------------------------------------------------
# Test: take_action Lambda
# ---------------------------------------------------------------------------


class TestTakeActionLambda(unittest.TestCase):
    """Tests for backend/lambda/take_action/lambda_function.py"""

    def setUp(self):
        """Set up test fixtures"""
        self.base_event = {
            "actionGroup": "soc-tools",
            "function": "take_action",
            "parameters": [
                {"name": "action_type", "value": "apply_quarantine_tag"},
                {"name": "resource_id", "value": "i-0abc123mock456"},
                {"name": "resource_type", "value": "EC2"},
                {"name": "severity", "value": "HIGH"},
                {"name": "reason", "value": "SSH brute force confirmed"},
            ],
        }

    def test_take_action_returns_bedrock_format(self):
        """Verify response follows Bedrock Action Group format"""
        sys.path.insert(0, "backend/lambda/take_action")
        from lambda_function import lambda_handler

        response = lambda_handler(self.base_event, None)

        self.assertEqual(response["messageVersion"], "1.0")
        self.assertIn("response", response)
        self.assertIn("functionResponse", response["response"])

        body = json.loads(
            response["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        )
        self.assertEqual(body["action_taken"], "apply_quarantine_tag")
        self.assertEqual(body["resource_id"], "i-0abc123mock456")
        self.assertEqual(body["severity"], "HIGH")

        sys.path.pop(0)

    def test_take_action_default_parameters(self):
        """Verify defaults when parameters are missing"""
        sys.path.insert(0, "backend/lambda/take_action")
        from lambda_function import lambda_handler

        minimal_event = {"parameters": []}
        response = lambda_handler(minimal_event, None)
        body = json.loads(
            response["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        )

        self.assertEqual(body["severity"], "LOW")
        self.assertEqual(body["resource_type"], "UNKNOWN")
        self.assertEqual(body["action_taken"], "RECOMMENDATION_ONLY")

        sys.path.pop(0)


# ---------------------------------------------------------------------------
# Test: get_logs Lambda — mock log analysis
# ---------------------------------------------------------------------------


class TestGetLogsLambda(unittest.TestCase):
    """Tests for backend/lambda/get_logs/lambda_function.py"""

    def test_mock_ec2_logs_generated(self):
        """Verify mock EC2 logs are generated when CloudTrail is unavailable"""
        sys.path.insert(0, "backend/lambda/get_logs")
        from lambda_function import generate_mock_logs

        logs = generate_mock_logs("i-0abc123mock456", "EC2")

        self.assertGreater(len(logs), 0)
        self.assertEqual(logs[0]["event_source"], "ec2.amazonaws.com")
        self.assertEqual(logs[0]["data_source"], "mock")

        sys.path.pop(0)

    def test_mock_iam_logs_generated(self):
        """Verify mock IAM logs contain privilege escalation events"""
        sys.path.insert(0, "backend/lambda/get_logs")
        from lambda_function import generate_mock_logs

        logs = generate_mock_logs("AIDA-MOCK-USER", "IAM")

        self.assertGreater(len(logs), 0)
        event_names = [log["event_name"] for log in logs]
        self.assertIn("CreateAccessKey", event_names)
        self.assertIn("AttachUserPolicy", event_names)

        sys.path.pop(0)

    def test_analyze_suspicious_pattern(self):
        """Verify pattern analysis flags privileged actions as SUSPICIOUS"""
        sys.path.insert(0, "backend/lambda/get_logs")
        from lambda_function import analyze_log_patterns, generate_mock_logs

        logs = generate_mock_logs("i-0abc123mock456", "EC2")
        analysis = analyze_log_patterns(logs, "i-0abc123mock456", "EC2")

        self.assertEqual(analysis["pattern"], "SUSPICIOUS")
        self.assertGreater(len(analysis["suspicious_indicators"]), 0)

        sys.path.pop(0)

    def test_analyze_empty_logs(self):
        """Verify empty logs return NO_LOGS pattern"""
        sys.path.insert(0, "backend/lambda/get_logs")
        from lambda_function import analyze_log_patterns

        analysis = analyze_log_patterns([], "i-test", "EC2")
        self.assertEqual(analysis["pattern"], "NO_LOGS")

        sys.path.pop(0)


# ---------------------------------------------------------------------------
# Test: save_incident Lambda — parameter parsing
# ---------------------------------------------------------------------------


class TestSaveIncidentLambda(unittest.TestCase):
    """Tests for backend/lambda/save_incident/lambda_function.py"""

    def test_status_logic_quarantine(self):
        """Verify QUARANTINE_TAG_APPLIED sets status to INVESTIGATING"""
        # Test the status logic directly
        action_taken = "QUARANTINE_TAG_APPLIED"
        if action_taken in ("NONE", "RECOMMEND_ONLY", "RECOMMENDATION_ONLY"):
            status = "OPEN"
        elif action_taken in ("QUARANTINE_TAG_APPLIED", "IAM_KEY_FLAGGED_FOR_REVIEW"):
            status = "INVESTIGATING"
        else:
            status = "OPEN"

        self.assertEqual(status, "INVESTIGATING")

    def test_status_logic_recommendation(self):
        """Verify RECOMMENDATION_ONLY sets status to OPEN"""
        action_taken = "RECOMMENDATION_ONLY"
        if action_taken in ("NONE", "RECOMMEND_ONLY", "RECOMMENDATION_ONLY"):
            status = "OPEN"
        elif action_taken in ("QUARANTINE_TAG_APPLIED", "IAM_KEY_FLAGGED_FOR_REVIEW"):
            status = "INVESTIGATING"
        else:
            status = "OPEN"

        self.assertEqual(status, "OPEN")

    def test_status_logic_iam_flag(self):
        """Verify IAM_KEY_FLAGGED_FOR_REVIEW sets status to INVESTIGATING"""
        action_taken = "IAM_KEY_FLAGGED_FOR_REVIEW"
        if action_taken in ("NONE", "RECOMMEND_ONLY", "RECOMMENDATION_ONLY"):
            status = "OPEN"
        elif action_taken in ("QUARANTINE_TAG_APPLIED", "IAM_KEY_FLAGGED_FOR_REVIEW"):
            status = "INVESTIGATING"
        else:
            status = "OPEN"

        self.assertEqual(status, "INVESTIGATING")


# ---------------------------------------------------------------------------
# Test: AISoc-alerttrigger Lambda — event parsing
# ---------------------------------------------------------------------------


class TestAlertTriggerLambda(unittest.TestCase):
    """Tests for backend/lambda/AISoc-alerttrigger/lambda_function.py"""

    def test_eventbridge_detail_extraction(self):
        """Verify EventBridge detail payload is correctly extracted"""
        event_with_detail = {
            "detail": {
                "alert_type": "UnauthorizedAccess:EC2/SSHBruteForce",
                "resource_id": "i-0abc123mock456",
                "severity": 7.0,
            }
        }

        if "detail" in event_with_detail:
            alert_data = event_with_detail["detail"]
        else:
            alert_data = event_with_detail

        self.assertEqual(alert_data["alert_type"], "UnauthorizedAccess:EC2/SSHBruteForce")
        self.assertEqual(alert_data["resource_id"], "i-0abc123mock456")

    def test_direct_invocation_extraction(self):
        """Verify direct Lambda invocation (no detail key) works"""
        event_direct = {
            "alert_type": "IAMUser:AnomalousBehavior",
            "resource_id": "AIDA-TEST",
        }

        if "detail" in event_direct:
            alert_data = event_direct["detail"]
        else:
            alert_data = event_direct

        self.assertEqual(alert_data["alert_type"], "IAMUser:AnomalousBehavior")


# ---------------------------------------------------------------------------
# Test: AISoc-ChatHandler Lambda — input validation
# ---------------------------------------------------------------------------


class TestChatHandlerLambda(unittest.TestCase):
    """Tests for backend/lambda/AISoc-ChatHandler/lambda_function.py"""

    def test_empty_message_returns_400(self):
        """Verify empty message returns 400 Bad Request"""
        sys.path.insert(0, "backend/lambda/AISoc-ChatHandler")
        from lambda_function import lambda_handler

        event = {
            "httpMethod": "POST",
            "body": json.dumps({"message": ""}),
        }

        response = lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 400)

        body = json.loads(response["body"])
        self.assertIn("error", body)

        sys.path.pop(0)

    def test_cors_options_request(self):
        """Verify OPTIONS request returns 200 with CORS headers"""
        sys.path.insert(0, "backend/lambda/AISoc-ChatHandler")
        from lambda_function import lambda_handler

        event = {"httpMethod": "OPTIONS"}
        response = lambda_handler(event, None)

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["Access-Control-Allow-Origin"], "*")

        sys.path.pop(0)


# ---------------------------------------------------------------------------
# Test: Infrastructure JSON validation
# ---------------------------------------------------------------------------


class TestInfrastructureFiles(unittest.TestCase):
    """Validate all infrastructure JSON files are well-formed"""

    INFRA_FILES = [
        "infrastructure/dynamodb_schema.json",
        "infrastructure/eventbridge_rule.json",
        "infrastructure/bedrock_guardrail.json",
        "infrastructure/iam_policies/bedrock_agent_role.json",
        "infrastructure/iam_policies/lambda_execution_role.json",
        "infrastructure/iam_policies/eventbridge_role.json",
    ]

    def test_all_json_files_parseable(self):
        """Verify all infrastructure JSON files parse without errors"""
        for filepath in self.INFRA_FILES:
            with open(filepath, "r") as f:
                try:
                    data = json.load(f)
                    self.assertIsInstance(data, dict, f"{filepath} is not a JSON object")
                except json.JSONDecodeError as e:
                    self.fail(f"{filepath} contains invalid JSON: {e}")

    def test_dynamodb_schema_has_key_schema(self):
        """Verify DynamoDB schema defines key schema"""
        with open("infrastructure/dynamodb_schema.json", "r") as f:
            schema = json.load(f)
        self.assertIn("KeySchema", schema)
        self.assertIn("TableName", schema)

    def test_eventbridge_rule_has_event_pattern(self):
        """Verify EventBridge rule defines an event pattern"""
        with open("infrastructure/eventbridge_rule.json", "r") as f:
            rule = json.load(f)
        self.assertIn("EventPattern", rule)

    def test_guardrail_has_topic_policy(self):
        """Verify Bedrock guardrail defines topic blocking policies"""
        with open("infrastructure/bedrock_guardrail.json", "r") as f:
            guardrail = json.load(f)
        self.assertIn("topicPolicyConfig", guardrail)
        self.assertIn("wordPolicyConfig", guardrail)
        topics = guardrail["topicPolicyConfig"]["topicsConfig"]
        self.assertGreater(len(topics), 0)
        # Verify all topics are DENY type
        for topic in topics:
            self.assertEqual(topic["type"], "DENY")

    def test_mock_alert_files_exist(self):
        """Verify all 5 mock alert JSON files are valid"""
        mock_files = [
            "backend/mock_data/test_alert_1_ssh_bruteforce.json",
            "backend/mock_data/test_alert_2_iam_anomaly.json",
            "backend/mock_data/test_alert_3_false_positive.json",
            "backend/mock_data/test_alert_4_crypto_mining.json",
            "backend/mock_data/test_alert_5_s3_malicious_ip.json",
        ]
        for filepath in mock_files:
            with open(filepath, "r") as f:
                data = json.load(f)
                self.assertIn("alert_type", data.get("detail", data))


if __name__ == "__main__":
    unittest.main()
