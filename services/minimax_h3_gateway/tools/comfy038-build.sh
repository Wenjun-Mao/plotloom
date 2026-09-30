#!/usr/bin/env bash
# The only supported build entrypoint for this exact qualification candidate.
set -euo pipefail

readonly base_tag=spark-comfyui:keep-h3-v035-20260930
readonly expected_base=sha256:d45ca7983d4eda39cdd4df3bd03921b28754b2c15ce17f906032ef4dafd1cabc
readonly candidate_tag=spark-comfyui:h3-v038-candidate-20260930
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly script_dir

actual_base="$(docker image inspect --format '{{.Id}}' "$base_tag")"
if [[ "$actual_base" != "$expected_base" ]]; then
  printf 'Refusing build: baseline image identity differs from %s\n' "$expected_base" >&2
  exit 1
fi
docker build --progress=plain --build-arg "BASE_IMAGE=$actual_base" \
  --file "$script_dir/comfy038.Dockerfile" --tag "$candidate_tag" "$script_dir"
