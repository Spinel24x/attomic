FROM python:3.12-alpine

WORKDIR /app

COPY socks5.py /app/socks5.py

RUN chmod +x /app/socks5.py

ENV PYTHONUNBUFFERED=1

CMD ["python3", "/app/socks5.py"]
