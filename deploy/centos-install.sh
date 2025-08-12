#!/bin/bash

# MCP Agent CentOS 7 专用部署脚本
# 适用于阿里云 ECS CentOS 7.7 环境

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 配置变量
PROJECT_DIR="/opt/mcpagent"
SERVICE_USER="mcpagent"
DOMAIN="${1:-47.86.96.112}"

# 安装 EPEL 源
install_epel() {
    log_info "安装 EPEL 源..."
    yum install -y epel-release
}

# 安装 Python 3.13.5 (从源码编译)
install_python() {
    log_info "安装 Python 3.13.5..."
    
    # 安装编译依赖
    yum groupinstall -y "Development Tools"
    yum install -y openssl-devel bzip2-devel libffi-devel zlib-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel expat-devel
    
    # 下载并编译 Python 3.13.5
    cd /tmp
    wget https://www.python.org/ftp/python/3.13.5/Python-3.13.5.tgz
    tar xzf Python-3.13.5.tgz
    cd Python-3.13.5
    
    # 配置编译选项
    ./configure --enable-optimizations --prefix=/usr/local
    
    # 编译安装 (使用多核加速)
    make -j$(nproc)
    make altinstall
    
    # 创建软链接
    ln -sf /usr/local/bin/python3.13 /usr/bin/python3
    ln -sf /usr/local/bin/pip3.13 /usr/bin/pip3
    
    # 验证安装
    python3 --version
    
    # 升级 pip
    python3 -m pip install --upgrade pip
    
    # 清理编译文件
    cd /
    rm -rf /tmp/Python-3.13.5*
}

# 安装 Node.js 16
install_nodejs() {
    log_info "安装 Node.js 16..."
    curl -fsSL https://rpm.nodesource.com/setup_16.x | bash -
    yum install -y nodejs
    
    # 配置 npm 镜像源 (加速)
    npm config set registry https://registry.npmmirror.com/
}

# 安装 MongoDB 4.4
install_mongodb() {
    log_info "安装 MongoDB 4.4..."
    
    # 添加 MongoDB YUM 源
    cat > /etc/yum.repos.d/mongodb-org-4.4.repo << EOF
[mongodb-org-4.4]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/7/mongodb-org/4.4/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-4.4.asc
EOF

    yum install -y mongodb-org
    
    # 启动并设置开机自启
    systemctl start mongod
    systemctl enable mongod
    
    # 等待 MongoDB 启动
    sleep 5
    
    log_info "MongoDB 安装完成"
}

# 安装 Nginx
install_nginx() {
    log_info "安装 Nginx..."
    yum install -y nginx
    
    # 启动并设置开机自启
    systemctl start nginx
    systemctl enable nginx
}

# 创建用户和目录
setup_user() {
    log_info "创建用户和目录..."
    
    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -m -s /bin/bash $SERVICE_USER
        log_info "创建用户: $SERVICE_USER"
    fi
    
    mkdir -p $PROJECT_DIR
    chown $SERVICE_USER:$SERVICE_USER $PROJECT_DIR
}

# 部署后端
deploy_backend() {
    log_info "部署后端应用..."
    
    sudo -u $SERVICE_USER bash << EOF
cd $PROJECT_DIR

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装 Python 依赖
pip install -r requirements.txt

# 安装全局 MCP Server 依赖
EOF

    # 安装全局依赖 (需要 sudo)
    npm install -g @modelcontextprotocol/server-puppeteer
    pip3 install uvx
}

# 构建前端
build_frontend() {
    log_info "构建前端应用..."
    
    sudo -u $SERVICE_USER bash << EOF
cd $PROJECT_DIR/frontend

# 安装依赖
npm install

# 构建生产版本
npm run build
EOF
}

# 配置环境变量
setup_environment() {
    log_info "配置环境变量..."
    
    if [ ! -f "$PROJECT_DIR/.env" ]; then
        sudo -u $SERVICE_USER tee $PROJECT_DIR/.env << EOF
# OpenAI 配置
BASE_URL=https://ark.cn-beijing.volces.com/api/v3
API_KEY=94aea83f-d09c-4da8-be15-67441e02ec0c
MODEL=doubao-1-5-pro-32k-250115

# 数据库配置
MONGO_URI=mongodb://localhost:27017/mcpagent

# 服务配置
HOST=0.0.0.0
PORT=8000
EOF
        
        chmod 600 $PROJECT_DIR/.env
        log_warn "请编辑 $PROJECT_DIR/.env 文件，设置正确的 API_KEY"
    fi
}

# 配置 Nginx (针对阿里云 ECS)
setup_nginx() {
    log_info "配置 Nginx..."
    
    # 备份原配置
    cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak
    
    # 创建新配置
    tee /etc/nginx/nginx.conf << EOF
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent" "\$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 20M;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;

    server {
        listen 80;
        server_name $DOMAIN;

        # 前端静态文件
        location / {
            root $PROJECT_DIR/frontend/dist;
            try_files \$uri \$uri/ /index.html;
            
            # 静态资源缓存
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }
        
        # API 代理
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
            
            # 超时设置
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 300s;
        }
        
        # 直接代理后端路由
        location ~ ^/(sessions|chat|servers|health) {
            proxy_pass http://127.0.0.1:8000;
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
        
        # 错误页面
        error_page 500 502 503 504 /50x.html;
        location = /50x.html {
            root /usr/share/nginx/html;
        }
    }
}
EOF

    # 测试配置
    nginx -t
    
    # 重启 Nginx
    systemctl restart nginx
    systemctl reload nginx
}

# 配置系统服务
setup_systemd() {
    log_info "配置系统服务..."
    
    tee /etc/systemd/system/mcpagent.service << EOF
[Unit]
Description=MCP Agent Backend Service
After=network.target mongod.service
Wants=mongod.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/venv/bin/uvicorn mcp_agent.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# 安全设置
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable mcpagent
}

# 配置防火墙
setup_firewall() {
    log_info "配置防火墙..."
    
    # CentOS 7 默认使用 firewalld
    systemctl start firewalld
    systemctl enable firewalld
    
    # 开放端口
    firewall-cmd --permanent --add-service=ssh
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --permanent --add-port=8000/tcp
    firewall-cmd --reload
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    systemctl start mcpagent
    
    # 等待服务启动
    sleep 10
    
    # 检查服务状态
    if systemctl is-active --quiet mcpagent; then
        log_info "MCP Agent 服务启动成功"
    else
        log_error "MCP Agent 服务启动失败"
        journalctl -u mcpagent --no-pager -l
        exit 1
    fi
}

# 创建管理脚本
create_management_scripts() {
    log_info "创建管理脚本..."
    
    # 状态检查脚本
    tee $PROJECT_DIR/status.sh << 'EOF'
#!/bin/bash
echo "=== MCP Agent 系统状态 ==="
echo "后端服务状态:"
systemctl status mcpagent --no-pager -l

echo -e "\n=== 端口监听状态 ==="
netstat -tlnp | grep -E ':8000|:80|:443' || echo "未找到监听端口"

echo -e "\n=== 内存使用情况 ==="
free -h

echo -e "\n=== 磁盘使用情况 ==="
df -h /opt/mcpagent

echo -e "\n=== MongoDB 状态 ==="
systemctl status mongod --no-pager -l

echo -e "\n=== Nginx 状态 ==="
systemctl status nginx --no-pager -l

echo -e "\n=== 最新日志 ==="
journalctl -u mcpagent --no-pager -l -n 10
EOF

    chmod +x $PROJECT_DIR/status.sh
    chown $SERVICE_USER:$SERVICE_USER $PROJECT_DIR/status.sh
}

# 显示部署结果
show_result() {
    log_info "部署完成！"
    echo
    echo "=================================="
    echo "MCP Agent 阿里云 ECS 部署信息"
    echo "=================================="
    echo "公网访问: http://$DOMAIN"
    echo "私网访问: http://172.17.193.201"
    echo "后端API:  http://$DOMAIN:8000"
    echo "项目目录: $PROJECT_DIR"
    echo "服务用户: $SERVICE_USER"
    echo
    echo "管理命令:"
    echo "  systemctl status mcpagent"
    echo "  systemctl restart mcpagent"
    echo "  journalctl -u mcpagent -f"
    echo "  $PROJECT_DIR/status.sh"
    echo
    echo "重要配置:"
    echo "1. 编辑 $PROJECT_DIR/.env 设置 OpenAI API Key"
    echo "2. 阿里云安全组已配置: 22, 80, 443, 8000"
    echo "3. MongoDB 运行在本地 27017 端口"
    echo "=================================="
}

# 主函数
main() {
    log_info "开始在阿里云 ECS CentOS 7 上部署 MCP Agent..."
    
    # 检查是否为 root 用户
    if [[ $EUID -ne 0 ]]; then
        log_error "请使用 root 用户运行此脚本"
        exit 1
    fi
    
    # 检查当前目录
    if [ ! -f "requirements.txt" ] || [ ! -d "mcp_agent" ] || [ ! -d "frontend" ]; then
        log_error "请在项目根目录运行此脚本"
        exit 1
    fi
    
    install_epel
    install_python
    install_nodejs
    install_mongodb
    install_nginx
    setup_user
    
    # 复制项目文件
    log_info "复制项目文件..."
    cp -r . $PROJECT_DIR/
    chown -R $SERVICE_USER:$SERVICE_USER $PROJECT_DIR
    
    deploy_backend
    build_frontend
    setup_environment
    setup_nginx
    setup_systemd
    setup_firewall
    start_services
    create_management_scripts
    
    show_result
}

# 错误处理
trap 'log_error "脚本执行失败，请检查错误信息"; exit 1' ERR

# 执行主函数
main "$@"
