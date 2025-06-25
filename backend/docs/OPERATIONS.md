# MBA Job Hunter - 運維手冊

本手冊為MBA Job Hunter應用程式的日常運維提供詳細指導，包含監控、維護、故障排除和性能優化。

## 目錄

- [日常維護](#日常維護)
- [監控指標](#監控指標)
- [性能調優](#性能調優)
- [備份恢復](#備份恢復)
- [安全檢查](#安全檢查)
- [故障排除](#故障排除)
- [容量規劃](#容量規劃)
- [緊急響應](#緊急響應)

## 日常維護

### 每日檢查 (自動化)

```bash
#!/bin/bash
# daily_check.sh - 每日自動化檢查腳本

# 1. 健康檢查
python scripts/health_check.py --environment production --output /logs/health_$(date +%Y%m%d).json

# 2. 煙霧測試
python scripts/smoke_test.py --environment production --output /logs/smoke_$(date +%Y%m%d).json

# 3. 系統資源檢查
df -h > /logs/disk_usage_$(date +%Y%m%d).log
free -h > /logs/memory_usage_$(date +%Y%m%d).log
top -bn1 | head -20 > /logs/cpu_usage_$(date +%Y%m%d).log

# 4. 日誌輪轉檢查
logrotate /etc/logrotate.d/mba-job-hunter

# 5. 備份驗證
ls -la /backups/ | tail -5

echo "Daily check completed: $(date)"
```

### 每週檢查

**週一 - 性能檢查：**
```bash
# 數據庫性能分析
psql $DATABASE_URL -c "
SELECT 
    schemaname,
    tablename,
    n_tup_ins + n_tup_upd + n_tup_del as total_writes,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    seq_scan,
    seq_tup_read,
    idx_scan,
    idx_tup_fetch
FROM pg_stat_user_tables 
ORDER BY total_writes DESC;
"

# API性能分析
curl -s http://localhost:8000/metrics | grep http_request_duration_seconds
```

**週三 - 安全檢查：**
```bash
# SSL證書檢查
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com 2>/dev/null | openssl x509 -noout -dates

# 安全更新檢查
apt list --upgradable | grep -i security

# 異常訪問檢查
grep -E "(404|429|500)" /var/log/nginx/access.log | tail -20
```

**週五 - 備份檢查：**
```bash
# 備份完整性檢查
python scripts/backup_verify.py --backup-dir /backups --days 7

# 恢復測試（測試環境）
./scripts/restore_test.sh
```

### 每月檢查

**容量規劃：**
```bash
# 存儲增長趨勢
du -sh /var/lib/docker/volumes/* | sort -h

# 數據庫大小分析
psql $DATABASE_URL -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

**依賴項更新：**
```bash
# Python依賴檢查
pip list --outdated

# Docker鏡像更新
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.CreatedAt}}\t{{.Size}}"
```

## 監控指標

### 系統指標

**關鍵指標：**

| 指標 | 正常範圍 | 警告閾值 | 危險閾值 |
|-----|---------|---------|---------|
| CPU使用率 | < 70% | 70-80% | > 80% |
| 記憶體使用率 | < 75% | 75-85% | > 85% |
| 磁碟使用率 | < 80% | 80-90% | > 90% |
| 磁碟I/O等待 | < 10% | 10-20% | > 20% |
| 網路延遲 | < 50ms | 50-100ms | > 100ms |

**監控查詢：**

```bash
# CPU監控
top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//'

# 記憶體監控
free | grep Mem | awk '{printf "%.2f\n", $3/$2 * 100.0}'

# 磁碟監控
df / | tail -1 | awk '{print $5}' | sed 's/%//'

# 網路監控
ping -c 1 8.8.8.8 | tail -1 | awk '{print $4}' | cut -d '/' -f 2
```

### 應用指標

**HTTP指標：**
```bash
# 請求量統計
curl -s http://localhost:8000/metrics | grep http_requests_total

# 響應時間統計
curl -s http://localhost:8000/metrics | grep http_request_duration_seconds

# 錯誤率統計
curl -s http://localhost:8000/metrics | grep 'http_requests_total.*5..'
```

**業務指標：**
```bash
# 職缺搜索統計
curl -s http://localhost:8000/metrics | grep job_searches_total

# AI分析統計
curl -s http://localhost:8000/metrics | grep job_match_quality

# 用戶活動統計
curl -s http://localhost:8000/metrics | grep user_actions_total
```

### 數據庫指標

```sql
-- 連接數監控
SELECT count(*) as active_connections 
FROM pg_stat_activity 
WHERE state = 'active';

-- 慢查詢監控
SELECT query, calls, total_time, mean_time, rows
FROM pg_stat_statements 
WHERE mean_time > 1000
ORDER BY total_time DESC 
LIMIT 10;

-- 鎖等待監控
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

## 性能調優

### 數據庫優化

**查詢優化：**

```sql
-- 分析查詢計劃
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) 
SELECT * FROM jobs WHERE title ILIKE '%manager%';

-- 更新統計信息
ANALYZE jobs;

-- 重新整理索引
REINDEX INDEX CONCURRENTLY idx_jobs_title_search;
```

**連接池調優：**

```python
# database.py - 生產配置調整
DATABASE_CONFIG = {
    "pool_size": 20,           # 基礎連接數
    "max_overflow": 30,        # 最大溢出連接
    "pool_recycle": 3600,      # 連接回收時間
    "pool_pre_ping": True,     # 連接前測試
    "pool_timeout": 30,        # 連接超時
}
```

**慢查詢優化：**

```sql
-- 啟用慢查詢日誌
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();

-- 查看最慢查詢
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 5;
```

### 應用程式優化

**快取策略：**

```python
# 快取配置優化
CACHE_CONFIG = {
    "job_search_ttl": 1800,      # 30分鐘
    "analysis_ttl": 7200,        # 2小時
    "user_profile_ttl": 86400,   # 24小時
    "max_connections": 50,       # Redis連接池
}
```

**非同步優化：**

```python
# 異步配置調優
ASYNC_CONFIG = {
    "pool_size": 100,            # 異步連接池
    "max_workers": 50,           # 最大工作線程
    "timeout": 30,               # 請求超時
    "keepalive_timeout": 5,      # 保持連接時間
}
```

### 系統優化

**記憶體調優：**

```bash
# /etc/sysctl.conf
vm.swappiness=10
vm.dirty_ratio=15
vm.dirty_background_ratio=5
net.core.rmem_max=134217728
net.core.wmem_max=134217728
```

**檔案描述符限制：**

```bash
# /etc/security/limits.conf
mba-app soft nofile 65536
mba-app hard nofile 65536
```

## 備份恢復

### 自動備份策略

**每日備份腳本：**

```bash
#!/bin/bash
# backup_daily.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# 創建備份目錄
mkdir -p $BACKUP_DIR/daily

# 數據庫備份
echo "Starting database backup..."
pg_dump $DATABASE_URL | gzip > $BACKUP_DIR/daily/db_$DATE.sql.gz

# 應用配置備份
echo "Backing up application config..."
tar -czf $BACKUP_DIR/daily/config_$DATE.tar.gz /app/config

# 日誌備份
echo "Backing up logs..."
tar -czf $BACKUP_DIR/daily/logs_$DATE.tar.gz /app/logs

# 清理舊備份
echo "Cleaning old backups..."
find $BACKUP_DIR/daily -name "*.gz" -mtime +$RETENTION_DAYS -delete

# 驗證備份
echo "Verifying backup..."
gunzip -t $BACKUP_DIR/daily/db_$DATE.sql.gz

# 備份到遠程存儲
echo "Uploading to remote storage..."
aws s3 cp $BACKUP_DIR/daily/db_$DATE.sql.gz s3://mba-job-hunter-backups/

echo "Backup completed: $(date)"
```

**恢復程序：**

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1
TARGET_ENV=${2:-staging}

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file> [environment]"
    exit 1
fi

echo "Starting restore to $TARGET_ENV environment..."

# 停止應用服務
docker-compose down

# 恢復數據庫
echo "Restoring database from $BACKUP_FILE..."
gunzip -c $BACKUP_FILE | psql $DATABASE_URL

# 執行遷移（如果需要）
echo "Running migrations..."
docker-compose run --rm api alembic upgrade head

# 啟動服務
echo "Starting services..."
docker-compose up -d

# 驗證恢復
echo "Verifying restore..."
python scripts/health_check.py --environment $TARGET_ENV

echo "Restore completed: $(date)"
```

### 災難恢復

**完整恢復程序：**

1. **評估損壞範圍**
2. **獲取最新備份**
3. **準備新環境**
4. **恢復數據**
5. **驗證完整性**
6. **切換流量**

**恢復時間目標 (RTO)：**
- 數據庫恢復：< 30分鐘
- 應用重啟：< 5分鐘
- 完整災難恢復：< 2小時

**恢復點目標 (RPO)：**
- 數據丟失：< 1小時
- 配置丟失：< 24小時

## 安全檢查

### 定期安全審計

**每週安全檢查：**

```bash
#!/bin/bash
# security_audit.sh

echo "=== Security Audit Report $(date) ==="

# 1. 檢查SSL證書
echo "1. SSL Certificate Check:"
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com 2>/dev/null | openssl x509 -noout -dates

# 2. 檢查開放端口
echo "2. Open Ports:"
netstat -tuln | grep LISTEN

# 3. 檢查失敗登入
echo "3. Failed Login Attempts:"
grep "authentication failure" /var/log/auth.log | tail -5

# 4. 檢查異常流量
echo "4. Rate Limit Violations:"
grep "429" /var/log/nginx/access.log | wc -l

# 5. 檢查安全更新
echo "5. Security Updates:"
apt list --upgradable | grep -i security

# 6. 檢查文件權限
echo "6. File Permissions:"
find /app -type f -perm /o+w | head -5

# 7. 檢查環境變數洩露
echo "7. Environment Security:"
python scripts/health_check.py --component security
```

**安全配置驗證：**

```bash
# 驗證防火牆規則
sudo ufw status verbose

# 檢查SSH配置
sudo sshd -T | grep -E "(PasswordAuthentication|PermitRootLogin|Port)"

# 驗證Docker安全
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  docker/docker-bench-security
```

### 入侵檢測

**異常檢測腳本：**

```bash
#!/bin/bash
# intrusion_detection.sh

# 檢查異常網路連接
echo "Checking unusual network connections..."
netstat -an | grep ESTABLISHED | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -nr | head -10

# 檢查異常進程
echo "Checking unusual processes..."
ps aux | awk '{print $11}' | sort | uniq -c | sort -nr | head -10

# 檢查文件完整性
echo "Checking file integrity..."
find /app -type f -name "*.py" -newer /tmp/last_check -ls

# 更新檢查時間戳
touch /tmp/last_check
```

## 故障排除

### 常見問題診斷

**應用程式無響應：**

```bash
# 1. 檢查進程狀態
ps aux | grep python

# 2. 檢查端口監聽
netstat -tuln | grep 8000

# 3. 檢查資源使用
top -p $(pgrep python)

# 4. 檢查日誌
tail -f /app/logs/app.log

# 5. 檢查Docker容器
docker ps
docker logs mba-job-hunter-api
```

**數據庫連接問題：**

```bash
# 1. 測試數據庫連接
psql $DATABASE_URL -c "SELECT 1"

# 2. 檢查連接池狀態
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity"

# 3. 檢查鎖等待
psql $DATABASE_URL -c "SELECT * FROM pg_locks WHERE NOT granted"

# 4. 檢查慢查詢
psql $DATABASE_URL -c "SELECT query, state, query_start FROM pg_stat_activity WHERE state != 'idle'"
```

**記憶體洩露診斷：**

```bash
# 1. 監控記憶體使用
watch -n 5 'free -m'

# 2. 檢查進程記憶體
ps aux --sort=-%mem | head -10

# 3. 分析記憶體映射
pmap -x $(pgrep python)

# 4. 檢查交換空間
swapon --show
```

### 效能問題診斷

**響應時間慢：**

```bash
# 1. API響應時間測試
time curl -s http://localhost:8000/health

# 2. 數據庫查詢分析
psql $DATABASE_URL -c "SELECT query, total_time, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 5"

# 3. 網路延遲測試
ping -c 10 yourdomain.com

# 4. 負載測試
ab -n 100 -c 10 http://localhost:8000/health
```

## 容量規劃

### 資源使用趨勢

**月度容量報告：**

```bash
#!/bin/bash
# capacity_report.sh

REPORT_DATE=$(date +%Y%m)
REPORT_FILE="/reports/capacity_$REPORT_DATE.txt"

echo "=== Capacity Report $REPORT_DATE ===" > $REPORT_FILE

# CPU使用趨勢
echo "CPU Usage Trend (Last 30 days):" >> $REPORT_FILE
sar -u 1 1 >> $REPORT_FILE

# 記憶體使用趨勢
echo "Memory Usage Trend:" >> $REPORT_FILE
free -h >> $REPORT_FILE

# 磁碟使用趨勢
echo "Disk Usage Trend:" >> $REPORT_FILE
df -h >> $REPORT_FILE

# 數據庫大小趨勢
echo "Database Size Trend:" >> $REPORT_FILE
psql $DATABASE_URL -c "SELECT pg_size_pretty(pg_database_size('mba_job_hunter_prod'))" >> $REPORT_FILE

# 請求量趨勢
echo "Request Volume Trend:" >> $REPORT_FILE
curl -s http://localhost:8000/metrics | grep http_requests_total >> $REPORT_FILE
```

### 擴展建議

**垂直擴展觸發條件：**
- CPU使用率持續 > 70%
- 記憶體使用率 > 80%
- 磁碟I/O等待 > 15%

**水平擴展觸發條件：**
- 請求響應時間 > 2秒
- 請求隊列長度 > 100
- 錯誤率 > 5%

**擴展計畫：**

```yaml
# 擴展配置
scaling_plan:
  current_capacity:
    cpu: 4 cores
    memory: 8GB
    disk: 100GB
    
  level_1_scaling:  # +50% capacity
    cpu: 6 cores
    memory: 12GB
    disk: 150GB
    
  level_2_scaling:  # +100% capacity
    cpu: 8 cores
    memory: 16GB
    disk: 200GB
    instances: 2
```

## 緊急響應

### 緊急聯絡清單

| 角色 | 聯絡人 | 電話 | Email | 負責領域 |
|-----|-------|------|-------|---------|
| 系統管理員 | 張三 | +886-912-345-678 | admin@company.com | 系統、網路 |
| 數據庫管理員 | 李四 | +886-912-345-679 | dba@company.com | 數據庫 |
| 應用開發者 | 王五 | +886-912-345-680 | dev@company.com | 應用程式 |
| 安全負責人 | 趙六 | +886-912-345-681 | security@company.com | 安全事件 |

### 事件響應程序

**Severity 1 (系統完全無法使用)：**

1. **立即響應 (5分鐘內)**
   - 通知所有關鍵人員
   - 啟動戰情室
   - 開始問題分析

2. **初步評估 (15分鐘內)**
   - 確定影響範圍
   - 評估修復時間
   - 決定是否需要回滾

3. **修復行動 (30分鐘內)**
   - 執行修復步驟
   - 監控修復進度
   - 準備通報內容

**Severity 2 (系統部分功能受影響)：**

1. **響應時間：30分鐘內**
2. **修復目標：2小時內**
3. **通報：受影響用戶**

**事件後檢討：**

```markdown
# 事件後檢討報告模板

## 事件概要
- 事件時間：
- 影響時間：
- 影響範圍：
- 根本原因：

## 時間軸
- [時間] 事件發生
- [時間] 檢測到問題
- [時間] 開始響應
- [時間] 問題解決

## 根本原因分析
- 直接原因：
- 根本原因：
- 貢獻因素：

## 改善措施
- 短期措施：
- 長期措施：
- 負責人：
- 完成時間：
```

### 災難恢復演練

**季度演練計畫：**

```bash
#!/bin/bash
# disaster_recovery_drill.sh

echo "=== Disaster Recovery Drill $(date) ==="

# 1. 模擬災難情境
echo "Simulating disaster scenario..."
docker-compose down

# 2. 啟動恢復程序
echo "Starting recovery procedure..."
./scripts/restore.sh /backups/latest_backup.sql.gz staging

# 3. 驗證恢復結果
echo "Verifying recovery..."
python scripts/health_check.py --environment staging
python scripts/smoke_test.py --environment staging

# 4. 記錄演練結果
echo "Recording drill results..."
echo "Drill completed at $(date)" >> /logs/dr_drill.log

# 5. 清理演練環境
echo "Cleaning up drill environment..."
docker-compose -f docker-compose.staging.yml down
```

**演練檢查清單：**

- [ ] 備份可讀取並完整
- [ ] 數據庫可成功恢復
- [ ] 應用程式可正常啟動
- [ ] 所有功能正常運作
- [ ] 恢復時間符合RTO要求
- [ ] 數據完整性符合RPO要求

## 文檔維護

**運維文檔更新頻率：**
- 每月檢查：程序和配置更新
- 每季檢查：聯絡人和響應計畫
- 每年檢查：整體架構和策略

**版本控制：**
所有運維文檔都應納入版本控制，並與應用程式代碼同步更新。

**培訓計畫：**
- 新團隊成員：完整運維培訓
- 現有成員：季度更新培訓
- 緊急響應：年度演練