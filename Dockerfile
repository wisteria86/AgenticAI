# Sandbox environment for code execution
FROM python:3.10-slim

# Create a non-root user for extra security
RUN useradd -m sandboxuser
WORKDIR /app

# Install basic libraries for the sandbox
RUN pip install --no-cache-dir fpdf2

# The agent's generated code will be run as this user
USER sandboxuser
