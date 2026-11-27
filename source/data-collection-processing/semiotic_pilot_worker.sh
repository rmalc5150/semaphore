#!/bin/bash
set -euo pipefail
cd "$HOME/semiotic-run"
handoff=$1
output="$handoff/${2:-output}"
mkdir -p "$output"
export PYTHONHOME="$PWD/runtime"
export PYTHONPATH="$PWD/hybrid/packages:$PWD/hybrid/nlp:$PWD/runtime/packages"
export HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1
server="$PWD/models/llama-b12248/llama-server"
export LD_LIBRARY_PATH="$(dirname "$server"):$PWD/runtime/lib64"
alias=qwen3.5-2b-ud-q4_k_xl-623132b
port=18081
pids=()
cleanup() {
    local code=$? pid
    for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
    for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || true; done
    printf '%s\n' "$code" > "$output/exit-status"
}
trap cleanup EXIT
start_model() {
    local weights=$1 model=$2 endpoint=$3 slots=$4 _
    "$server" --model "$weights" --alias "$model" --host 127.0.0.1 \
        --port "$endpoint" --threads 4 --parallel "$slots" --ctx-size 6144 --reasoning off > "$output/$model-server.log" 2>&1 &
    local pid=$!
    pids+=("$pid")
    for _ in $(seq 1 45); do
        if curl --silent --fail "http://127.0.0.1:$endpoint/health" >/dev/null; then return; fi
        kill -0 "$pid"
        sleep 1
    done
    curl --silent --fail "http://127.0.0.1:$endpoint/health" >/dev/null
}
start_model models/Qwen3.5-2B-UD-Q4_K_XL.gguf "$alias" "$port" 3
thesis_args=()
thesis_weights=models/Ministral-3-3B-Instruct-2512-Q4_K_M.gguf
if [[ -f "$thesis_weights" ]]; then
    thesis_alias=ministral-3-3b-instruct-2512-q4_k_m
    thesis_port=18082
    start_model "$thesis_weights" "$thesis_alias" "$thesis_port" 1
    thesis_args=(--thesis-model "$thesis_alias" --thesis-port "$thesis_port")
fi
runtime/bin/python3.12 -uB pilot-v1/app/semiotic_pilot.py work \
    --handoff "$handoff/handoff.json" --archive "$handoff/archive" --assets hybrid/assets \
    --output "$output" --model "$alias" --port "$port" "${thesis_args[@]}"
