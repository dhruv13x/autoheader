FROM python:3.12-slim

# Install git as it might be needed for gitignore or git hooks checks
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the source code
COPY . /app

# Install the package
RUN pip install --no-cache-dir .

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]
