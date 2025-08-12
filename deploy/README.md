# MCP Agent 阿里云 ECS 部署指南

## 🚀 快速部署

### 服务器信息
- **公网IP**: 47.86.96.112
- **系统**: CentOS 7.7 64位
- **配置**: 2核2GB
- **区域**: 中国香港

### 方法一：一键部署 (推荐)

```bash
# 1. 连接服务器
ssh root@47.86.96.112

# 2. 上传项目代码
cd /opt
git clone <your-repo-url> mcpagent
# 或使用 scp: scp -r ./mcp-agent root@47.86.96.112:/opt/mcpagent

# 3. 执行一键部署
cd /opt/mcpagent
./deploy/centos-install.sh

# 4. 配置 API Key
vim /opt/mcpagent/.env
# 修改 API_KEY=your_openai_api_key_here

# 5. 重启服务
systemctl restart mcpagent
```

### 版本信息

- **Python**: 3.13.5 (从源码编译安装)
- **API配置**: 已预配置豆包AI
  - **API地址**: https://ark.cn-beijing.volces.com/api/v3
  - **模型**: doubao-1-5-pro-32k-250115
  - **API Key**: 已配置

## 🔧 部署后配置

### 1. 确认 API 配置

```bash
# 查看当前配置
cat /opt/mcpagent/.env

# 配置已预设为豆包AI，如需修改：
vim /opt/mcpagent/.env

# 重启服务使配置生效
systemctl restart mcpagent
```

### 2. 配置域名 (可选)

如果您有域名，可以配置域名访问：

```bash
# 修改 Nginx 配置
vim /etc/nginx/nginx.conf

# 将 server_name 改为您的域名
server_name your-domain.com;

# 重启 Nginx
systemctl restart nginx

# SSL 配置可使用其他工具，如 Let's Encrypt
# certbot --nginx -d your-domain.com
```

### 3. 配置阿里云安全组

在阿里云控制台 -> ECS -> 安全组，确保开放：
- 端口 22 (SSH)
- 端口 80 (HTTP)
- 端口 443 (HTTPS)

## 📊 访问应用

部署完成后，通过以下地址访问：

- **前端应用**: http://47.86.96.112
- **API 接口**: http://47.86.96.112/api
- **健康检查**: http://47.86.96.112/health

## 🛠️ 管理命令

### 服务管理

```bash
# 查看服务状态
systemctl status mcpagent

# 启动/停止/重启服务
systemctl start mcpagent
systemctl stop mcpagent
systemctl restart mcpagent

# 查看日志
journalctl -u mcpagent -f

# 查看系统状态
/opt/mcpagent/status.sh
```

### 应用更新

```bash
cd /opt/mcpagent

# 拉取最新代码
git pull

# 重新安装依赖
source venv/bin/activate
pip install -r requirements.txt

# 重新构建前端
cd frontend
npm install
npm run build
cd ..

# 重启服务
systemctl restart mcpagent
systemctl reload nginx
```

### 数据库管理

```bash
# 连接 MongoDB
mongo

# 查看数据库
show dbs
use mcpagent
show collections

# 备份数据库
mongodump --db mcpagent --out /opt/mcpagent/backup/$(date +%Y%m%d)

# 恢复数据库
mongorestore --db mcpagent /opt/mcpagent/backup/20240101/mcpagent/
```

## 🔍 故障排查

### 1. 服务无法启动

```bash
# 查看详细错误日志
journalctl -u mcpagent --no-pager -l

# 检查端口占用
netstat -tlnp | grep 8000

# 检查 Python 环境
/opt/mcpagent/venv/bin/python --version
```

### 2. 前端无法访问

```bash
# 检查 Nginx 状态
systemctl status nginx

# 测试 Nginx 配置
nginx -t

# 查看 Nginx 错误日志
tail -f /var/log/nginx/error.log

# 检查文件权限
ls -la /opt/mcpagent/frontend/dist/
```

### 3. API 调用失败

```bash
# 测试后端健康检查
curl http://localhost:8000/health

# 检查环境变量
cat /opt/mcpagent/.env

# 测试 MongoDB 连接
systemctl status mongod
mongo --eval "db.stats()"
```

### 4. MCP Server 连接问题

```bash
# 检查全局依赖
npm list -g @modelcontextprotocol/server-puppeteer
uvx --version

# 测试 MCP Server 配置
cat /opt/mcpagent/config.yaml

# 查看应用日志中的 MCP 相关错误
journalctl -u mcpagent | grep -i mcp
```

## 🔒 安全建议

### 1. 更改默认端口

```bash
# 修改 SSH 端口 (可选)
vim /etc/ssh/sshd_config
# Port 2222
systemctl restart sshd

# 在安全组中开放新端口，关闭 22 端口
```

### 2. 设置防火墙

```bash
# 查看防火墙状态
firewall-cmd --state

# 查看开放端口
firewall-cmd --list-all

# 限制访问来源 (可选)
firewall-cmd --permanent --add-rich-rule="rule family='ipv4' source address='your-ip' port protocol='tcp' port='22' accept"
```

### 3. 备份策略

```bash
# 创建定时备份
crontab -e

# 添加以下行 (每天凌晨2点备份)
0 2 * * * /opt/mcpagent/backup.sh

# 创建备份脚本
cat > /opt/mcpagent/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/mcpagent/backups"
mkdir -p $BACKUP_DIR

# 备份数据库
mongodump --db mcpagent --out "$BACKUP_DIR/mongo_$DATE"

# 备份配置
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" /opt/mcpagent/.env /opt/mcpagent/config.yaml

# 清理 7 天前的备份
find $BACKUP_DIR -type f -mtime +7 -delete
EOF

chmod +x /opt/mcpagent/backup.sh
```

## 📈 性能优化

### 1. 系统优化

```bash
# 增加文件描述符限制
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# 优化内核参数
echo "net.core.somaxconn = 1024" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 1024" >> /etc/sysctl.conf
sysctl -p
```

### 2. 应用优化

```bash
# 使用 Gunicorn 多进程部署 (可选)
pip install gunicorn

# 修改 systemd 服务文件
vim /etc/systemd/system/mcpagent.service

# 将 ExecStart 改为：
# ExecStart=/opt/mcpagent/venv/bin/gunicorn mcp_agent.main:app -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

systemctl daemon-reload
systemctl restart mcpagent
```

---

**部署完成后，通过 http://47.86.96.112 访问您的 MCP Agent 应用！**
