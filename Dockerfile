FROM python:3.11-slim

LABEL org.opencontainers.image.title="Zotero PDF Processor"
LABEL org.opencontainers.image.description="A tool for processing PDF attachments in Zotero, for usage with other systems."
LABEL org.opencontainers.image.authors="wangyunze16@gmail.com"
LABEL org.opencontainers.image.url="https://github.com/Firefox2100/zotero-pdf-processor"
LABEL org.opencontainers.image.source="https://github.com/Firefox2100/zotero-pdf-processor"
LABEL org.opencontainers.image.vendor="uk.co.firefox2100"
LABEL org.opencontainers.image.licenses="GPL-3.0-or-later"

ENV PYTHONUNBUFFERED=1
ENV ZP_ENV_FILE="/app/.env"
ENV ZP_DATA_DIR="/app/data"

RUN apt-get update && apt-get install -y --no-install-recommends bash && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --system appgroup && \
    useradd --system --no-create-home --gid appgroup appuser

WORKDIR /app
COPY ./src/zotero_pdf_processor /app/src/zotero_pdf_processor
COPY ./pyproject.toml /app/pyproject.toml
COPY ./example.env /app/.env
COPY ./LICENSE /app/LICENSE
COPY ./README.md /app/README.md

RUN pip install --upgrade pip && \
    pip install . && \
    chown -R appuser:appgroup /app

USER appuser

VOLUME ["/app/data"]

ENTRYPOINT ["zotero-pdf-processor"]
