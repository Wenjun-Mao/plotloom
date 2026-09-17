# CI history checkout repair

## Root cause

GitHub Actions run `35224027415` checked out with the `actions/checkout`
default depth of one. The retained-runtime coverage inventory deliberately
derives its baseline from commits `e658057` and `f908c51`, so its guarded
`git diff --name-status e658057 f908c51 -- tests` could not resolve those
objects in that shallow checkout. The inventory test consequently failed even
though the current checkout contains the required history locally.

## Repair and verification

CI now requests full repository history at checkout. This belongs at the
workflow boundary because the inventory's fixed historical comparison is its
intentional contract; changing the test, inventory, or its historical refs
would weaken that coverage rather than make the required objects available.

Focused local evidence on `b562203` before this workflow-only repair:

```sh
git cat-file -e e658057^{commit}
git cat-file -e f908c51^{commit}
uv run --locked pytest -q tests/test_retained_runtime_coverage_inventory.py
```

The local gate is not evidence of a remote CI result. The next GitHub Actions
run after this commit is the final validation of checkout history availability.
