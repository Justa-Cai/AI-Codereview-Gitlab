# 前端构建阶段
FROM node:18-slim AS frontend-builder

# 设置工作目录
WORKDIR /app/frontend

# 配置是否使用国内镜像源
ARG USE_CHINA_MIRROR=false
ARG NPM_REGISTRY=https://registry.npmjs.org
ARG YARN_REGISTRY=https://registry.yarnpkg.com
ENV NPM_CONFIG_REGISTRY=${NPM_REGISTRY}
ENV YARN_REGISTRY=${YARN_REGISTRY}
ENV NODE_OPTIONS=--max_old_space_size=4096

# 创建缓存目录
RUN mkdir -p /root/.yarn-cache

# 首先只复制 package.json 和 yarn.lock
COPY ui/package*.json ./
COPY ui/yarn.lock* ./

# 安装依赖并生成 yarn.lock
RUN yarn install --frozen-lockfile --cache-folder /root/.yarn-cache --registry=${YARN_REGISTRY}

# 复制源代码
COPY ui/ .

# 构建前端
RUN yarn build

# 后端基础镜像
FROM python:3.10-slim AS backend-builder

# 设置工作目录
WORKDIR /app/

# 设置pip使用国内镜像源
ARG USE_CHINA_MIRROR=false
ARG PIP_INDEX_URL=https://pypi.org/simple

# 创建pip缓存目录
RUN mkdir -p /root/.cache/pip

# 配置pip镜像源
RUN pip config set global.index-url ${PIP_INDEX_URL}

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

# 设置pip使用国内镜像源
ARG USE_CHINA_MIRROR=false
ARG PIP_INDEX_URL=https://pypi.org/simple

# 配置pip镜像源
RUN pip config set global.index-url ${PIP_INDEX_URL}

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