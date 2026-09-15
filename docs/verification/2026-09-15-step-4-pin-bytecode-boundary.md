# Step 4 specialist-pin bytecode boundary repair

This is a source-attestation regression receipt, not a media attempt, creative
acceptance, or Step 4 completion.

## Root cause and repair

The modular pin boundary correctly includes the recursive API and persistence
source packages. Git's ignored-status output may collapse a normal Python
`__pycache__` directory into one dirty entry, though. The old preflight treated
that aggregate entry as authored source and refused a clean checkout after
ordinary imports.

The repair classifies only non-executable PEP 3147-style `.pyc` files as runtime
bytecode. It expands the collapsed cache directory before accepting it, so an
old cache from a committed module move is not confused with authored source.
Any source file, executable, symlink, nested directory, or malformed name
remains an uncommitted-change refusal.

## Regression evidence

- Fixture modules in the actual API and persistence package paths are imported
  with the running Python interpreter before a clean preflight; their normal
  bytecode caches do not block pinning.
- A real non-executable, PEP 3147-style stale `.pyc` is compiled from a
  temporary source file that is removed before preflight. It pins successfully,
  and an import side effect embedded in that bytecode never occurs.
- Modified tracked API source still refuses after those imports.
- Hidden Python source, an executable cache-named file, a symlink, a nested
  directory, and a real bytecode file with a malformed cache filename inside
  an ignored `__pycache__` directory each refuse and report the specific entry.
- Existing staged deletion, untracked source, ignored source, missing committed
  source, provenance, and re-pin refusal coverage remains in the same focused
  suite.

No package was pinned or rewritten while collecting this regression evidence.
No ImageGen, provider, or H3 operation occurred. The preserved exploratory Step
4 package remains untouched; a separately authorized media continuation must
still use its own preflight and acceptance boundary.
