#!/bin/sh
# Build once; test each deployment's locked dependency closure in an isolated venv.
set -eu
service_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
smoke_root=$(mktemp -d "${TMPDIR:-/tmp}/plotloom-service-install.XXXXXX")
printf 'Retained artifact smoke workspace: %s\n' "$smoke_root"
uv build --project "$service_root" --wheel --out-dir "$smoke_root/dist"
set -- "$smoke_root"/dist/*.whl
test "$#" = 1
wheel=$1
for role in dashboard gateway; do
    if [ "$role" = gateway ]; then set -- --extra gateway; else set --; fi
    uv export --project "$service_root" --locked --no-dev --no-emit-project "$@" \
        --output-file "$smoke_root/$role-requirements.txt" >/dev/null
    uv venv --python 3.12 "$smoke_root/$role"
    interpreter="$smoke_root/$role/bin/python"
    uv pip sync --python "$interpreter" "$smoke_root/$role-requirements.txt"
    uv pip install --python "$interpreter" --no-deps "$wheel"
    (cd "$smoke_root" && PATH="$smoke_root/$role/bin:$PATH" \
        "$interpreter" -I "$service_root/tools/packaging/smoke.py" "$role")
done
