FROM python:3.14-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends openssl ca-certificates && rm -rf /var/lib/apt/lists/*
COPY lab_server.py /lab/lab_server.py
COPY inputs.py /lab/inputs.py
RUN mkdir -p /lab/tls && openssl req -x509 -newkey rsa:2048 -nodes -keyout /lab/tls/key.pem -out /lab/tls/cert.pem -days 30 -subj /CN=lab -addext 'subjectAltName=DNS:lab,DNS:portal.lab.test,IP:172.30.42.10' && chown -R 65534:65534 /lab/tls
USER 65534:65534
WORKDIR /lab
ENTRYPOINT ["python", "/lab/lab_server.py"]
