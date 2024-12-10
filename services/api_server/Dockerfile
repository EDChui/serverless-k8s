FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install dependencies for both Python and Go
RUN apt-get update && apt-get install -y \
    git \
    make \
    wget \
    gcc \
    libc6-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Go
ENV GO_VERSION=1.21.0
RUN wget https://golang.org/dl/go${GO_VERSION}.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz && \
    rm go${GO_VERSION}.linux-amd64.tar.gz

# Add Go to PATH
ENV PATH="/usr/local/go/bin:$PATH"

# Clone and build Auger
RUN git clone https://github.com/etcd-io/auger && \
    cd auger && \
    make build

# Copy Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Expose application port
EXPOSE 8080

# Start Python application
CMD ["python", "-u", "api_server.py"]
