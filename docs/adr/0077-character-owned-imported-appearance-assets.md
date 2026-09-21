# ADR 0077: Character-owned imported appearance assets

**Status:** Accepted

## Decision

Existing managed-image import remains the sole byte/provenance owner. A new,
immutable character-owned membership records which imported project asset is an
unselected appearance option for one current accepted-cast subject, its frozen
cast context, and a creator-visible label. It is not an identity-reference
decision and cannot select a reference implicitly.

The Characters gallery composes current and stale imported memberships with
proposal deliveries. Both retain readable evidence while reopened/stale cast
state disables import, selection, and refinement. The existing reference
decision owner remains the only selection authority.

The byte import and the membership attachment are intentionally separate
mutations. If the browser changes project or cast session while an upload is
in flight, it may finish storing the generic managed asset, but it must not
issue the follow-on membership request. The membership endpoint independently
requires the captured current accepted-cast revision, so a stale client cannot
attach an asset even when bypassing the gallery's session guard.

Imported memberships are not specialist-delivery candidates. They may be
browsed, compared, enlarged, and explicitly selected, but they cannot be used
as a character-reference proposal refinement parent. The UI must surface that
boundary and offer a fresh proposal instead of sending an invalid parent ID.
