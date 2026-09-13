FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.141.1 \
    pillow==11.3.0 \
    pydantic==2.13.5 \
    python-multipart==0.0.32 \
    requests==2.34.2 \
    uvicorn[standard]==0.52.4

COPY src/plotloom/h3_gateway /app/src/plotloom/h3_gateway

ENV PYTHONPATH=/app/src
CMD ["python", "-m", "plotloom.h3_gateway"]
