# 🚀 NBA Fantasy Basketball Platform - Complete Deployment Guide

## 📋 Table of Contents
1. [Local Development Setup](#local-development-setup)
2. [Database Setup](#database-setup)
3. [Testing](#testing)
4. [Production Deployment Options](#production-deployment-options)
5. [Monitoring & Maintenance](#monitoring--maintenance)
6. [Troubleshooting](#troubleshooting)

---

## 🏠 Local Development Setup

### **Prerequisites**
- Python 3.9+ installed
- PostgreSQL 13+ installed
- Git installed
- Terminal/Command Prompt access

### **Step 1: Create Project Directory**

```bash
# Create main project folder
mkdir nba_fantasy_platform
cd nba_fantasy_platform

# Create subdirectories
mkdir sql
mkdir app
mkdir docs
mkdir tests
```

### **Step 2: Download All Files**

Place the 14 files you have in artifacts into the correct folders:

```
nba_fantasy_platform/
├── sql/
│   ├── dbb2_database_schema.sql
│   └── dbb2_scoring_schema.sql
├── app/
│   ├── dbb2_main.py
│   ├── dbb2_database.py
│   ├── dbb2_nba_data_fetcher.py
│   ├── dbb2_scoring_engine.py
│   ├── dbb2_league_db.py
│   ├── dbb2_weekly_tracking.py
│   ├── dbb2_lineup_optimizer.py
│   ├── dbb2_streaming_optimizer.py
│   ├── dbb2_opponent_analyzer.py
│   ├── dbb2_trade_analyzer.py
│   └── dbb2_api_logger.py
├── dbb2_requirements.txt
└── .env (you'll create this)
```

### **Step 3: Install Python Dependencies**

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r dbb2_requirements.txt
```

### **Step 4: Create Environment File**

Create a `.env` file in the root directory:

```bash
# Database
DATABASE_URL=postgresql://localhost/nba_projections

# Server
PORT=8000
DEBUG=True

# Optional: Add later
# SENTRY_DSN=your_sentry_url
# REDIS_URL=redis://localhost:6379
```

---

## 🗄️ Database Setup

### **Step 1: Install PostgreSQL**

**macOS:**
```bash
brew install postgresql@15
brew services start postgresql@15
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
Download installer from: https://www.postgresql.org/download/windows/

### **Step 2: Create Database**

```bash
# Access PostgreSQL
psql postgres

# In psql console:
CREATE DATABASE nba_projections;
CREATE USER nba_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE nba_projections TO nba_user;
\q
```

If using custom user, update `.env`:
```bash
DATABASE_URL=postgresql://nba_user:your_secure_password@localhost/nba_projections
```

### **Step 3: Run Database Schemas**

```bash
# Run main schema
psql -d nba_projections -f sql/dbb2_database_schema.sql

# Run scoring schema
psql -d nba_projections -f sql/dbb2_scoring_schema.sql
```

**Expected output:**
```
✅ Main database schema created successfully!
👥 Demo customers created
🔑 Demo API keys created
...
✅ Scoring schema created successfully!
📊 Tables: leagues, rosters, weekly_performance...
✨ 4 default category presets inserted
```

### **Step 4: Verify Database**

```bash
psql -d nba_projections

# Check tables
\dt

# Should see:
# customers, api_keys, nba_players, leagues, rosters, etc.

# Check demo data
SELECT * FROM customers;
SELECT * FROM api_keys;

\q
```

---

## 🧪 Testing

### **Step 1: Start the API Server**

```bash
# From project root (with venv activated)
cd app
python dbb2_main.py
```

**Expected output:**
```
============================================================
🏀 NBA Fantasy Basketball Platform API
============================================================
✅ Starting server on http://0.0.0.0:8000
📚 API Documentation: http://localhost:8000/docs
🔧 Health Check: http://localhost:8000/health
============================================================
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### **Step 2: Test Health Check**

Open browser or use curl:

```bash
curl http://localhost:8000/health
```

**Expected:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### **Step 3: Test API Documentation**

Open in browser: `http://localhost:8000/docs`

You should see **interactive Swagger UI** with all 50+ endpoints!

### **Step 4: Test with Demo API Key**

```bash
# Test 5-year projection
curl -H "X-API-Key: free_demo_key_12345" \
  http://localhost:8000/projections/5year/201939

# Test account endpoint
curl -H "X-API-Key: pro_demo_key_67890" \
  http://localhost:8000/account

# Test player search
curl -H "X-API-Key: free_demo_key_12345" \
  "http://localhost:8000/players?q=curry"
```

### **Step 5: Test Complete Workflow**

```bash
# 1. Create a league
curl -X POST http://localhost:8000/leagues \
  -H "X-API-Key: pro_demo_key_67890" \
  -H "Content-Type: application/json" \
  -d '{
    "league_name": "Test League",
    "scoring_type": "roto",
    "categories": ["PTS", "REB", "AST", "STL", "BLK"],
    "weekly_targets": {
      "PTS": 712,
      "REB": 196,
      "AST": 142,
      "STL": 54,
      "BLK": 41
    }
  }'

# 2. Add a player (use league_id from above)
curl -X POST http://localhost:8000/leagues/{LEAGUE_ID}/roster \
  -H "X-API-Key: pro_demo_key_67890" \
  -H "Content-Type: application/json" \
  -d '{
    "player_id": 201939,
    "player_name": "Stephen Curry",
    "player_team": "GSW",
    "player_position": "PG,SG"
  }'

# 3. Get league score
curl -H "X-API-Key: pro_demo_key_67890" \
  http://localhost:8000/leagues/{LEAGUE_ID}/score
```

---

## 🌐 Production Deployment Options

### **Option 1: AWS Elastic Beanstalk (Easiest)**

#### **1. Install EB CLI**
```bash
pip install awsebcli
```

#### **2. Initialize EB**
```bash
cd nba_fantasy_platform
eb init -p python-3.9 nba-fantasy-platform --region us-east-1
```

#### **3. Create Environment**
```bash
eb create nba-fantasy-prod
```

#### **4. Set Environment Variables**
```bash
eb setenv DATABASE_URL=your_rds_connection_string
```

#### **5. Deploy**
```bash
eb deploy
```

**Estimated Cost:** $50-100/month

---

### **Option 2: Heroku (Fastest)**

#### **1. Create `Procfile`**
```
web: cd app && uvicorn dbb2_main:app --host 0.0.0.0 --port $PORT
```

#### **2. Create `runtime.txt`**
```
python-3.9.16
```

#### **3. Deploy**
```bash
heroku create nba-fantasy-platform
heroku addons:create heroku-postgresql:mini
git push heroku main
```

**Estimated Cost:** $25-50/month

---

### **Option 3: DigitalOcean App Platform (Balanced)**

#### **1. Create `app.yaml`**
```yaml
name: nba-fantasy-platform
services:
  - name: api
    source_dir: app
    github:
      repo: your-username/nba-fantasy-platform
      branch: main
    run_command: uvicorn dbb2_main:app --host 0.0.0.0 --port 8080
    envs:
      - key: DATABASE_URL
        value: ${db.DATABASE_URL}
databases:
  - name: db
    engine: PG
    version: "15"
```

#### **2. Deploy via UI**
- Push code to GitHub
- Connect DigitalOcean to GitHub
- Deploy from dashboard

**Estimated Cost:** $17-40/month

---

### **Option 4: Docker + VPS (Most Control)**

#### **1. Create `Dockerfile`**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY dbb2_requirements.txt .
RUN pip install --no-cache-dir -r dbb2_requirements.txt

COPY app/ ./app/
COPY sql/ ./sql/

WORKDIR /app/app

CMD ["uvicorn", "dbb2_main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### **2. Create `docker-compose.yml`**
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/nba_projections
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=nba_projections
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql:/docker-entrypoint-initdb.d

volumes:
  postgres_data:
```

#### **3. Deploy**
```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f api
```

#### **4. Deploy to VPS**
```bash
# Copy to server
scp -r nba_fantasy_platform user@your-server.com:/home/user/

# SSH to server
ssh user@your-server.com

# Run
cd nba_fantasy_platform
docker-compose up -d
```

**Estimated Cost:** $5-20/month (VPS) + domain

---

## 📊 Monitoring & Maintenance

### **Setup Monitoring**

#### **1. Add Sentry (Error Tracking)**
```bash
pip install sentry-sdk
```

In `dbb2_main.py`:
```python
import sentry_sdk

sentry_sdk.init(
    dsn="your_sentry_dsn",
    traces_sample_rate=1.0
)
```

#### **2. Add Uptime Monitoring**
- **UptimeRobot** (free): https://uptimerobot.com
- Monitor `/health` endpoint every 5 minutes
- Get alerts via email/SMS

#### **3. Setup Log Aggregation**
```bash
# For production logging
pip install python-json-logger
```

### **Database Maintenance**

#### **Daily Backup Script**
```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d)
pg_dump nba_projections > backup_$DATE.sql
gzip backup_$DATE.sql

# Upload to S3 (optional)
aws s3 cp backup_$DATE.sql.gz s3://your-bucket/backups/
```

Run via cron:
```bash
crontab -e

# Add:
0 2 * * * /path/to/backup.sh
```

#### **Weekly Cleanup**
```bash
# Clean old logs (runs via API)
curl -X POST http://localhost:8000/admin/cleanup-logs?days=30 \
  -H "X-API-Key: your_enterprise_key"
```

### **Performance Optimization**

#### **Add Redis Caching**
```bash
pip install redis

# In dbb2_main.py
import redis
cache = redis.Redis(host='localhost', port=6379, db=0)

# Cache projections for 1 hour
@app.get("/projections/5year/{player_id}")
async def get_5year_projection(player_id: int, x_api_key: str = Header(...)):
    cache_key = f"proj_5year_{player_id}"
    cached = cache.get(cache_key)
    
    if cached:
        return json.loads(cached)
    
    projection = nba.calculate_5year_average(player_id)
    cache.setex(cache_key, 3600, json.dumps(projection))
    
    return projection
```

---

## 🐛 Troubleshooting

### **Issue: Database Connection Failed**

**Error:** `could not connect to server`

**Solutions:**
```bash
# Check PostgreSQL is running
brew services list  # macOS
sudo systemctl status postgresql  # Linux

# Restart PostgreSQL
brew services restart postgresql@15  # macOS
sudo systemctl restart postgresql  # Linux

# Verify DATABASE_URL in .env
echo $DATABASE_URL
```

---

### **Issue: Module Not Found**

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r dbb2_requirements.txt
```

---

### **Issue: Port Already in Use**

**Error:** `Address already in use`

**Solution:**
```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Or use different port
uvicorn dbb2_main:app --port 8001
```

---

### **Issue: NBA API Rate Limiting**

**Error:** `Too many requests`

**Solution:**
```python
# Add delay between requests in dbb2_nba_data_fetcher.py
import time

def get_player_career_stats(player_id: int):
    time.sleep(0.6)  # 600ms delay
    # ... rest of function
```

---

### **Issue: Demo Keys Not Working**

**Error:** `Invalid API key`

**Solution:**
```bash
# Re-run database schema
psql -d nba_projections -f sql/dbb2_database_schema.sql

# Verify demo keys exist
psql -d nba_projections -c "SELECT * FROM api_keys;"
```

---

## 📈 Scaling Checklist

When you get to **100+ customers:**

- [ ] Add Redis caching
- [ ] Implement database read replicas
- [ ] Add CDN for static assets
- [ ] Setup load balancer (nginx/AWS ALB)
- [ ] Move to managed database (AWS RDS/DigitalOcean)
- [ ] Add API versioning
- [ ] Implement rate limiting per tier
- [ ] Setup CI/CD pipeline
- [ ] Add comprehensive test suite

---

## 🎯 Launch Checklist

Before going live:

- [ ] All 14 files in correct directories
- [ ] Database schemas run successfully
- [ ] All tests passing
- [ ] Demo API keys working
- [ ] Environment variables configured
- [ ] Backup system setup
- [ ] Monitoring/alerting configured
- [ ] Domain name purchased
- [ ] SSL certificate setup (Let's Encrypt)
- [ ] CORS configured for your domain
- [ ] Rate limits tested
- [ ] Documentation updated
- [ ] Terms of Service written
- [ ] Privacy Policy written
- [ ] Payment system integrated (Stripe)

---

## 🚀 Next Steps

1. **Test locally** following this guide
2. **Choose deployment option** (recommend DigitalOcean for balance)
3. **Deploy to staging** environment first
4. **Test with real data**
5. **Deploy to production**
6. **Market your platform!**

---

## 📞 Support Resources

- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **NBA API Docs:** https://github.com/swar/nba_api
- **Deployment Tutorials:**
  - Heroku: https://devcenter.heroku.com/articles/python
  - AWS: https://docs.aws.amazon.com/elasticbeanstalk/
  - DigitalOcean: https://docs.digitalocean.com/products/app-platform/

---

## 🎉 You're Ready to Launch!

Your complete NBA Fantasy Basketball Platform is ready for deployment. Good luck! 🏀🚀