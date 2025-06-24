# 🚀 MBA Job Hunter - 部署指南

## ⚡ Task 8 完成後的設置步驟

### 1. GitHub Repository Secrets 設置

在 GitHub repo → **Settings** → **Secrets and variables** → **Actions** 中添加以下 Secrets：

#### 🔑 必要的 Secrets

```bash
# AI API Keys
OPENAI_API_KEY=sk-your_openai_api_key_here
ANTHROPIC_API_KEY=sk-ant-your_anthropic_api_key_here
NOTION_API_KEY=secret_your_notion_integration_token_here

# Database Configuration
DB_USER=your_database_username
DB_PASSWORD=your_database_password
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database

# Redis Configuration
REDIS_URL=redis://user:password@host:6379/0

# Security
SECRET_KEY=your-super-secret-32-character-key-for-production-use
JWT_SECRET_KEY=your-jwt-secret-key-minimum-32-characters-long

# External Services
NOTION_DATABASE_ID=your_notion_database_id_here
INDEED_API_KEY=your_indeed_api_key_if_available

# Deployment Tokens
RAILWAY_TOKEN=your_railway_deployment_token
RAILWAY_APP_URL=https://your-app.railway.app
DOCKER_USERNAME=your_docker_hub_username
DOCKER_PASSWORD=your_docker_hub_password_or_token

# Kubernetes (if using K8s deployment)
KUBE_CONFIG_STAGING=base64_encoded_kubeconfig_for_staging
KUBE_CONFIG_PRODUCTION=base64_encoded_kubeconfig_for_production

# Notification Services
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/slack/webhook
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/webhook

# LinkedIn (使用需謹慎)
LINKEDIN_EMAIL=your-linkedin-email@example.com
LINKEDIN_PASSWORD=your-linkedin-password
```

#### 🔧 可選的 Secrets

```bash
# Monitoring & Analytics
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
DATADOG_API_KEY=your_datadog_api_key
NEW_RELIC_LICENSE_KEY=your_new_relic_license_key

# Cloud Storage
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-s3-bucket-name

# Email Services  
SENDGRID_API_KEY=your_sendgrid_api_key
MAILGUN_API_KEY=your_mailgun_api_key
MAILGUN_DOMAIN=your-mailgun-domain.com

# Additional Webhook URLs
WEBHOOK_URL=https://your-custom-webhook-endpoint.com
TEAMS_WEBHOOK_URL=https://your-teams-webhook-url
```

### 2. 環境變量設置

#### Development Environment (.env)
```bash
cp backend/.env.example backend/.env
```

編輯 `backend/.env` 文件：
```bash
# 基本配置
DEBUG=true
ENVIRONMENT=development
SECRET_KEY=dev-secret-key-not-for-production

# 本地數據庫
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/mba_job_hunter
REDIS_URL=redis://localhost:6379/0

# API Keys (開發環境可使用測試密鑰)
OPENAI_API_KEY=your-dev-openai-key
NOTION_API_KEY=your-dev-notion-key
```

#### Production Environment
生產環境變量通過 CI/CD 管道自動注入，不需要本地 .env 文件。

### 3. 部署平台設置

#### 🚄 Railway 部署

1. **連接 GitHub Repository**
   ```bash
   # 在 Railway Dashboard:
   # 1. 創建新項目
   # 2. 連接 GitHub repo
   # 3. 選擇 backend 目錄作為根目錄
   ```

2. **設置環境變量**
   ```bash
   # 在 Railway 項目設置中添加:
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   OPENAI_API_KEY=your_openai_api_key
   NOTION_API_KEY=your_notion_api_key
   SECRET_KEY=your_production_secret_key
   ENVIRONMENT=production
   ```

3. **添加數據庫服務**
   ```bash
   # 在 Railway 中添加:
   # - PostgreSQL 插件
   # - Redis 插件
   ```

#### 🐳 Docker Hub 部署

1. **設置 Docker Registry**
   ```bash
   # GitHub Secrets:
   DOCKER_USERNAME=your_dockerhub_username
   DOCKER_PASSWORD=your_dockerhub_token
   ```

2. **自動構建和推送**
   - CI/CD 管道會自動構建和推送鏡像
   - 標籤格式: `username/mba-job-hunter:latest`

#### ☸️ Kubernetes 部署

1. **準備 Kubeconfig**
   ```bash
   # 編碼 kubeconfig 文件
   cat ~/.kube/config | base64 -w 0
   
   # 添加到 GitHub Secrets:
   KUBE_CONFIG_STAGING=base64_encoded_content
   KUBE_CONFIG_PRODUCTION=base64_encoded_content
   ```

2. **創建 Kubernetes Secrets**
   ```bash
   kubectl create secret generic mba-job-hunter-secrets \
     --from-literal=database-url="$DATABASE_URL" \
     --from-literal=redis-url="$REDIS_URL" \
     --from-literal=secret-key="$SECRET_KEY" \
     --from-literal=openai-api-key="$OPENAI_API_KEY" \
     --from-literal=notion-api-key="$NOTION_API_KEY" \
     --namespace=staging
   ```

### 4. 通知服務設置

#### 📢 Slack 通知

1. **創建 Slack App**
   - 訪問 https://api.slack.com/apps
   - 創建新應用
   - 啟用 Incoming Webhooks

2. **獲取 Webhook URL**
   ```bash
   # 添加到 GitHub Secrets:
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
   ```

#### 📧 Discord 通知

```bash
# Discord Webhook URL:
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdefghijklmnop
```

### 5. 監控和日誌設置

#### 📊 Sentry 錯誤追踪

1. **創建 Sentry 項目**
   - 訪問 https://sentry.io
   - 創建新項目 (Python/FastAPI)

2. **獲取 DSN**
   ```bash
   # 添加到 GitHub Secrets:
   SENTRY_DSN=https://abcdef123456@o123456.ingest.sentry.io/123456
   ```

#### 📈 應用性能監控

```bash
# DataDog
DATADOG_API_KEY=your_datadog_api_key

# New Relic
NEW_RELIC_LICENSE_KEY=your_new_relic_license_key
```

### 6. 數據庫遷移

#### 🗃️ 生產數據庫設置

1. **創建生產數據庫**
   ```bash
   # PostgreSQL 設置
   CREATE DATABASE mba_job_hunter_prod;
   CREATE USER mba_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE mba_job_hunter_prod TO mba_user;
   ```

2. **運行遷移**
   ```bash
   # 在部署過程中自動運行
   alembic upgrade head
   ```

### 7. SSL/TLS 證書設置

#### 🔒 Let's Encrypt (免費)

```bash
# 使用 Certbot
certbot --nginx -d your-domain.com -d api.your-domain.com
```

#### 🛡️ CloudFlare (推薦)

- 設置 CloudFlare 代理
- 啟用 "Full (strict)" SSL/TLS 加密
- 配置防火牆規則

### 8. 域名和 DNS 設置

#### 🌐 DNS 記錄

```bash
# A Records
api.your-domain.com    → Your-Server-IP
staging.your-domain.com → Staging-Server-IP

# CNAME Records  
www.your-domain.com    → your-domain.com
```

### 9. 備份策略

#### 💾 數據庫備份

```bash
# 每日自動備份 (設置 cron job)
0 2 * * * pg_dump -h host -U user mba_job_hunter_prod > /backups/$(date +\%Y\%m\%d)_backup.sql
```

#### 📦 配置備份

- GitHub Repository (自動)
- 環境變量導出 (定期)
- SSL 證書備份

### 10. 安全檢查清單

#### ✅ 部署前檢查

- [ ] 所有 API 密鑰已設置
- [ ] 數據庫連接正常
- [ ] Redis 連接正常  
- [ ] SSL 證書有效
- [ ] 防火牆規則配置
- [ ] 備份策略已啟用
- [ ] 監控服務運行
- [ ] 日誌收集配置
- [ ] 性能測試通過
- [ ] 安全掃描通過

#### 🔐 安全最佳實踐

- 定期輪換 API 密鑰
- 使用強密碼和多因素認證
- 限制數據庫訪問 IP
- 啟用 WAF (Web Application Firewall)
- 定期更新依賴項
- 監控異常活動

### 11. 故障排除

#### 🐛 常見問題

**數據庫連接失敗:**
```bash
# 檢查連接字符串
echo $DATABASE_URL
# 測試連接
pg_isready -h host -p 5432 -U user
```

**Redis 連接失敗:**
```bash
# 檢查 Redis 服務
redis-cli -u $REDIS_URL ping
```

**API 密鑰無效:**
```bash
# 驗證 OpenAI API
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

**部署失敗:**
```bash
# 檢查 GitHub Actions 日誌
# 驗證所有必需的 secrets 已設置
# 檢查 Docker 鏡像構建日誌
```

### 12. 監控和維護

#### 📊 關鍵指標監控

- API 響應時間
- 數據庫連接池使用率
- Redis 內存使用
- 錯誤率和異常
- 用戶活躍度

#### 🔄 定期維護任務

- 數據庫性能優化
- 日誌清理
- 依賴項更新
- 安全補丁
- 備份驗證

---

## 🎯 快速開始

1. **設置 GitHub Secrets** (上述必要的 secrets)
2. **推送代碼** 觸發 CI/CD 管道
3. **等待部署完成** (約 5-10 分鐘)
4. **驗證部署** 訪問健康檢查端點
5. **配置監控** 設置告警和儀表板

部署完成後，你的應用將可在 `https://your-domain.com` 訪問！