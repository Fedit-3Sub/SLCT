FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/app

# 내장 CPU LLM(코파일럿) 포함 여부. 0 이면 규칙 기반 생성기만 쓰는 가벼운 이미지가 된다.
ARG WITH_LOCAL_LLM=1
ARG LOCAL_LLM_MODEL_URL=https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf

# 모델 파일은 크고 바뀌지 않으므로 소스보다 먼저 받아 레이어 캐시를 재사용한다.
RUN mkdir -p /opt/app/models /opt/app/data \
    && if [ "$WITH_LOCAL_LLM" = "1" ]; then \
         python -c "import urllib.request,sys; urllib.request.urlretrieve(sys.argv[1], '/opt/app/models/' + sys.argv[1].rsplit('/', 1)[-1])" "$LOCAL_LLM_MODEL_URL"; \
       fi

COPY requirements.txt requirements-local-llm.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn \
    && if [ "$WITH_LOCAL_LLM" = "1" ]; then \
         pip install --no-cache-dir -r requirements-local-llm.txt \
           --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu; \
       fi

COPY . .

ENV DJANGO_SETTINGS_MODULE=core.settings \
    DJANGO_ALLOWED_HOSTS=* \
    DJANGO_DEBUG=0 \
    DJANGO_DB_PATH=/opt/app/data/db.sqlite3 \
    LOCAL_LLM_ENABLED=${WITH_LOCAL_LLM}

RUN python manage.py collectstatic --noinput

# DB 는 볼륨으로 붙여 컨테이너를 다시 만들어도 남도록 한다.
VOLUME ["/opt/app/data"]
EXPOSE 1337

# 로직 실행은 요청을 받은 워커 안의 스레드에서 돌므로, 긴 실행 중에도 워커가
# 다른 요청을 받도록 스레드 워커를 쓴다.
CMD sh -c "python manage.py migrate --noinput && python manage.py load_samples && gunicorn --workers 2 --threads 4 --timeout 300 --bind 0.0.0.0:1337 core.wsgi:application"
