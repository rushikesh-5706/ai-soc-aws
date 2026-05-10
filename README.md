# 🛡️ AI-SOC AWS — Intelligent Security Operations Center

An end-to-end, cloud-native AI Security Operations Center (SOC) built on AWS. This platform automatically ingests security events, classifies them by severity, triggers automated remediation playbooks via AWS Bedrock agents, and surfaces everything through a sleek, real-time React dashboard.

---

## 📁 Repository Structure

```
ai-soc-aws/
├── backend/
│   ├── agent/              # AWS Bedrock agent configuration & prompts
│   ├── lambda/
│   │   ├── get_logs/       # Lambda: fetch incidents from DynamoDB
│   │   ├── save_incident/  # Lambda: ingest & store new security events
│   │   └── take_action/    # Lambda: execute automated remediation actions
│   └── mock_data/          # Sample incident payloads for local testing
│
├── frontend/
│   └── soc-dashboard/      # React 18 dashboard (CRA)
│       ├── public/         # Static assets (favicon, manifest)
│       └── src/
│           ├── App.js      # Main application component
│           ├── App.css     # Global theme & component styles
│           ├── api.js      # API base URL config
│           ├── index.js    # React entry point
│           └── index.css   # Base font & reset styles
│
├── infrastructure/
│   ├── dynamodb_schema.json  # DynamoDB table schema definition
│   └── iam_policies/         # IAM role & policy JSON files
│
├── docs/
│   ├── architecture_diagram.png  # AWS architecture overview
│   └── project_report.md         # Technical project report
│
├── .gitignore
└── README.md
```

---

## 🚀 Key Features

- **Real-time incident ingestion** via EventBridge → Lambda → DynamoDB pipeline
- **AI-powered analysis** using AWS Bedrock Agent with natural language querying
- **Automated remediation** via `take_action` Lambda (quarantine, tag, block)
- **Interactive SOC Dashboard** — filterable KPI tiles, severity-based tables, analytics charts
- **AI Chat Assistant** — ask natural language questions about any incident
- **Persistent incident management** — delete incidents with browser-local persistence
- **Dark / Light mode** with Poppins font and brand-consistent color palette

---

## 🧰 Tech Stack

| Layer        | Technology                              |
|--------------|-----------------------------------------|
| Frontend     | React 18, Recharts, Lucide React        |
| Backend      | AWS Lambda (Python), AWS Bedrock Agent  |
| Database     | Amazon DynamoDB                         |
| Event Bus    | Amazon EventBridge                      |
| API          | Amazon API Gateway (REST)               |
| Auth/Roles   | AWS IAM                                 |

---

## ⚙️ Local Setup

### Frontend
```bash
cd frontend/soc-dashboard
npm install
npm start
```
Dashboard runs at `http://localhost:3000`

### Backend
Deploy Lambda functions individually via AWS Console or AWS CLI. Ensure DynamoDB table and API Gateway are provisioned using `infrastructure/dynamodb_schema.json` and the IAM policies in `infrastructure/iam_policies/`.

---

## 🌐 API Endpoint

The frontend connects to a deployed AWS API Gateway endpoint configured in `frontend/soc-dashboard/src/api.js`.

---

## 👥 Team

Built as part of an AI-powered cloud security automation project.
