# 🤝 Contributing Guidelines — AI SOC for AWS

> **Project Space 8.0 | Team 14**  
> Guidelines for contributing to the AI-Powered Security Operations Center

---

## 👥 Team Structure

| Member | Roll Number | Role |
|--------|-------------|------|
| Ch. Vaishnavi | 23A91A61E4 | AI Agent Lead |
| K. Rushikesh | 23MH1A4930 | EventBridge & QA Lead |
| K. Pavan | 23MH1A05H3 | Lambda & Backend Lead |
| M. Praneetha | 23MH1A05I3 | Data & Documentation Lead |
| A. Satwika | 23MH1A05E6 | Frontend & UI Lead |
| P. Varun | 23MH1A05K2 | Project Support & Coordinator |

---

## 🌿 Branch Strategy

```
main                  ← stable, production-ready code
feature/dynamo-eventbridge ← active development branch
feature/<name>        ← individual feature branches
hotfix/<name>         ← urgent bug fixes
```

**Always branch off from `feature/dynamo-eventbridge`** for new work during active development.

---

## 📝 Commit Message Convention

Use the following prefixes for all commit messages:

```
feat:     New feature or functionality
fix:      Bug fix
docs:     Documentation changes only
style:    Formatting, whitespace (no logic change)
refactor: Code restructuring (no feature/fix)
test:     Adding or updating tests
chore:    Build process, dependency updates
```

**Examples:**
```bash
git commit -m "feat: add crypto mining detection to take_action lambda"
git commit -m "fix: handle empty CloudTrail response in get_logs"
git commit -m "docs: update deployment guide for Phase 4 Bedrock agent"
git commit -m "test: add test_alert_4_crypto_mining mock payload"
```

---

## 🔀 Pull Request Process

1. **Create a feature branch** from `feature/dynamo-eventbridge`
2. **Make your changes** — keep commits atomic and meaningful
3. **Test locally** before pushing
4. **Push your branch** and open a Pull Request
5. **Assign a reviewer** — at least one team member must approve
6. **Address review comments** before merging
7. **Squash and merge** to keep history clean

---

## 🧪 Testing Requirements

Before opening a PR, ensure:

- [ ] All Lambda functions tested with mock payloads from `backend/mock_data/`
- [ ] EventBridge routing verified via `aws events put-events`
- [ ] DynamoDB records confirmed with `aws dynamodb scan`
- [ ] No hardcoded credentials in any file
- [ ] CORS tested from the React dashboard
- [ ] CI pipeline passes (`.github/workflows/ci.yml`)

---

## 📁 File Organization

Follow the repository structure defined in `README.md`:

```
backend/lambda/<FunctionName>/lambda_function.py   ← Lambda code
backend/agent/                                     ← Bedrock Agent config
backend/mock_data/                                 ← Test payloads
infrastructure/                                    ← AWS resource definitions
frontend/soc-dashboard/src/                        ← React source
docs/                                              ← Documentation
```

**Do NOT** place Lambda code outside its designated folder.  
**Do NOT** commit `node_modules/`, `__pycache__/`, `.env`, or `*.pyc` files.

---

## 🔐 Security Rules

- **Never commit** AWS credentials, access keys, or secret keys
- **Never commit** `.env` files (add to `.gitignore`)
- All AWS access must be via **IAM roles** and **environment variables**
- Sensitive resource ARNs in environment variables, not hardcoded
- If you accidentally commit a secret: rotate it immediately, then remove from git history

---

## 🏗️ Lambda Development Guidelines

1. **Single responsibility** — each Lambda does one thing
2. **Always handle exceptions** with try/except and return structured error responses
3. **Log meaningfully** — CloudWatch logs should tell the story
4. **Return Bedrock-compatible format** for Action Group Lambdas:
   ```python
   return {
       "messageVersion": "1.0",
       "response": {
           "actionGroup": event.get("actionGroup", ""),
           "function": event.get("function", ""),
           "functionResponse": {
               "responseBody": {
                   "TEXT": {"body": json.dumps(result)}
               }
           }
       }
   }
   ```
5. **Set Lambda timeout** to at least 60 seconds (Bedrock can be slow)

---

## 📚 Documentation Standards

- Update `docs/DEPLOYMENT.md` for any infrastructure changes
- Update `docs/API_REFERENCE.md` for any API endpoint changes
- Update `docs/test_execution_report.md` after running tests
- Keep `README.md` accurate — it is the project's front page
- All markdown files must have proper headings, tables, and code blocks

---

## ❓ Questions & Help

Reach out to the relevant team lead based on your area:

- **Bedrock Agent / ARIA issues** → Ch. Vaishnavi
- **Lambda / backend issues** → K. Pavan
- **EventBridge / testing** → K. Rushikesh
- **Frontend / dashboard** → A. Satwika
- **DynamoDB / data** → M. Praneetha
- **API Gateway / coordination** → P. Varun

---

*— AI SOC for AWS · Project Space 8.0 · Team 14 —*
