"""
Unit Tests for AI SOC Lambda Functions
Uses unittest with importlib for clean module loading.
Run: python -m pytest tests/test_lambdas.py -v
"""

import json
import unittest
import datetime
import uuid
import os
import sys
import importlib.util


def load_lambda(module_name, file_path):
    """Load a Lambda module from a specific file path, bypassing module cache."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Test: take_action Lambda
# ---------------------------------------------------------------------------


class TestTakeActionLambda(unittest.TestCase):
    """Tests for backend/lambda/take_action/lambda_function.py"""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_lambda(
            "take_action", "backend/lambda/take_action/lambda_function.py"
        )

    def setUp(self):
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
        response = self.mod.lambda_handler(self.base_event, None)

        self.assertEqual(response["messageVersion"], "1.0")
        self.assertIn("response", response)
        self.assertIn("functionResponse", response["response"])

        body = json.loads(
            response["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        )
        self.assertEqual(body["action_taken"], "apply_quarantine_tag")
        self.assertEqual(body["resource_id"], "i-0abc123mock456")
        self.assertEqual(body["severity"], "HIGH")

    def test_take_action_default_parameters(self):
        """Verify defaults when parameters are missing"""
        minimal_event = {"parameters": []}
        response = self.mod.lambda_handler(minimal_event, None)
        body = json.loads(
            response["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        )

        self.assertEqual(body["severity"], "MEDIUM")
        self.assertEqual(body["resource_type"], "Unknown")
        self.assertEqual(body["action_taken"], "RECOMMENDATION_ONLY")

    def test_take_action_description_mapping(self):
        """Verify action descriptions are correctly mapped"""
        response = self.mod.lambda_handler(self.base_event, None)
        body = json.loads(
            response["response"]["functionResponse"]["responseBody"]["TEXT"]["body"]
        )
        self.assertEqual(body["description"], "Applied quarantine tag to restrict network access.")


# ---------------------------------------------------------------------------
# Test: get_logs Lambda — mock log analysis
# ---------------------------------------------------------------------------


class TestGetLogsLambda(unittest.TestCase):
    """Tests for backend/lambda/get_logs/lambda_function.py"""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_lambda(
            "get_logs", "backend/lambda/get_logs/lambda_function.py"
        )

    def test_mock_ec2_logs_generated(self):
        """Verify mock EC2 logs are generated when CloudTrail is unavailable"""
        logs = self.mod.generate_mock_logs("i-0abc123mock456", "EC2")

        self.assertGreater(len(logs), 0)
        self.assertEqual(logs[0]["event_source"], "ec2.amazonaws.com")
        self.assertEqual(logs[0]["data_source"], "mock")

    def test_mock_iam_logs_generated(self):
        """Verify mock IAM logs contain privilege escalation events"""
        logs = self.mod.generate_mock_logs("AIDA-MOCK-USER", "IAM")

        self.assertGreater(len(logs), 0)
        event_names = [log["event_name"] for log in logs]
        self.assertIn("CreateAccessKey", event_names)
        self.assertIn("AttachUserPolicy", event_names)

    def test_mock_rds_logs_generated(self):
        """Verify mock RDS logs contain database events"""
        logs = self.mod.generate_mock_logs("db-instance-1", "RDS")

        self.assertGreater(len(logs), 0)
        event_names = [log["event_name"] for log in logs]
        self.assertIn("ModifyDBInstance", event_names)
        self.assertIn("RestoreDBFromSnapshot", event_names)

    def test_analyze_suspicious_pattern(self):
        """Verify pattern analysis flags privileged actions as SUSPICIOUS"""
        logs = self.mod.generate_mock_logs("i-0abc123mock456", "EC2")
        analysis = self.mod.analyze_log_patterns(logs, "i-0abc123mock456", "EC2")

        self.assertEqual(analysis["pattern"], "SUSPICIOUS")
        self.assertGreater(len(analysis["suspicious_indicators"]), 0)

    def test_analyze_empty_logs(self):
        """Verify empty logs return NO_LOGS pattern"""
        analysis = self.mod.analyze_log_patterns([], "i-test", "EC2")
        self.assertEqual(analysis["pattern"], "NO_LOGS")


# ---------------------------------------------------------------------------
# Test: save_incident Lambda — parameter parsing & status logic
# ---------------------------------------------------------------------------


class TestSaveIncidentLambda(unittest.TestCase):
    """Tests for backend/lambda/save_incident/lambda_function.py"""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_lambda(
            "save_incident", "backend/lambda/save_incident/lambda_function.py"
        )

    def test_normalize_empty_string(self):
        """Verify normalize returns default for empty strings"""
        self.assertEqual(self.mod.normalize("", "fallback"), "fallback")
        self.assertEqual(self.mod.normalize(None, "fallback"), "fallback")
        self.assertEqual(self.mod.normalize("UNKNOWN", "fallback"), "fallback")
        self.assertEqual(self.mod.normalize("N/A", "fallback"), "fallback")

    def test_normalize_valid_value(self):
        """Verify normalize returns the value when it's valid"""
        self.assertEqual(self.mod.normalize("i-0abc123", "fallback"), "i-0abc123")
        self.assertEqual(self.mod.normalize("HIGH", "MEDIUM"), "HIGH")

    def test_map_action_ssh_bruteforce(self):
        """Verify SSH brute force maps to quarantine tag"""
        result = self.mod.map_action("UnauthorizedAccess:EC2/SSHBruteForce")
        self.assertEqual(result, "apply_quarantine_tag")

    def test_map_action_unknown_alert(self):
        """Verify unknown alert types map to RECOMMENDATION_ONLY"""
        result = self.mod.map_action("SomeUnknownAlert")
        self.assertEqual(result, "RECOMMENDATION_ONLY")

    def test_determine_status_investigating(self):
        """Verify quarantine actions set status to INVESTIGATING"""
        self.assertEqual(self.mod.determine_status("apply_quarantine_tag"), "INVESTIGATING")
        self.assertEqual(self.mod.determine_status("isolate_instance"), "INVESTIGATING")

    def test_determine_status_open(self):
        """Verify unknown actions set status to OPEN"""
        self.assertEqual(self.mod.determine_status("RECOMMENDATION_ONLY"), "OPEN")
        self.assertEqual(self.mod.determine_status("some_other_action"), "OPEN")


# ---------------------------------------------------------------------------
# Test: AISoc-alerttrigger Lambda — event parsing
# ---------------------------------------------------------------------------


class TestAlertTriggerLambda(unittest.TestCase):
    """Tests for backend/lambda/AISoc-alerttrigger/lambda_function.py"""

    @classmethod
    def setUpClass(cls):
        cls.mod = load_lambda(
            "alerttrigger", "backend/lambda/AISoc-alerttrigger/lambda_function.py"
        )

    def test_extract_from_detail_dict(self):
        """Verify extraction from EventBridge detail dict"""
        event = {
            "detail": {
                "alert_type": "UnauthorizedAccess:EC2/SSHBruteForce",
                "resource": "i-0abc123mock456",
                "resource_type": "EC2",
                "severity": 7,
                "source_ip": "203.0.113.45",
            }
        }
        fields = self.mod.extract_alert_fields(event)
        self.assertEqual(fields["alert_type"], "UnauthorizedAccess:EC2/SSHBruteForce")
        self.assertEqual(fields["resource"], "i-0abc123mock456")
        self.assertEqual(fields["severity"], "CRITICAL")  # 7 → CRITICAL

    def test_extract_from_top_level(self):
        """Verify extraction from direct Lambda invocation"""
        event = {
            "alert_type": "IAMUser:AnomalousBehavior",
            "resource": "AIDA-TEST",
            "resource_type": "IAM",
            "severity": "HIGH",
            "source_ip": "10.0.0.1",
        }
        fields = self.mod.extract_alert_fields(event)
        self.assertEqual(fields["alert_type"], "IAMUser:AnomalousBehavior")
        self.assertEqual(fields["resource"], "AIDA-TEST")

    def test_severity_normalization_numeric(self):
        """Verify numeric severity is converted to text labels"""
        event = {"detail": {"alert_type": "test", "severity": 8}}
        fields = self.mod.extract_alert_fields(event)
        self.assertEqual(fields["severity"], "CRITICAL")

        event2 = {"detail": {"alert_type": "test", "severity": 2}}
        fields2 = self.mod.extract_alert_fields(event2)
        self.assertEqual(fields2["severity"], "LOW")

    def test_build_structured_prompt(self):
        """Verify structured prompt contains all required fields"""
        fields = {
            "alert_type": "SSHBruteForce",
            "resource": "i-test",
            "resource_type": "EC2",
            "severity": "HIGH",
            "source_ip": "1.2.3.4",
            "region": "us-east-1",
        }
        prompt = self.mod.build_structured_prompt(fields)
        self.assertIn("SSHBruteForce", prompt)
        self.assertIn("i-test", prompt)
        self.assertIn("STEP 1: Call get_logs", prompt)
        self.assertIn("STEP 2: Call take_action", prompt)
        self.assertIn("STEP 3: Call save_incident", prompt)


# ---------------------------------------------------------------------------
# Test: Infrastructure JSON validation
# ---------------------------------------------------------------------------


class TestInfrastructureFiles(unittest.TestCase):
    """Validate all infrastructure JSON files are well-formed"""

    INFRA_FILES = [
        "infrastructure/dynamodb_schema.json",
        "infrastructure/eventbridge_rule.json",
        "infrastructure/bedrock_guardrail.json",
        "infrastructure/sns_alert_topic.json",
        "infrastructure/cognito_user_pool.json",
        "infrastructure/security_hub_config.json",
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
