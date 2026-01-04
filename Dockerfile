# 使用 Python 3.10 作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY customer_churn_predict/ ./customer_churn_predict/
COPY data/ ./data/
COPY reports/ ./reports/

# 创建必要的目录
RUN mkdir -p data/raw data/processed data/models reports

# 设置环境变量
ENV FLASK_APP=customer_churn_predict/app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]

