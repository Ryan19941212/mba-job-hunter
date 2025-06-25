# MBA Job Hunter - 生產環境部署指南

本文檔提供MBA Job Hunter應用程式的完整生產環境部署指南，包含安全配置、性能優化和最佳實踐。

## 目錄

- [快速開始](#快速開始)
- [環境準備](#環境準備)
- [配置設定](#配置設定)
- [部署方式](#部署方式)
- [數據庫設置](#數據庫設置)
- [安全配置](#安全配置)
- [監控設置](#監控設置)
- [故障排除](#故障排除)

## 快速開始

### 前置要求

- Docker & Docker Compose
- Git
- Python 3.11+
- PostgreSQL 15+ (生產環境)
- Redis 7+ (可選，用於快取和限流)

### 一鍵部署

```bash
# 1. 克隆專案
git clone <repository-url>
cd mba-job-hunter/backend

# 2. 配置環境變數
cp .env.production.example .env.production
# 編輯 .env.production 設置實際值

# 3. 執行部署
./scripts/deploy.sh production

# 4. 驗證部署
python scripts/health_check.py --environment production
python scripts/smoke_test.py --environment production
```

## 環境準備

### 1. 系統要求

**最低配置：**
- CPU: 2 cores
- RAM: 4GB
- 存儲: 20GB SSD
- 網路: 100Mbps

**推薦配置：**
- CPU: 4+ cores
- RAM: 8GB+
- 存儲: 50GB+ SSD
- 網路: 1Gbps

### 2. 軟體依賴

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y docker.io docker-compose git python3 python3-pip curl

# CentOS/RHEL
sudo yum install -y docker docker-compose git python3 python3-pip curl

# 啟動Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### 3. 安全設置

```bash
# 創建應用用戶
sudo useradd -m -s /bin/bash mba-app
sudo usermod -aG docker mba-app

# 設置防火牆
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

## 配置設定

### 1. 環境變數配置

**必要配置：**

```bash
# .env.production
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-key-min-32-chars-long
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars-long

# 數據庫
DATABASE_URL=postgresql://user:password@host:5432/mba_job_hunter_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis
REDIS_URL=redis://host:6379/0
REDIS_PASSWORD=your-redis-password

# 外部API
OPENAI_API_KEY=your-openai-api-key
NOTION_API_KEY=your-notion-api-key
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
```

**安全配置：**

```bash
# CORS設定
CORS_ALLOWED_ORIGINS=["https://yourdomain.com"]

# 速率限制
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST=20

# SSL設定
SSL_CERTFILE=/path/to/cert.pem
SSL_KEYFILE=/path/to/key.pem
```

### 2. 配置驗證

```bash
# 驗證配置
python scripts/health_check.py --component security
```

## 部署方式

### 方式一：Railway 部署

1. **準備Railway配置**
   ```bash
   # railway.json已包含完整配置
   railway login
   railway link [project-id]
   ```

2. **設置環境變數**
   ```bash
   railway variables set SECRET_KEY=your-secret-key
   railway variables set DATABASE_URL=your-database-url
   # ... 其他變數
   ```

3. **部署**
   ```bash
   railway up
   ```

### 方式二：Heroku 部署

1. **安裝Heroku CLI**
   ```bash
   curl https://cli-assets.heroku.com/install.sh | sh
   heroku login
   ```

2. **創建應用**
   ```bash
   heroku create mba-job-hunter-prod
   heroku addons:create heroku-postgresql:standard-0
   heroku addons:create heroku-redis:premium-0
   ```

3. **配置環境變數**
   ```bash
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set ENVIRONMENT=production
   # ... 其他變數
   ```

4. **部署**
   ```bash
   git push heroku main
   ```

### 方式三：Docker Compose 部署

1. **生產配置**
   ```yaml
   # docker-compose.prod.yml
   version: '3.8'
   services:
     api:
       build: .
       environment:
         - ENVIRONMENT=production
       restart: unless-stopped
       ports:
         - "8000:8000"
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
         interval: 30s
         timeout: 10s
         retries: 3
   ```

2. **部署**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

### 方式四：Kubernetes 部署

1. **創建配置文件**
   ```yaml
   # k8s/deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: mba-job-hunter
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: mba-job-hunter
     template:
       metadata:
         labels:
           app: mba-job-hunter
       spec:
         containers:
         - name: api
           image: mba-job-hunter:latest
           ports:
           - containerPort: 8000
           env:
           - name: ENVIRONMENT
             value: "production"
           resources:
             requests:
               memory: "512Mi"
               cpu: "250m"
             limits:
               memory: "1Gi"
               cpu: "500m"
   ```

2. **部署**
   ```bash
   kubectl apply -f k8s/
   ```

## 數據庫設置

### 1. PostgreSQL 配置

**生產配置優化：**

```sql
-- postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 256MB
max_connections = 200
```

**安全設置：**

```sql
-- pg_hba.conf
hostssl all all 0.0.0.0/0 md5
```

### 2. 數據庫遷移

```bash
# 執行遷移
./scripts/deploy.sh production

# 手動遷移
docker-compose exec api alembic upgrade head

# 性能索引
docker-compose exec api alembic upgrade perf_indexes_001
```

### 3. 備份策略

```bash
# 自動備份腳本
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/mba_job_hunter_$DATE.sql"

pg_dump $DATABASE_URL > $BACKUP_FILE
gzip $BACKUP_FILE

# 保留30天備份
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

## 安全配置

### 1. SSL/TLS 設置

**使用Let's Encrypt：**

```bash
# 安裝Certbot
sudo apt install certbot python3-certbot-nginx

# 獲取證書
sudo certbot --nginx -d yourdomain.com

# 自動續期
sudo crontab -e
0 12 * * * /usr/bin/certbot renew --quiet
```

### 2. 防火牆配置

```bash
# UFW配置
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 3. 安全標頭

應用程式已自動設置以下安全標頭：

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`
- `Content-Security-Policy: default-src 'self'`

### 4. 速率限制

```bash
# Redis配置用於分散式限流
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST=20
RATE_LIMIT_STORAGE_URL=${REDIS_URL}
```

## 監控設置

### 1. 健康檢查

```bash
# 基本健康檢查
curl http://localhost:8000/health

# 詳細健康檢查
python scripts/health_check.py --verbose

# 持續監控
watch -n 30 'curl -s http://localhost:8000/health | jq'
```

### 2. Prometheus 指標

**配置Prometheus：**

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'mba-job-hunter'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

**指標說明：**

- `http_requests_total` - HTTP請求總數
- `http_request_duration_seconds` - 請求響應時間
- `job_searches_total` - 職缺搜索總數
- `system_cpu_usage_percent` - CPU使用率
- `database_connections_active` - 活躍數據庫連接

### 3. 日誌管理

**結構化日誌：**

```json
{
  "timestamp": "2024-06-24T10:00:00Z",
  "level": "INFO",
  "message": "Job search completed",
  "request_id": "req_123",
  "user_id": "user_456",
  "duration_ms": 150,
  "results_count": 25
}
```

**日誌聚合：**

```bash
# 使用ELK Stack或簡單的日誌監控
tail -f logs/app.log | jq
```

### 4. 警報設置

**關鍵指標警報：**

- CPU使用率 > 80%
- 記憶體使用率 > 85%
- 錯誤率 > 5%
- 響應時間 > 2秒
- 數據庫連接失敗

## 故障排除

### 1. 常見問題

**問題：應用程式無法啟動**

```bash
# 檢查日誌
docker-compose logs api

# 檢查配置
python scripts/health_check.py --component security

# 驗證環境變數
env | grep -E "(SECRET_KEY|DATABASE_URL)"
```

**問題：數據庫連接失敗**

```bash
# 測試數據庫連接
psql $DATABASE_URL -c "SELECT 1"

# 檢查連接池狀態
python scripts/health_check.py --component database
```

**問題：外部API調用失敗**

```bash
# 檢查API金鑰
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# 檢查網路連接
python scripts/health_check.py --component external_apis
```

### 2. 性能問題

**慢查詢診斷：**

```sql
-- 啟用慢查詢日誌
SET log_min_duration_statement = 1000;

-- 查看慢查詢
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;
```

**記憶體使用分析：**

```bash
# 檢查記憶體使用
free -h
docker stats

# 分析應用記憶體
python scripts/health_check.py --component system
```

### 3. 安全事件響應

**異常流量檢測：**

```bash
# 檢查訪問日誌
grep "429" logs/access.log | wc -l

# 分析IP地址
awk '{print $1}' logs/access.log | sort | uniq -c | sort -nr | head -10
```

**安全事件日誌：**

```bash
# 查看安全日誌
grep "security_threat" logs/app.log | jq
```

### 4. 緊急恢復

**回滾部署：**

```bash
# 使用部署腳本回滾
./scripts/deploy.sh production --rollback

# 手動回滾
git checkout previous-version
docker-compose up -d --build
```

**數據庫恢復：**

```bash
# 從備份恢復
gunzip backup_20240624_100000.sql.gz
psql $DATABASE_URL < backup_20240624_100000.sql
```

## 最佳實踐

### 1. 部署檢查清單

- [ ] 環境變數已設置並驗證
- [ ] SSL證書已配置
- [ ] 數據庫遷移已執行
- [ ] 性能索引已創建
- [ ] 健康檢查通過
- [ ] 煙霧測試通過
- [ ] 監控已設置
- [ ] 備份策略已實施
- [ ] 安全配置已檢查
- [ ] 日誌聚合已配置

### 2. 運營準備

- [ ] 運維文檔已準備
- [ ] 緊急聯絡人已設置
- [ ] 回滾計畫已測試
- [ ] 性能基準已建立
- [ ] 容量規劃已完成
- [ ] 安全響應計畫已準備

### 3. 持續改進

- 定期安全掃描
- 性能基準測試
- 容量規劃檢查
- 依賴項更新
- 備份恢復測試
- 災難恢復演練

## 支援聯絡

如需技術支援，請聯絡：

- **Email**: support@mba-job-hunter.com
- **文檔**: [運維手冊](OPERATIONS.md)
- **監控**: [Grafana Dashboard](https://grafana.yourdomain.com)
- **日誌**: [Kibana](https://kibana.yourdomain.com)