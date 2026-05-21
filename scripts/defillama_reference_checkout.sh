#!/usr/bin/env bash
set -euo pipefail

root="${DEFILLAMA_REFERENCE_ROOT:-/private/tmp/defillama-reference}"
mkdir -p "$root"

clone_sparse() {
  local name="$1"
  local url="$2"
  shift 2
  local dir="$root/$name"

  if [ ! -d "$dir/.git" ]; then
    git clone --depth 1 --filter=blob:none --sparse "$url" "$dir"
  else
    git -C "$dir" fetch --depth 1 origin main
    git -C "$dir" reset --hard origin/main
  fi

  git -C "$dir" sparse-checkout init --no-cone
  git -C "$dir" sparse-checkout set "$@"
  printf "%s %s\n" "$name" "$(git -C "$dir" rev-parse HEAD)"
}

clone_sparse \
  DefiLlama-Adapters \
  https://github.com/DefiLlama/DefiLlama-Adapters.git \
  /skills/adapter-author/ \
  /projects/helper/coreAssets.json \
  /projects/helper/abis/aave.json \
  /projects/helper/abis/uniswap.js \
  /projects/helper/abis/uniV3.json \
  /projects/helper/abis/balancer.json \
  /projects/helper/abis/morpho.json \
  /projects/aave-v3/ \
  /projects/aave-v4/ \
  /projects/morpho-blue/ \
  /projects/uniswap-v2/ \
  /projects/uniswap-v4/ \
  /projects/uniswap/v3/ \
  /projects/aerodrome-CL/ \
  /projects/camelot-v2/ \
  /projects/curve/

clone_sparse \
  dimension-adapters \
  https://github.com/DefiLlama/dimension-adapters.git \
  /dexs/aerodrome/ \
  /dexs/aerodrome-slipstream/ \
  /dexs/uniswap-v2.ts \
  /dexs/uniswap-v3.ts \
  /dexs/uniswap-v4.ts \
  /dexs/curve/ \
  /dexs/balancer-v2.ts \
  /dexs/balancer-v3/ \
  /dexs/camelot-v3/ \
  /dexs/pancakeswap-v2.ts \
  /dexs/pancakeswap-v3.ts \
  /dexs/sushiswap-v3.ts \
  /dexs/swapbased-v2.ts \
  /dexs/swapbased-v3.ts \
  /fees/aave-v3.ts \
  /fees/aave-v4.ts \
  /fees/curve.ts \
  /fees/uniswap-lab.ts \
  /fees/velodrome/

clone_sparse \
  chainlist \
  https://github.com/DefiLlama/chainlist.git \
  /constants/chainIds.js \
  /constants/extraRpcs.js \
  /package.json

clone_sparse \
  defillama-app \
  https://github.com/DefiLlama/defillama-app.git \
  /src/components/BuyOnLlamaswap.tsx \
  /src/containers/DimensionAdapters/ \
  /src/containers/LlamaAI/ \
  /src/containers/ProDashboard/components/datasets/DexsDataset/ \
  /src/containers/ProDashboard/components/datasets/YieldsDataset/ \
  /src/containers/ProtocolOverview/ \
  /src/api/ \
  /docs/adr/0001-dataset-cache-manifest-and-runtime-adapters.md \
  /LICENSE \
  /package.json
