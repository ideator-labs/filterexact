#!/usr/bin/env bash
# Usage: bash demo.sh [--break]
# --break makes the reference store compare as float64, the bug most stores ship.
set -uo pipefail
cd "$(dirname "$0")"
export FE_OUT="$PWD/results" FE_BREAK=0
[[ "${1:-}" == "--break" ]] && FE_BREAK=1
rm -rf results && mkdir -p results .cache

QDRANT_VERSION=1.20.0
QDRANT_SHA=b03a64616a1f41ddab78b480a318466541765f19835318113b1821cbea8df52c
QDRANT_BIN=.cache/qdrant-$QDRANT_VERSION/qdrant
if [[ ! -x $QDRANT_BIN ]]; then
  mkdir -p "$(dirname "$QDRANT_BIN")"
  curl -fsSL -o .cache/qdrant.tgz \
    "https://github.com/qdrant/qdrant/releases/download/v$QDRANT_VERSION/qdrant-x86_64-unknown-linux-musl.tar.gz"
  echo "$QDRANT_SHA  .cache/qdrant.tgz" | sha256sum -c --quiet || exit 1
  tar xzf .cache/qdrant.tgz -C "$(dirname "$QDRANT_BIN")"
fi

PORT=${QDRANT_PORT:-16333}
QDRANT_STORAGE="$(mktemp -d)"
QDRANT__STORAGE__STORAGE_PATH="$QDRANT_STORAGE" QDRANT__SERVICE__HTTP_PORT=$PORT \
  QDRANT__SERVICE__GRPC_PORT=$((PORT + 1)) QDRANT__TELEMETRY_DISABLED=true \
  "$QDRANT_BIN" > results/qdrant-server.log 2>&1 &
QDRANT_PID=$!
trap 'kill $QDRANT_PID 2>/dev/null; rm -rf "$QDRANT_STORAGE"' EXIT
for _ in $(seq 60); do curl -fs "localhost:$PORT/" >/dev/null && break; sleep 0.5; done

py() { uv run --quiet --no-project --python 3.12 "$@"; }
cd adapters
echo "running the same 15 filters against each store"
py python reference.py
py --with langgraph-checkpoint-sqlite==3.1.3 python langgraph_sqlite.py
py --with chromadb==1.5.9 python chroma_store.py 2>/dev/null
py --with qdrant-client==1.20.0 python qdrant_store.py local
py --with qdrant-client==1.20.0 python qdrant_store.py server-no-index "http://localhost:$PORT"
py --with qdrant-client==1.20.0 python qdrant_store.py server-index "http://localhost:$PORT"
py --with qdrant-client==1.20.0 python qdrant_store.py server-rest "http://localhost:$PORT"
py --with lancedb==0.41.0 --with pylance python lancedb_store.py
py --with pymilvus==3.0.2 --with milvus-lite==3.2.2 python milvus_store.py 2>/dev/null
cd ..
echo
python3 check.py
