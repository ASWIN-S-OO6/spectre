FROM kalilinux/kali-rolling:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV HOME=/root

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    nmap \
    dirb \
    gobuster \
    nikto \
    hydra \
    sqlmap \
    whatweb \
    wfuzz \
    curl \
    wget \
    git \
    net-tools \
    iproute2 \
    iputils-ping \
    dnsutils \
    whois \
    nodejs \
    npm \
    tor \
    proxychains4 \
    torsocks \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/run/tor /var/log/tor /var/lib/tor \
    && chown -R debian-tor:debian-tor /var/run/tor /var/log/tor /var/lib/tor

WORKDIR /opt/spectre

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY app/ ./app/

# Build React Frontend
RUN cd app/frontend && npm install && npm run build

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

RUN mkdir -p reports/tor_logs reports/sessions wordlists

EXPOSE 7777

ENTRYPOINT ["./entrypoint.sh"]