#!/bin/bash

# 输出颜色设置
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的信息
print_info() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

print_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        print_error "$1 命令未找到，请先安装"
        exit 1
    fi
}

# 检查必要的命令
check_command docker

# 检查Docker版本
DOCKER_VERSION=$(docker --version)
print_info "使用Docker版本: $DOCKER_VERSION"

# 设置变量
DOCKER_IMAGE_NAME="ai-codereview"
DOCKER_IMAGE_TAG="latest"

# 检查必要文件
if [ ! -d "ui" ]; then
    print_error "前端目录 ui 不存在"
    exit 1
fi

if [ ! -f "ui/package.json" ]; then
    print_error "前端 package.json 不存在"
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    print_error "后端 requirements.txt 不存在"
    exit 1
fi

# 构建Docker镜像
print_info "开始构建Docker镜像..."
print_info "注意：前端构建将在Docker容器中进行..."

# 使用国内镜像源构建
print_info "使用国内镜像源构建"
build_args="--build-arg NPM_REGISTRY=https://registry.npmmirror.com --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple --network host --no-cache"

# 构建Docker镜像
docker build $build_args -t $DOCKER_IMAGE_NAME:$DOCKER_IMAGE_TAG .

# 检查构建是否成功
if [ $? -eq 0 ]; then
    print_info "Docker镜像构建成功！"
    print_info "镜像名称: $DOCKER_IMAGE_NAME:$DOCKER_IMAGE_TAG"
else
    print_error "Docker镜像构建失败"
    print_error "请检查错误信息并确保所有必要文件都存在且权限正确"
    exit 1
fi

print_info "构建完成！"
print_info "你可以使用以下命令运行容器："
echo "docker run -d -p 5001:5001 $DOCKER_IMAGE_NAME:$DOCKER_IMAGE_TAG" 