# MBA Job Hunter - 生產級求職平台

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-red.svg)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)

企業級MBA求職平台，提供智能職缺搜索、AI分析匹配、多平台數據整合等功能。專為中文使用者設計，具備完整的生產環境部署與運維支援。

## 🌟 核心特色

### 智能求職功能
- **智能職缺搜索**: 支援多關鍵字、地點、經驗等級篩選
- **AI匹配分析**: 基於使用者背景進行職缺適配度分析
- **多平台整合**: 支援LinkedIn、Indeed、104等主流平台
- **職缺管理**: 收藏、分類、匯出職缺至Notion等工具

### 企業級架構
- **高可用性**: 零停機部署、自動故障恢復
- **安全防護**: 多層安全防護、SQL注入防護、速率限制
- **性能優化**: 數據庫索引優化、連接池管理、快取策略
- **監控告警**: Prometheus指標、健康檢查、結構化日誌

### 生產就緒
- **多環境部署**: Railway、Heroku、Docker、Kubernetes
- **自動化運維**: 部署腳本、健康檢查、煙霧測試
- **完整文檔**: 中文運維手冊、部署指南、故障排除
- **測試覆蓋**: 端到端測試、安全測試、性能測試

## 🚀 快速開始

### 前置要求

```bash
# 系統要求
- Python 3.11+
- PostgreSQL 15+
- Redis 7+ (可選)
- Docker & Docker Compose
```

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

### 開發環境設置

```bash
# 1. 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 2. 安裝依賴
pip install -r requirements.txt

# 3. 配置開發環境
cp .env.example .env
# 編輯 .env 設置開發用配置

# 4. 初始化資料庫
alembic upgrade head

# 5. 啟動開發伺服器
uvicorn app.main:app --reload
```

## 📁 專案結構

```
backend/
├── app/                          # 應用程式核心
│   ├── api/                      # API 路由
│   ├── core/                     # 核心配置和工具
│   │   ├── config.py            # 配置管理
│   │   ├── database.py          # 資料庫連接
│   │   ├── security.py          # 安全工具
│   │   └── exceptions.py        # 自定義例外
│   ├── middleware/               # 中介軟體
│   │   ├── security.py          # 安全中介軟體
│   │   ├── monitoring.py        # 監控中介軟體
│   │   └── error_handler.py     # 錯誤處理
│   ├── models/                   # 資料模型
│   ├── services/                 # 業務邏輯
│   ├── utils/                    # 工具函數
│   │   ├── metrics.py           # 指標收集
│   │   └── error_handler.py     # 錯誤處理工具
│   └── main.py                   # 應用程式入口
├── alembic/                      # 資料庫遷移
├── scripts/                      # 運維腳本
│   ├── deploy.sh                # 部署腳本
│   ├── health_check.py          # 健康檢查
│   └── smoke_test.py            # 煙霧測試
├── tests/                        # 測試套件
│   ├── test_production/         # 生產環境測試
│   │   ├── test_end_to_end.py   # 端到端測試
│   │   └── test_security.py     # 安全測試
├── docs/                         # 文檔
│   ├── DEPLOYMENT.md            # 部署指南
│   └── OPERATIONS.md            # 運維手冊
├── .env.production              # 生產環境配置
├── railway.json                 # Railway 部署配置
├── app.json                     # Heroku 部署配置
└── requirements.txt             # Python 依賴
```

## 🔧 核心功能

### 1. 職缺搜索API

```python
POST /api/v1/jobs/search
{
    "keywords": ["MBA", "管理", "策略"],
    "location": "台北",
    "experience_level": "entry",
    "limit": 20
}
```

### 2. AI匹配分析

```python
POST /api/v1/analysis/analyze
{
    "job_id": "job-123",
    "user_profile": {
        "education": "MBA",
        "experience_years": 2,
        "skills": ["分析", "管理", "策略"],
        "preferences": {
            "industry": ["科技", "金融"],
            "company_size": "大型企業"
        }
    }
}
```

### 3. 健康檢查

```python
GET /health
# 回應: {"status": "healthy", "timestamp": "2024-06-25T10:00:00Z"}

GET /health/detailed
# 詳細健康狀態包含資料庫、Redis、外部API狀態
```

### 4. 指標監控

```python
GET /metrics
# Prometheus 格式指標
# 包含: HTTP請求、資料庫連接、業務指標等
```

## 🛡️ 安全特性

### 多層安全防護

- **輸入驗證**: 嚴格的資料驗證和清理
- **SQL注入防護**: 自動檢測和阻擋惡意查詢
- **XSS防護**: HTML標籤過濾和編碼
- **速率限制**: Redis分散式限流
- **安全標頭**: HSTS、CSP、XSS Protection等

### 驗證和授權

```python
# JWT Token 驗證
headers = {"Authorization": "Bearer <jwt-token>"}

# API Key 驗證
headers = {"X-API-Key": "<api-key>"}
```

### 資料加密

```python
# 敏感資料加密存儲
encrypted_data = encryption_manager.encrypt(sensitive_data)
decrypted_data = encryption_manager.decrypt(encrypted_data)
```

## 📊 監控和指標

### 系統指標

| 指標類型 | 監控項目 | 警告閾值 |
|---------|---------|---------|
| CPU使用率 | system_cpu_usage_percent | > 80% |
| 記憶體使用率 | system_memory_usage_percent | > 85% |
| 磁碟使用率 | system_disk_usage_percent | > 90% |
| HTTP請求 | http_requests_total | - |
| 響應時間 | http_request_duration_seconds | > 2s |

### 業務指標

- `job_searches_total`: 職缺搜索總數
- `job_match_quality`: AI匹配品質評分
- `user_actions_total`: 使用者行為統計
- `external_api_calls_total`: 外部API調用統計

### 告警設置

```yaml
# 關鍵指標告警
alerts:
  - name: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    
  - name: SlowResponse
    expr: histogram_quantile(0.95, http_request_duration_seconds) > 2
    
  - name: DatabaseDown
    expr: up{job="database"} == 0
```

## 🚀 部署選項

### 1. Railway 部署

```bash
# 自動部署 (推薦)
railway login
railway link [project-id]
railway up
```

### 2. Heroku 部署

```bash
# 一鍵部署
heroku create mba-job-hunter-prod
git push heroku main
```

### 3. Docker 部署

```bash
# 容器化部署
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 4. Kubernetes 部署

```bash
# 雲原生部署
kubectl apply -f k8s/
```

## 🧪 測試

### 運行測試套件

```bash
# 單元測試
pytest tests/ -v

# 生產環境測試
pytest tests/test_production/ -v

# 安全測試
pytest tests/test_production/test_security.py -v

# 端到端測試
pytest tests/test_production/test_end_to_end.py -v
```

### 煙霧測試

```bash
# 快速驗證
python scripts/smoke_test.py --environment production

# 詳細測試
python scripts/smoke_test.py --environment production --verbose
```

### 健康檢查

```bash
# 基本健康檢查
python scripts/health_check.py

# 完整系統檢查
python scripts/health_check.py --component all --verbose
```

## 🔧 配置管理

### 環境變數

```bash
# 核心配置
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-key-min-32-chars-long
JWT_SECRET_KEY=your-jwt-secret-key-min-32-chars-long

# 資料庫配置
DATABASE_URL=postgresql://user:password@host:5432/mba_job_hunter_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis配置
REDIS_URL=redis://host:6379/0
REDIS_PASSWORD=your-redis-password

# 外部API
OPENAI_API_KEY=your-openai-api-key
NOTION_API_KEY=your-notion-api-key
LINKEDIN_CLIENT_ID=your-linkedin-client-id
LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
```

### 安全配置

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

## 📚 文檔資源

### 部署和運維

- [📖 部署指南](docs/DEPLOYMENT.md) - 完整的生產環境部署指南
- [📖 運維手冊](docs/OPERATIONS.md) - 日常運維和故障排除
- [📖 API文檔](http://localhost:8000/docs) - 互動式API文檔

### 最佳實踐

1. **安全最佳實踐**
   - 定期更新依賴項
   - 實施最小權限原則
   - 啟用所有安全中介軟體
   - 定期進行安全審計

2. **性能最佳實踐**
   - 使用資料庫連接池
   - 實施適當的快取策略
   - 監控和優化慢查詢
   - 定期清理過期資料

3. **運維最佳實踐**
   - 自動化部署流程
   - 實施全面監控
   - 定期備份資料
   - 準備災難恢復計畫

## 🐛 故障排除

### 常見問題

**應用程式無法啟動**
```bash
# 檢查日誌
docker-compose logs api

# 驗證配置
python scripts/health_check.py --component security
```

**資料庫連接失敗**
```bash
# 測試連接
psql $DATABASE_URL -c "SELECT 1"

# 檢查連接池
python scripts/health_check.py --component database
```

**外部API調用失敗**
```bash
# 檢查API金鑰
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# 檢查網路連接
python scripts/health_check.py --component external_apis
```

### 效能調優

**慢查詢優化**
```sql
-- 啟用慢查詢日誌
SET log_min_duration_statement = 1000;

-- 查看最慢查詢
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;
```

**記憶體使用分析**
```bash
# 檢查記憶體使用
free -h
docker stats

# 分析應用記憶體
python scripts/health_check.py --component system
```

## 🤝 貢獻指南

### 開發流程

1. Fork 專案
2. 創建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

### 代碼規範

```bash
# 代碼格式化
black app/ tests/
isort app/ tests/

# 程式碼檢查
flake8 app/ tests/
mypy app/

# 安全檢查
bandit -r app/
```

### 測試要求

- 新功能必須包含單元測試
- 確保所有測試通過
- 維持測試覆蓋率 > 80%
- 包含安全測試用例

## 📄 授權條款

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案

## 📞 技術支援

### 聯絡資訊

- **Email**: support@mba-job-hunter.com
- **文檔**: [部署指南](docs/DEPLOYMENT.md) | [運維手冊](docs/OPERATIONS.md)
- **監控**: [Grafana Dashboard](https://grafana.yourdomain.com)
- **日誌**: [Kibana](https://kibana.yourdomain.com)

### 支援資源

- 🐛 [問題回報](https://github.com/your-org/mba-job-hunter/issues)
- 💬 [討論區](https://github.com/your-org/mba-job-hunter/discussions)
- 📚 [Wiki文檔](https://github.com/your-org/mba-job-hunter/wiki)
- 🔄 [更新日誌](https://github.com/your-org/mba-job-hunter/releases)

---

**MBA Job Hunter** - 用技術賦能求職，用智慧連接機會 🚀

*建構於 FastAPI、PostgreSQL、Redis 之上的現代化求職平台*