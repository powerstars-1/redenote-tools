# 部署基线

## 部署目标

本服务面向自有服务器部署。

推荐基线环境：

- Linux 服务器
- Python 3.11+
- Node.js 18+
- 使用 `uv` 或 virtualenv 管理 Python 运行环境
- 使用 Nginx 或 Caddy 作为反向代理
- 在反向代理层完成 HTTPS 终止
- 通过 systemd、PM2 或 Docker 进行进程托管

## 第一阶段运行假设

- 第一阶段允许单实例部署
- 第一阶段允许本地文件日志
- 第一阶段暂不需要分布式缓存
- 第一阶段默认使用本地 `SQLite`
- 第一阶段不需要额外安装 MySQL
- 第一阶段需要在服务目录执行 `npm install` 安装签名依赖

## 必备运维能力

- 启动健康检查
- 结构化应用日志
- 请求超时控制
- 异常退出自动拉起
- 基础访问日志保留

## 日志处理要求

- 绝不记录原始 Cookie
- 绝不在接口响应中回显 Cookie
- 对敏感请求头和请求体字段做脱敏
- 保留请求 ID 便于排障

## 反向代理要求

- 强制 HTTPS
- 设置请求体大小限制
- 配置上游超时边界
- 后续可接入 IP 白名单或统一鉴权网关

## 后续生产增强项

- Redis 或等价缓存组件
- 限流中间件
- 指标采集接口
- 告警与错误聚合
- 将重任务拆分到独立 worker

## Linux 服务器推荐目录

建议统一部署到：

```text
/srv/redenote-tools
```

建议配套目录：

```text
/srv/redenote-tools
  .venv/
  data/
  runtime/
  service/
```

## 首次部署步骤

以下步骤以 Ubuntu 22.04 / 24.04 为例。

### 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y git curl nginx python3 python3-venv python3-pip
```

安装 Node.js 20 LTS：

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### 2. 拉取代码

```bash
sudo mkdir -p /srv/redenote-tools
sudo chown -R $USER:$USER /srv/redenote-tools
git clone https://github.com/<your-account>/redenote-tools.git /srv/redenote-tools
cd /srv/redenote-tools
```

### 3. 创建 Python 虚拟环境并安装依赖

```bash
cd /srv/redenote-tools
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .[dev]
```

### 4. 安装签名所需 Node 依赖

```bash
cd /srv/redenote-tools/service
npm install
```

### 5. 写入环境变量

复制示例配置：

```bash
cd /srv/redenote-tools
cp .env.example .env
```

建议初始配置：

```env
REDNOTE_APP_ENV=prod
REDNOTE_LOG_LEVEL=INFO
REDNOTE_UPSTREAM_TIMEOUT_SECONDS=15
REDNOTE_MAX_PAGE_COUNT=10
REDNOTE_DATABASE_PATH=/srv/redenote-tools/data/app.db
REDNOTE_DEFAULT_SYNC_TARGET=openclaw_bitable
REDNOTE_API_KEYS=replace-me-public-key
REDNOTE_INTERNAL_API_KEYS=replace-me-internal-key
```

说明：

- `REDNOTE_API_KEYS` 支持配置多个值，用英文逗号分隔
- `REDNOTE_INTERNAL_API_KEYS` 用于 OpenClaw 等内部同步程序
- 如果未单独配置内部 Key，内部同步接口会回退使用公开 Key
- 对外开放前必须把示例值 `replace-me-*` 替换成真实随机值

### 6. 手动验证服务

```bash
cd /srv/redenote-tools
source .venv/bin/activate
uvicorn service.app.main:app --host 127.0.0.1 --port 8000
```

验证：

- `http://127.0.0.1:8000/healthz`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/`
- `ls -lh /srv/redenote-tools/data/app.db`

## systemd 托管示例

创建服务文件：

```bash
sudo nano /etc/systemd/system/redenote-tools.service
```

写入：

```ini
[Unit]
Description=RedNote Tools Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/srv/redenote-tools
EnvironmentFile=/srv/redenote-tools/.env
ExecStart=/srv/redenote-tools/.venv/bin/uvicorn service.app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

授权并启动：

```bash
sudo chown -R www-data:www-data /srv/redenote-tools
sudo systemctl daemon-reload
sudo systemctl enable redenote-tools
sudo systemctl start redenote-tools
sudo systemctl status redenote-tools
```

查看日志：

```bash
journalctl -u redenote-tools -f
```

## Nginx 反向代理示例

创建站点配置：

```bash
sudo nano /etc/nginx/sites-available/redenote-tools.conf
```

写入：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 10m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
        proxy_connect_timeout 30;
    }
}
```

启用站点：

```bash
sudo ln -s /etc/nginx/sites-available/redenote-tools.conf /etc/nginx/sites-enabled/redenote-tools.conf
sudo nginx -t
sudo systemctl reload nginx
```

如果域名已解析完成，建议继续接入：

- `certbot`
- 或 Caddy 自动签发 HTTPS

## 更新发布流程

服务端更新建议按以下顺序执行：

```bash
cd /srv/redenote-tools
git pull origin main
source .venv/bin/activate
pip install -e .[dev]
cd service
npm install
cd ..
sudo systemctl restart redenote-tools
sudo systemctl status redenote-tools
```

## 排障顺序

如果 Linux 上接口无法使用，优先检查：

1. `systemctl status redenote-tools`
2. `journalctl -u redenote-tools -f`
3. `curl http://127.0.0.1:8000/healthz`
4. `node -v` 与 `python3 --version`
5. `/srv/redenote-tools/service/node_modules/crypto-js` 是否存在
6. `/srv/redenote-tools/data/app.db` 是否已创建且有写权限

## 当前阶段的上线建议

- GitHub 仓库默认建议设为私有
- 先只开放给内部员工使用
- 先跑单实例，不急着上容器编排
- 等接入落库、同步队列、多维表格后，再考虑拆 worker
