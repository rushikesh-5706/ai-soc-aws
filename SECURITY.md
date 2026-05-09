# 🔐 Security Policy — AI SOC for AWS

> **Project Space 8.0 | Team 14**  
> Security policy, vulnerability reporting, and hardening guidelines

---

## Supported Versions

| Version | Branch | Status |
|---------|--------|--------|
| Latest | `feature/dynamo-eventbridge` | ✅ Active development |
| Main | `main` | ✅ Stable |

---

## 🚨 Reporting a Vulnerability

If you discover a security vulnerability in this project:

1. **Do NOT open a public GitHub Issue**
2. Contact the team lead directly: **K. Rushikesh** (23MH1A4930)
3. Provide a clear description of the vulnerability and reproduction steps
4. Allow the team 48 hours to assess and respond

---

## 🛡️ Security Architecture

### IAM Least-Privilege Design

All AWS services in this project operate under dedicated IAM roles with **only the permissions they need**:

| Role | Trust Principal | Permissions Granted |
|------|----------------|---------------------|
| `AISoc-LambdaExecutionRole` | `lambda.amazonaws.com` | DynamoDB CRUD, CloudTrail read, EC2 tagging only |
| `AISoc-BedrockAgentRole` | `bedrock.amazonaws.com` | Lambda invoke (3 tools only), Bedrock model access |
| `AISoc-EventBridgeRole` | `events.amazonaws.com` | Invoke `AISoc-alerttrigger` Lambda only |

**No wildcard `*` actions** are permitted in any policy except where AWS requires it (e.g., CloudTrail).

### Bedrock Guardrails

The Bedrock Agent (ARIA) is protected by **Amazon Bedrock Guardrails** that independently block:

| Category | Blocked Terms / Actions |
|----------|------------------------|
| Destructive commands | `terminate`, `delete`, `destroy`, `wipe`, `deactivate`, `format`, `truncate`, `drop` |
| Data exfiltration | Credential extraction, secret key exposure requests |
| PII protection | AWS Account IDs and IAM access keys redacted from responses |
| Malicious prompts | Prompt injection and jailbreak attempts blocked |

Guardrails operate **independently of agent instructions** — they cannot be bypassed by the model itself.

### Lambda Security Controls

- **No hardcoded credentials** in any Lambda function
- All AWS SDK access via **IAM execution role** (injected by Lambda runtime)
- Agent IDs stored as **Lambda environment variables**
- **No secrets in source code** — verified via `.gitignore` rules

### DynamoDB Security

- Table encrypted with **AWS-managed KMS key** (SSE enabled by default)
- Access scoped to exact table ARN in IAM policy (not `*`)
- **TTL enabled** — records auto-deleted after 90 days (data minimization)
- DynamoDB table name not exposed in public API responses

### API Gateway Security

- CORS headers configured to control cross-origin access
- API accepts only `Content-Type: application/json` requests
- No authentication bypass possible — Lambda function validates input
- All errors return generic messages (no internal stack traces to client)

---

## 🔍 Security Controls Checklist

| Control | Status | Implementation |
|---------|--------|---------------|
| No wildcard `*` permissions | ✅ | Resource-scoped ARNs in all policies |
| No hardcoded credentials | ✅ | IAM roles + environment variables only |
| Encrypted storage | ✅ | DynamoDB KMS encryption enabled |
| Guardrails safety layer | ✅ | Amazon Bedrock Guardrails enforced |
| Least-privilege IAM | ✅ | Dedicated role per service |
| No destructive Lambda permissions | ✅ | `ec2:CreateTags` only — no terminate/stop/delete |
| Audit trail | ✅ | All actions logged to CloudWatch |
| Data minimization | ✅ | 90-day TTL on all incident records |
| CORS controlled | ✅ | API Gateway CORS configured |
| Input validation | ✅ | Lambda functions validate all inputs |

---

## 🚫 What ARIA Will Never Do

The AI agent (ARIA) is designed with explicit safety boundaries:

1. **Will NOT terminate EC2 instances** — only tags are applied (`ec2:CreateTags`)
2. **Will NOT delete IAM users, roles, or policies** — flags for human review only
3. **Will NOT delete or truncate DynamoDB tables**
4. **Will NOT expose AWS credentials** in any response
5. **Will NOT execute commands outside of its 3 defined Action Group tools**
6. **Will NOT bypass Bedrock Guardrails** — they operate at infrastructure level

---

## 📋 Dependency Security

| Layer | Runtime | Known Vulnerabilities |
|-------|---------|----------------------|
| Lambda (Python) | Python 3.12 | None — uses only AWS SDK (boto3) |
| Frontend (React) | Node 18+ | Run `npm audit` regularly |
| Infrastructure | AWS managed | AWS handles patching |

```bash
# Check frontend for vulnerabilities
cd frontend/soc-dashboard
npm audit
npm audit fix  # auto-fix non-breaking issues
```

---

## 🔄 Incident Response

If a real security incident occurs involving this system:

1. **Immediately rotate** any exposed IAM credentials
2. **Disable** the compromised Lambda or Bedrock Agent alias
3. **Review CloudWatch logs** for the incident timeline
4. **Scan DynamoDB** for unauthorized writes
5. **Notify** the team lead and AWS support if account-level compromise suspected

---

*— AI SOC for AWS · Project Space 8.0 · Team 14 —*
