#! /usr/bin/env bash
# Start the local Orchidarium stack.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

./scripts/generate-test-self-signed-certs.sh

docker compose up -d --build "$@"
