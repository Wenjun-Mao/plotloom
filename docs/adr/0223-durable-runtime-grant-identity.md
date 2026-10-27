# 0223: Durable database identity for installation-local execution grants

Status: accepted bounded repair decision, 2026-10-27.

The installed OrbStack virtiofs view no longer matches the device/inode values
retained in any of its 28 video/QA grant rows. Host DB identities match retained
activation evidence; the exact historical cause of guest identity drift remains
unproven. Filesystem inode numbers are useful within one command, but are not a
durable installation authorization identity across a shared-filesystem lifecycle.

Bind new grants to an immutable random database-attached extended attribute plus
the exact canonical home, project, batch/scope identity and immutable manifest
hash. A small platform leaf owns descriptor-based Linux/macOS xattr access;
unknown, missing, malformed or unsupported metadata fails closed. Only trusted
grant authorization may create the attribute, exclusively and durably. Reads,
including browser QA discovery, never create metadata or grant tables. A token
left by a failed grant transaction confers no authority by itself.

Use a distinct current grant table; old inode rows are never an executable
fallback. Existing scopes require reviewed one-time
exact-inventory adoption with old-row/current-material checks, never enrollment
by a label or a blanket regrant. Preserve source scope hashes and prior budget,
attribution, before-send/UNKNOWN and currentness contracts. New ordinary batch
authorization uses the same identity owner without acquiring agent-QA authority.

After independently verified adoption, the owner authorized retiring the obsolete
28-row inode table. Current code neither creates nor reads it; the cleanup keeps
all 25 current grants exact. Historical verification does not require indefinite
retention of inert operational rows.

The current snapshot backup and restore copy only declared bytes into newly
created files, omitting xattrs. Different-home copies fail the home binding; a
same-home restored or byte-replaced DB has no matching file identity. Keep the
ephemeral path/device/inode command context to catch a replacement during a QA
write. Deliberately cloning both all local identity metadata and original paths
outside supported lifecycle tools is outside this boundary: local filesystem
write access can forge local authority. This identifier is metadata, not a secret
credential or portable approval. No project-schema or portable-format change.

This supersedes only ADR 0198's durable device/inode binding. Its exact scopes,
truthful agent attribution and refusal to confer authority on copies/restores
remain. Authorization does not establish material inspection or owner approval.
