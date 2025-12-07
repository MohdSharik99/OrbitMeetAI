#!/bin/bash

# Run backend from project root
cd "$(dirname "$0")"
uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000

