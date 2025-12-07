#!/bin/bash

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install base dependencies first
pip install wheel setuptools

# Install FastAPI and its dependencies
pip install "fastapi>=0.104.1" "uvicorn[standard]>=0.24.0" "starlette>=0.27.0" "pydantic>=2.4.2"

# Install other dependencies
pip install "gradio>=4.12.0" "python-dotenv>=1.0.0" "groq>=0.4.2" "google-search-results>=2.4.2" "python-pptx>=0.6.21"

# Install additional required packages
pip install "typing-extensions>=4.8.0" "anyio>=3.7.1" "click>=8.1.7" "httpx>=0.25.0" "python-multipart>=0.0.6"

echo "Installation completed!" 