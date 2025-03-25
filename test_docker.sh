DOCKER_IMAGE_NAME="ai-codereview"
DOCKER_IMAGE_TAG="latest"
PORT=6001  # 添加端口变量，方便修改

# 确保必要的目录存在
mkdir -p log data

# 停止可能已经在运行的容器
docker stop $(docker ps -q --filter publish=$PORT) 2>/dev/null || true

docker run -d \
  -p $PORT:5001 \
  -v $(pwd)/conf:/app/conf \
  -v $(pwd)/log:/app/log \
  -v $(pwd)/data:/app/data \
  $DOCKER_IMAGE_NAME:$DOCKER_IMAGE_TAG 