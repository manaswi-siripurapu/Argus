#!/bin/bash
set -e

echo "=== SARGuard Jetson Setup ==="

sudo apt-get update
sudo apt-get install -y cmake git python3-pip libopenblas-dev

if [ ! -d "$HOME/llama.cpp" ]; then
  git clone https://github.com/ggerganov/llama.cpp "$HOME/llama.cpp"
fi

cd "$HOME/llama.cpp"
cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=87
cmake --build build --config Release -j4

pip3 install huggingface-hub --break-system-packages
mkdir -p "$HOME/models"

huggingface-cli download google/gemma-4-4b-it-GGUF \
  gemma-4-4b-it-Q4_K_M.gguf \
  --local-dir "$HOME/models"

echo "Model downloaded to $HOME/models/gemma-4-4b-it-Q4_K_M.gguf"
echo "Run jetson/start_gemma.sh to start the server."
