#!/bin/bash

MODEL=${GEMMA_MODEL_PATH:-$HOME/models/gemma-4-4b-it-Q4_K_M.gguf}
PORT=${JETSON_GEMMA_PORT:-8080}
CTX=${GEMMA_CTX_SIZE:-8192}
GPU_LAYERS=${GEMMA_GPU_LAYERS:-99}

echo "Starting Gemma server on port $PORT..."
"$HOME/llama.cpp/build/bin/llama-server" \
  -m "$MODEL" \
  --port "$PORT" \
  -ngl "$GPU_LAYERS" \
  --ctx-size "$CTX" \
  --host 0.0.0.0 \
  --threads 4 \
  --parallel 1 \
  --no-mmap
