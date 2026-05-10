import json
import boto3
import uuid
import os

bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))

AGENT_ID = os.environ.get("AGENT_ID", "UOSNOXLWJD")
AGENT_ALIAS_ID = os.environ.get("AGENT_ALIAS_ID", "02PQZAH3MY")


def extract_alert_fields(event):
    """
    Handles all 3 possible event formats:
    1. EventBridge → detail.Detail is a JSON string  (real flow)
    2. EventBridge → detail is a flat dict           (some EB setups)
    3. Fields at top level                           (manual Lambda test)
    """
    fields = {
        "alert_type":    "UnknownAlert",
        "resource":      "unknown-resource",
        "resource_type": "Unknown",
        "severity":      "MEDIUM",
        "source_ip":     "unknown",
        "region":        "us-east-1",
    }

    nested = None

    try:
        detail = event.get("detail", {})

        # Format 1: detail.Detail is a JSON string (EventBridge default)
        if isinstance(detail, dict) and "Detail" in detail:
            nested = json.loads(detail["Detail"])
            print("FORMAT: Parsed from detail.Detail string")

        # Format 2: detail is already a flat dict with alert fields
        elif isinstance(detail, dict) and "alert_type" in detail:
            nested = detail
            print("FORMAT: Parsed from detail dict directly")

        # Format 3: fields at top level (manual test)
        elif "alert_type" in event:
            nested = event
            print("FORMAT: Parsed from top-level event")

        else:
            print("WARNING: Unrecognized event format:")
            print(json.dumps(event, default=str))

        if nested:
            fields["alert_type"]    = str(nested.get("alert_type",    fields["alert_type"]))
            fields["resource"]      = str(nested.get("resource",      fields["resource"]))
            fields["resource_type"] = str(nested.get("resource_type", fields["resource_type"]))
            fields["source_ip"]     = str(nested.get("source_ip",     fields["source_ip"]))
            fields["region"]        = str(nested.get("region",        fields["region"]))

            # Normalize severity: numeric → text label
            severity = nested.get("severity", "MEDIUM")
            if isinstance(severity, int):
                if severity >= 7:
                    severity_text = "CRITICAL"
                elif severity >= 5:
                    severity_text = "HIGH"
                elif severity >= 3:
                    severity_text = "MEDIUM"
                else:
                    severity_text = "LOW"
            else:
                severity_text = str(severity)

            fields["severity"] = severity_text

    except Exception as e:
        print("ERROR extracting alert fields:", str(e))

    return fields


def build_structured_prompt(fields):
    """
    Builds an explicit structured prompt so ARIA knows
    exactly what fields to pass to each action group Lambda.
    """
    return (
        f"You are ARIA, an AI security operations analyst. "
        f"Investigate and respond to the following security alert.\n\n"
        f"ALERT DETAILS (use these exact values in all tool calls):\n"
        f"- alert_type: {fields['alert_type']}\n"
        f"- resource_id: {fields['resource']}\n"
        f"- resource_type: {fields['resource_type']}\n"
        f"- severity: {fields['severity']}\n"
        f"- source_ip: {fields['source_ip']}\n"
        f"- region: {fields['region']}\n\n"
        f"REQUIRED STEPS — complete all three in order:\n\n"
        f"STEP 1: Call get_logs with:\n"
        f"  - resource_id = {fields['resource']}\n"
        f"  - resource_type = {fields['resource_type']}\n"
        f"  - time_window_hours = 24\n\n"
        f"STEP 2: Call take_action with:\n"
        f"  - resource_id = {fields['resource']}\n"
        f"  - resource_type = {fields['resource_type']}\n"
        f"  - severity = {fields['severity']}\n"
        f"  - action_type = (choose based on alert_type, never use RECOMMENDATION_ONLY)\n"
        f"  - reason = (your analysis of why this action is needed)\n\n"
        f"STEP 3: Call save_incident with ALL of these exact values:\n"
        f"  - alert_type = {fields['alert_type']}\n"
        f"  - resource_id = {fields['resource']}\n"
        f"  - resource_type = {fields['resource_type']}\n"
        f"  - severity = {fields['severity']}\n"
        f"  - source_ip = {fields['source_ip']}\n"
        f"  - action_taken = (same action you used in step 2)\n"
        f"  - recommendation = (your recommended next steps)\n"
        f"  - agent_reasoning = (your full analysis)\n\n"
        f"CRITICAL: Never leave resource_id, resource_type, alert_type, "
        f"severity, or source_ip blank or as UNKNOWN. "
        f"Use the exact values from ALERT DETAILS above."
    )


def lambda_handler(event, context):
    print("AlertTrigger received event:")
    print(json.dumps(event, indent=2, default=str))

    # Extract fields from whatever format arrives
    fields = extract_alert_fields(event)
    print("Extracted fields:")
    print(json.dumps(fields, indent=2))

    # Safety check — if we still got unknowns, log clearly
    if fields["resource"] == "unknown-resource":
        print("WARNING: resource could not be extracted. Check EventBridge payload format.")

    # Build structured prompt for ARIA
    alert_text = build_structured_prompt(fields)
    print("Prompt sent to ARIA:")
    print(alert_text)

    session_id = f"session-{uuid.uuid4()}"

    try:
        print("Invoking Bedrock Agent ARIA...")

        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=alert_text,
            enableTrace=True,
        )

        final_response = ""

        for event_stream in response["completion"]:
            if "chunk" in event_stream:
                chunk = event_stream["chunk"]
                if "bytes" in chunk:
                    final_response += chunk["bytes"].decode("utf-8")

            if "trace" in event_stream:
                trace = event_stream["trace"]
                # Print useful trace info only
                try:
                    trace_str = json.dumps(trace, default=str)
                    if any(k in trace_str for k in ["invocationInput", "observation", "rationale", "FAILED"]):
                        print("TRACE:", trace_str[:500])
                except Exception:
                    print("TRACE EVENT (unparseable)")

        print("ARIA final response:")
        print(final_response)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "status":           "SUCCESS",
                "session_id":       session_id,
                "extracted_fields": fields,
                "agent_response":   final_response,
            }),
        }

    except Exception as e:
        print("ERROR invoking Bedrock Agent:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "FAILED",
                "error":  str(e),
            }),
        }
