FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN apt-get update && apt-get install -y curl nodejs npm && rm -rf /var/lib/apt/lists/*
RUN pip install -r requirements.txt && npm install -g newman
CMD ["bash", "run_all_tests.sh"]
