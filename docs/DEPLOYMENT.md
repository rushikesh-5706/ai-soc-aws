# 🚀 Deployment Guide — AI SOC for AWS

> **Project Space 8.0 | Team 14**  
> Complete step-by-step deployment instructions for all AWS services

---

## Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| AWS Account | Free Tier | — |
| AWS CLI v2 | 2.x | `aws --version` |
| Python | 3.12 | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | 2.x | `git --version` |

```bash
# Configure AWS CLI with your IAM credentials
aws configure
# AWS Access Key ID: <your-key>
# AWS Secret Access Key: <your-secret>
# Default region name: us-east-1
# Default output format: json
```

---

## Phase 1: IAM Roles Setup

### 1.1 Create Lambda Execution Role

1. Go to **IAM → Roles → Create Role**
2. Trusted entity: **AWS Service → Lambda**
3. Attach policies:
   - `AWSLambdaBasicExecutionRole` (AWS managed)
4. Add inline policy from file: `infrastructure/iam_policies/lambda_execution_role.json`
5. Name: `AISoc-LambdaExecutionRole`

### 1.2 Create Bedrock Agent Role

1. Go to **IAM → Roles → Create Role**
2. Trusted entity: **Custom trust policy**
3. Trust policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "bedrock.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```
4. Add inline policy from: `infrastructure/iam_policies/bedrock_agent_role.json`
5. Name: `AISoc-BedrockAgentRole`

### 1.3 Create EventBridge Role

1. Go to **IAM → Roles → Create Role**
2. Trusted entity: **Custom trust policy**
3. Trust policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "events.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```
4. Add inline policy from: `infrastructure/iam_policies/eventbridge_role.json`
5. Name: `AISoc-EventBridgeRole`

---

## Phase 2: DynamoDB Setup

```bash
# Create the DynamoDB table using the schema file
aws dynamodb create-table \
  --cli-input-json file://infrastructure/dynamodb_schema.json \
  --region us-east-1

# Verify table was created
aws dynamodb describe-table \
  --table-name AISoc-Incidents \
  --region us-east-1
```

**Expected output:** `TableStatus: CREATING` → wait ~30 seconds → `ACTIVE`

---

## Phase 3: Deploy Lambda Functions

Deploy each Lambda function using the script below. Replace `YOUR_ACCOUNT_ID` with your AWS Account ID.

```bash
ROLE_ARN="arn:aws:iam::YOUR_ACCOUNT_ID:role/AISoc-LambdaExecutionRole"
REGION="us-east-1"

deploy_lambda() {
  NAME=$1
  DIR=$2
  echo "Deploying $NAME..."
  cd backend/lambda/$DIR
  zip -j function.zip lambda_function.py
  
  # Check if function exists
  if aws lambda get-function --function-name $NAME --region $REGION 2>/dev/null; then
    aws lambda update-function-code \
      --function-name $NAME \
      --zip-file fileb://function.zip \
      --region $REGION
  else
    aws lambda create-function \
      --function-name $NAME \
      --runtime python3.12 \
      --handler lambda_function.lambda_handler \
      --zip-file fileb://function.zip \
      --role $ROLE_ARN \
      --timeout 60 \
      --memory-size 256 \
      --region $REGION
  fi
  cd ../../..
}

deploy_lambda "AISoc-alerttrigger"   "AISoc-alerttrigger"
deploy_lambda "AISoc-ChatHandler"    "AISoc-ChatHandler"
deploy_lambda "AISoc-GetIncidents"   "AISoc-GetIncidents"
deploy_lambda "AISoc-GetLogs"        "get_logs"
deploy_lambda "AISoc-SaveIncident"   "save_incident"
deploy_lambda "AISoc-TakeAction"     "take_action"

echo "All Lambda functions deployed!"
```

### 3.1 Set Environment Variables

After deploying `AISoc-alerttrigger` and `AISoc-ChatHandler`, set the Bedrock Agent IDs:

```bash
# For AISoc-alerttrigger (uses EventBridge alias)
aws lambda update-function-configuration \
  --function-name AISoc-alerttrigger \
  --environment Variables='{
    "AGENT_ID":"UOSNOXLWJD",
    "AGENT_ALIAS_ID":"02PQZAH3MY"
  }' \
  --region us-east-1

# For AISoc-ChatHandler (uses production alias)
aws lambda update-function-configuration \
  --function-name AISoc-ChatHandler \
  --environment Variables='{
    "AGENT_ID":"UOSNOXLWJD",
    "AGENT_ALIAS_ID":"0YQZSD4HA6"
  }' \
  --region us-east-1
```

---

## Phase 4: Amazon Bedrock Agent Setup

> **Note:** Bedrock Agent creation must be done via the AWS Console (UI). The new console UI may differ from older screenshots — use these instructions as your guide.

### 4.1 Request Model Access

1. Go to **Amazon Bedrock → Model access** (left sidebar)
2. Click **Manage model access**
3. Enable: **Meta Llama 3.1 8B Instruct** (`meta.llama3-8b-instruct-v1:0`)
4. Click **Save changes** — access is granted in ~1 minute

### 4.2 Create the Agent

1. Go to **Amazon Bedrock → Agents → Create agent**
2. **Agent name:** `ai-soc-analyst`
3. **Description:** `ARIA - Autonomous AI SOC analyst for AWS security threat triage`
4. **Agent resource role:** Select `AISoc-BedrockAgentRole`
5. **Model:** Select `Meta` → `meta.llama3-8b-instruct-v1:0`
6. **Instructions:** Paste the entire contents of `backend/agent/agent_instructions.txt`
7. Click **Save**

### 4.3 Create Action Group

1. In the agent, go to **Action groups → Add**
2. **Action group name:** `soc-tools`
3. **Description:** `Tools for log retrieval, remediation, and incident persistence`
4. **Action group type:** Define with function details → **Select Lambda functions**
5. Upload **OpenAPI schema:** upload `backend/agent/openapi_schema.json`
6. **Lambda function:** Add permissions for all three tool Lambdas:
   - `AISoc-GetLogs`
   - `AISoc-TakeAction`
   - `AISoc-SaveIncident`
7. Click **Save**

### 4.4 Add Bedrock Guardrails

1. Go to **Amazon Bedrock → Guardrails → Create guardrail**
2. **Name:** `AISoc-SafetyGuardrail`
3. **Denied topics:** Add topics:
   - "Data destruction commands"
   - "Resource termination or deletion"
   - "Credential exfiltration"
4. **Word filters:** Add words: `terminate`, `delete`, `destroy`, `wipe`, `deactivate`, `format`, `drop`
5. **PII protection:** Enable AWS Account ID redaction
6. Attach to your agent under **Guardrails** in Agent settings

### 4.5 Prepare and Alias the Agent

1. In the agent, click **Prepare** (top right) — wait for status `Prepared`
2. Go to **Aliases → Create alias**
3. **Alias name:** `production`
4. **Version:** Select the prepared version
5. Note down the **Alias ID** — update Lambda environment variables if different

---

## Phase 5: API Gateway Setup

### 5.1 Create REST API

1. Go to **API Gateway → Create API → REST API**
2. **Name:** `AISoc-API`
3. **Endpoint type:** Regional

### 5.2 Create Resources and Methods

**Resource 1: `/incidents`**
```
GET /incidents → Integration: Lambda (AISoc-GetIncidents)
OPTIONS /incidents → Integration: Mock (CORS)
```

**Resource 2: `/chat`**
```
POST /chat → Integration: Lambda (AISoc-ChatHandler)
OPTIONS /chat → Integration: Mock (CORS)
```

### 5.3 Enable CORS

For each resource:
1. Select the resource
2. Click **Actions → Enable CORS**
3. **Access-Control-Allow-Origin:** `*`
4. **Access-Control-Allow-Headers:** `Content-Type,X-Amz-Date,Authorization`
5. Click **Enable CORS and replace existing CORS headers**

### 5.4 Deploy API

1. Click **Actions → Deploy API**
2. **Deployment stage:** Create new stage: `prod`
3. Note the **Invoke URL** — update `API_BASE_URL` in `frontend/soc-dashboard/src/App.js` and `api.js`

---

## Phase 6: EventBridge Setup

### 6.1 Create EventBridge Rule

1. Go to **Amazon EventBridge → Rules → Create rule**
2. **Name:** `AISoc-SecurityAlertRouter`
3. **Event bus:** `default`
4. **Event pattern:**
```json
{
  "$or": [
    {
      "source": ["aws.guardduty"],
      "detail-type": ["GuardDuty Finding"]
    },
    {
      "source": ["custom.aisoc.mock"],
      "detail-type": ["MockSecurityAlert"]
    }
  ]
}
```
5. **Target:** Lambda function → `AISoc-alerttrigger`
6. Click **Create rule**

### 6.2 Grant EventBridge Permission to Invoke Lambda

```bash
aws lambda add-permission \
  --function-name AISoc-alerttrigger \
  --statement-id EventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --region us-east-1
```

---

## Phase 7: Enable GuardDuty

```bash
# Enable GuardDuty (30-day free trial)
aws guardduty create-detector \
  --enable \
  --finding-publishing-frequency FIFTEEN_MINUTES \
  --region us-east-1

# Generate sample findings for testing
DETECTOR_ID=$(aws guardduty list-detectors --region us-east-1 --query 'DetectorIds[0]' --output text)
aws guardduty create-sample-findings \
  --detector-id $DETECTOR_ID \
  --finding-types "UnauthorizedAccess:EC2/SSHBruteForce" \
  --region us-east-1
```

---

## Phase 8: Deploy React Dashboard

```bash
cd frontend/soc-dashboard

# Install dependencies
npm install

# Build for production
npm run build

# The /build folder is your deployable artifact
```

### Deploy to AWS Amplify

1. Go to **AWS Amplify → New app → Host web app**
2. **Source:** GitHub → Connect repository → Select branch `feature/dynamo-eventbridge`
3. **Build settings:** Amplify auto-detects React — confirm `npm run build` and `build` as output directory
4. Click **Save and deploy**
5. Amplify provides a public URL — your dashboard is live!

---

## Phase 9: End-to-End Test

```bash
# Send test alert 1: SSH Brute Force
aws events put-events \
  --entries '[{
    "Source": "custom.aisoc.mock",
    "DetailType": "MockSecurityAlert",
    "Detail": "{\"alert_type\":\"UnauthorizedAccess:EC2/SSHBruteForce\",\"resource_id\":\"i-0abc123mock456\",\"resource_type\":\"EC2\",\"severity\":7.0,\"source_ip\":\"185.220.101.34\",\"region\":\"us-east-1\"}"
  }]' \
  --region us-east-1

# Wait 30 seconds, then check DynamoDB
aws dynamodb scan \
  --table-name AISoc-Incidents \
  --region us-east-1 \
  --query 'Items[*].{ID:incident_id.S,Type:alert_type.S,Severity:severity.S,Action:action_taken.S}'
```

**Expected:** New incident record in DynamoDB with ARIA's analysis and action taken.

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Lambda timeout | Bedrock streaming takes > 3 seconds | Increase Lambda timeout to 60s |
| `AccessDeniedException` from Lambda | Missing IAM permission | Add missing permission to `AISoc-LambdaExecutionRole` |
| CORS error in browser | API Gateway CORS not set | Re-run Enable CORS on both resources |
| Agent returns empty response | Agent not prepared | Click Prepare in Bedrock console |
| DynamoDB `ValidationException` | TTL value not a number | Ensure `ttl` is set as integer Unix timestamp |

---

*— AI SOC for AWS · Project Space 8.0 · Team 14 —*
