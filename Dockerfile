# 前端构建阶段
FROM node:18-slim AS frontend-builder

# 设置工作目录
WORKDIR /app/frontend

# 配置yarn使用淘宝镜像源
ENV YARN_REGISTRY=https://registry.npmmirror.com
ENV NODE_OPTIONS=--max_old_space_size=4096

# 复制 package.json
COPY ui/package*.json ./

# 安装依赖并生成 yarn.lock
RUN yarn install --registry=https://registry.npmmirror.com

# 复制源代码
COPY ui/ .

# 构建前端
RUN yarn build

# 后端基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app/

# 设置pip使用国内镜像源
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip config set global.index-url ${PIP_INDEX_URL}

# 安装 supervisor
RUN pip install supervisor

# 复制后端代码和依赖文件
COPY requirements.txt .
COPY biz ./biz
COPY api.py ./api.py
COPY ui.py ./ui.py
COPY main.py ./main.py
COPY conf/prompt_templates.yml ./conf/prompt_templates.yml
COPY conf/agents ./conf/
COPY conf/supervisord.app.conf /etc/supervisor/supervisord.conf

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要的目录
RUN mkdir -p /app/static /app/log /app/data

# 从构建阶段复制前端文件
COPY --from=frontend-builder /app/frontend/dist /app/static

# 设置环境变量
ENV PYTHONPATH=/app/
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 5001

# 使用supervisord管理进程
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]