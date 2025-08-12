# MCP Agent 服务器部署指南

## 项目结构
```
mcp-agent/
├── mcp_agent/          # 后端 Python 代码
├── frontend/           # 前端 Vue3 应用
├── requirements.txt    # Python 依赖
├── config.yaml        # MCP Server 配置
└── deploy/            # 部署相关文件
```

## 部署方案

### 方案一：单服务器部署 (推荐)

#### 1. 服务器环境准备

**系统要求:**
- Ubuntu 20.04+ / CentOS 8+ / Rocky Linux 8+
- 至少 2GB RAM, 20GB 存储空间
- Python 3.8+, Node.js 16+

**安装基础依赖:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nodejs npm nginx mongodb

# CentOS/Rocky Linux
sudo yum update -y
sudo yum install -y python3 python3-pip nodejs npm nginx
# MongoDB 需要单独安装
```

#### 2. 用户和目录设置

```bash
# 创建专用用户
sudo useradd -m -s /bin/bash mcpagent
sudo usermod -aG sudo mcpagent

# 创建项目目录
sudo mkdir -p /opt/mcpagent
sudo chown mcpagent:mcpagent /opt/mcpagent

# 切换到专用用户
sudo su - mcpagent
cd /opt/mcpagent
```

#### 3. 后端部署

```bash
# 克隆或上传项目代码
git clone <your-repo-url> .
# 或者通过 scp/rsync 上传代码

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt

# 安装系统级依赖 (用于某些 MCP Server)
sudo npm install -g @modelcontextprotocol/server-puppeteer
pip install uvx  # 用于 SQLite MCP Server
```

#### 4. 前端构建

```bash
cd frontend
npm install
npm run build

# 构建产物在 frontend/dist/ 目录
```

#### 5. 环境配置

```bash
# 创建环境变量文件
cat > /opt/mcpagent/.env << EOF
# OpenAI 配置
API_KEY=your_openai_api_key
BASE_URL=https://api.openai.com/v1
MODEL=gpt-4-turbo-preview

# 数据库配置
MONGO_URI=mongodb://localhost:27017/mcpagent

# 服务配置
HOST=0.0.0.0
PORT=8000
EOF

# 设置权限
chmod 600 /opt/mcpagent/.env
```

#### 6. MongoDB 配置

```bash
# 启动 MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# 创建数据库用户 (可选，用于生产环境)
mongosh --eval "
use mcpagent
db.createUser({
  user: 'mcpagent',
  pwd: 'your_secure_password',
  roles: [{role: 'readWrite', db: 'mcpagent'}]
})
"

# 更新 .env 中的 MONGO_URI
# MONGO_URI=mongodb://mcpagent:your_secure_password@localhost:27017/mcpagent
```

#### 7. Nginx 配置

```bash
sudo tee /etc/nginx/sites-available/mcpagent << EOF
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名或IP

    # 前端静态文件
    location / {
        root /opt/mcpagent/frontend/dist;
        try_files \$uri \$uri/ /index.html;
        
        # 缓存配置
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # 后端 API 代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
    }
    
    # WebSocket 支持 (如需要)
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
}
EOF

# 启用站点
sudo ln -s /etc/nginx/sites-available/mcpagent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 8. 系统服务配置

```bash
# 创建 systemd 服务文件
sudo tee /etc/systemd/system/mcpagent.service << EOF
[Unit]
Description=MCP Agent Backend Service
After=network.target mongodb.service

[Service]
Type=simple
User=mcpagent
Group=mcpagent
WorkingDirectory=/opt/mcpagent
Environment=PATH=/opt/mcpagent/venv/bin
EnvironmentFile=/opt/mcpagent/.env
ExecStart=/opt/mcpagent/venv/bin/uvicorn mcp_agent.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl start mcpagent
sudo systemctl enable mcpagent

# 检查服务状态
sudo systemctl status mcpagent
```

#### 9. 防火墙配置

```bash
# UFW (Ubuntu)
sudo ufw allow 22      # SSH
sudo ufw allow 80      # HTTP
sudo ufw allow 443     # HTTPS
sudo ufw enable

# 或者 firewalld (CentOS/Rocky)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 方案二：Docker 容器化部署

#### 1. Docker 配置文件

**Dockerfile (后端):**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# 复制并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 MCP Server 依赖
RUN npm install -g @modelcontextprotocol/server-puppeteer
RUN pip install uvx

# 复制应用代码
COPY mcp_agent/ ./mcp_agent/
COPY config.yaml .

EXPOSE 8000

CMD ["uvicorn", "mcp_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Dockerfile (前端):**
```dockerfile
FROM node:18-alpine as builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  mongodb:
    image: mongo:7
    restart: always
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: your_secure_password
    volumes:
      - mongodb_data:/data/db
    ports:
      - "27017:27017"

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    restart: always
    environment:
      - API_KEY=your_openai_api_key
      - MONGO_URI=mongodb://admin:your_secure_password@mongodb:27017/mcpagent?authSource=admin
      - MODEL=gpt-4-turbo-preview
    ports:
      - "8000:8000"
    depends_on:
      - mongodb

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    restart: always
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  mongodb_data:
```

#### 2. Docker 部署步骤

```bash
# 克隆代码
git clone <your-repo-url> /opt/mcpagent
cd /opt/mcpagent

# 构建并启动
docker-compose up -d

# 查看状态
docker-compose ps
docker-compose logs -f backend
```

### 方案三：云服务部署

#### 1. 腾讯云/阿里云 ECS

- 选择2核4GB配置的CVM/ECS实例
- 安装宝塔面板或直接使用命令行部署
- 配置安全组开放80、443端口

#### 2. AWS EC2

```bash
# 使用 Ubuntu 22.04 AMI
# t3.small 实例类型 (2 vCPU, 2GB RAM)

# 安全组配置
# - SSH (22): 0.0.0.0/0
# - HTTP (80): 0.0.0.0/0
# - HTTPS (443): 0.0.0.0/0
```

#### 3. Vercel + Railway 分离部署

**前端部署到 Vercel:**
```bash
# 安装 Vercel CLI
npm i -g vercel

# 部署前端
cd frontend
vercel --prod
```

**后端部署到 Railway:**
```bash
# 创建 railway.json
{
  "build": {
    "builder": "nixpacks"
  },
  "deploy": {
    "startCommand": "uvicorn mcp_agent.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health"
  }
}
```

## SSL/HTTPS 配置

### 使用 Let's Encrypt

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 监控和日志

### 1. 应用监控

```bash
# 安装 htop
sudo apt install htop

# 监控脚本
cat > /opt/mcpagent/monitor.sh << EOF
#!/bin/bash
echo "=== MCP Agent 服务状态 ==="
sudo systemctl status mcpagent

echo -e "\n=== 端口监听状态 ==="
sudo netstat -tlnp | grep -E ':8000|:80|:443'

echo -e "\n=== 内存使用情况 ==="
free -h

echo -e "\n=== 磁盘使用情况 ==="
df -h
EOF

chmod +x /opt/mcpagent/monitor.sh
```

### 2. 日志管理

```bash
# 查看应用日志
sudo journalctl -u mcpagent -f

# 查看 Nginx 日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# 日志轮转配置
sudo tee /etc/logrotate.d/mcpagent << EOF
/var/log/mcpagent/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 mcpagent mcpagent
}
EOF
```

## 备份策略

```bash
# 数据库备份脚本
cat > /opt/mcpagent/backup.sh << EOF
#!/bin/bash
DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/mcpagent/backups"

mkdir -p \$BACKUP_DIR

# 备份 MongoDB
mongodump --uri="mongodb://localhost:27017/mcpagent" --out="\$BACKUP_DIR/mongo_\$DATE"

# 备份配置文件
tar -czf "\$BACKUP_DIR/config_\$DATE.tar.gz" /opt/mcpagent/.env /opt/mcpagent/config.yaml

# 清理7天前的备份
find \$BACKUP_DIR -type f -mtime +7 -delete

echo "备份完成: \$DATE"
EOF

chmod +x /opt/mcpagent/backup.sh

# 添加到定时任务
crontab -e
# 添加: 0 2 * * * /opt/mcpagent/backup.sh
```

## 故障排查

### 常见问题

1. **服务无法启动**
   ```bash
   sudo journalctl -u mcpagent --no-pager
   ```

2. **MongoDB 连接失败**
   ```bash
   sudo systemctl status mongod
   mongosh --eval "db.stats()"
   ```

3. **前端无法访问后端**
   - 检查 Nginx 配置
   - 确认防火墙设置
   - 查看后端服务状态

4. **MCP Server 连接问题**
   - 检查 config.yaml 配置
   - 确认 npm/uvx 全局包安装
   - 查看应用日志

### 性能优化

1. **数据库优化**
   ```bash
   # MongoDB 索引
   mongosh mcpagent --eval "
   db.sessions.createIndex({updated_at: -1})
   db.messages.createIndex({session_id: 1, timestamp: 1})
   "
   ```

2. **Nginx 优化**
   ```nginx
   # 在 nginx.conf 中添加
   worker_processes auto;
   worker_connections 1024;
   
   gzip on;
   gzip_types text/plain text/css application/json application/javascript;
   ```

3. **Python 应用优化**
   - 使用 Gunicorn 多进程部署
   - 配置适当的 worker 数量
   - 启用缓存机制

## 安全加固

1. **系统安全**
   ```bash
   # 禁用密码登录，只允许密钥登录
   sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
   sudo systemctl restart ssh
   
   # 安装 fail2ban
   sudo apt install fail2ban
   ```

2. **应用安全**
   - 设置强密码和API密钥
   - 配置适当的CORS策略
   - 定期更新依赖包

3. **网络安全**
   - 使用HTTPS
   - 配置适当的安全头
   - 限制不必要的端口开放

---

*部署完成后，通过 http://your-domain.com 访问应用*
