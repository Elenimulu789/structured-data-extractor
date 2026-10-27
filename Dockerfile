FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir uv==0.13.4
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY src ./src
COPY samples ./samples
COPY tests ./tests
COPY .streamlit ./.streamlit
RUN useradd --create-home appuser && mkdir /app/dlq && chown -R appuser:appuser /app
USER appuser
ENV PATH="/app/.venv/bin:$PATH" DLQ_DIR=/app/dlq
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "src/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
