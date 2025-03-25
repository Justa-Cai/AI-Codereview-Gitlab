# 前端构建阶段
FROM node:18-slim AS frontend-builder

# 设置工作目录
WORKDIR /app/frontend

# 配置镜像源参数（可选）
ARG NPM_REGISTRY
ARG YARN_REGISTRY

# 设置 Node 内存限制
ENV NODE_OPTIONS=--max_old_space_size=4096

# 创建缓存目录
RUN mkdir -p /root/.yarn-cache

# 配置 yarn
RUN yarn config set network-timeout 300000 && \
    if [ ! -z "$YARN_REGISTRY" ]; then \
      echo "Using custom registry: $YARN_REGISTRY" && \
      yarn config set registry $YARN_REGISTRY; \
    fi

# 首先只复制 package.json 和 yarn.lock
COPY ui/package*.json ./
COPY ui/yarn.lock* ./

# 安装依赖并生成 yarn.lock（添加重试机制）
RUN for i in 1 2 3; do \
      yarn install --frozen-lockfile --cache-folder /root/.yarn-cache --network-timeout 300000 && break || \
      echo "Retry attempt $i..." && \
      sleep 5; \
    done

# 复制源代码
COPY ui/ .

# 构建前端
RUN yarn build

# 后端基础镜像
FROM python:3.10-slim AS backend-builder

# 设置工作目录
WORKDIR /app/

# 设置pip镜像源（可选）
ARG PIP_INDEX_URL

# 创建pip缓存目录
RUN mkdir -p /root/.cache/pip

# 配置pip镜像源（如果指定了的话）
RUN if [ ! -z "$PIP_INDEX_URL" ]; then \
      echo "Using custom pip index: $PIP_INDEX_URL" && \
      pip config set global.index-url $PIP_INDEX_URL; \
    fi

# 首先只复制依赖文件
COPY requirements.txt .

# 安装依赖到临时目录
RUN pip install --no-cache-dir -r requirements.txt --target /install \
    --timeout 1000 \
    --retries 3 \
    --default-timeout 1000 \
    --no-deps \
    --verbose \
    && pip install --no-cache-dir -r requirements.txt --target /install \
    --timeout 1000 \
    --retries 3 \
    --default-timeout 1000 \
    --verbose

# 基础运行时镜像
FROM python:3.10-slim AS base

# 设置工作目录
WORKDIR /app/

# 从构建阶段复制已安装的依赖
COPY --from=backend-builder /install /usr/local/lib/python3.10/site-packages/

# 复制后端代码
COPY biz ./biz
COPY api.py ./api.py
COPY ui.py ./ui.py
COPY main.py ./main.py
COPY conf/prompt_templates.yml ./conf/prompt_templates.yml
COPY conf/agents ./conf/

# 创建必要的目录
RUN mkdir -p /app/static /app/log /app/data

# 设置环境变量
ENV PYTHONPATH=/app/
ENV PYTHONUNBUFFERED=1

# 主应用镜像
FROM base AS app

# 安装 supervisor
RUN pip install supervisor

# 复制 supervisor 配置
COPY conf/supervisord.app.conf /etc/supervisor/supervisord.conf

# 从构建阶段复制前端文件
COPY --from=frontend-builder /app/frontend/dist /app/static

# 暴露端口
EXPOSE 5001

# 使用supervisord管理进程
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]

# Worker 镜像
FROM base AS worker

# 安装 supervisor
RUN pip install supervisor

# 复制 worker 的 supervisor 配置
COPY conf/supervisord.worker.conf /etc/supervisor/supervisord.conf

# Worker 启动命令
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]