# ADR 0110 — Known project identity before admission

Status: accepted for the bounded E2E runtime repair, 2026-10-04.

## Problem

A browser restart trace returned404 for a retained project. Directory discovery
intentionally suppresses unavailable/corrupt stores, but known-ID lookup reused
that filtered catalog. A disposable exclusive-lease reproduction proves an
existing, valid-manifest home becomes “not found.” The exact rejected admission
reason in the historical restart trace remains unknown.

## Decision

Resolve a known project ID from confined, non-hidden regular manifests without
opening every project database. Then run the existing target-home schema, lease,
storage and operational-state admission checks, preserving their busy/corrupt/
closed errors. Refuse duplicate identities and invalid matching manifests. Keep
catalog discovery's availability filtering unchanged; it is not identity truth.

## Alternatives and guardrails

Browser reload retries or tolerant404 handling would conceal admission errors.
A cached alternate registry would introduce another identity authority. Neither
is used. Regression tests cover known busy/corrupt homes, unrelated-store
isolation, absent identities and duplicates. Existing confinement, schema and
closed-home suites remain required. No lease, schema or persistence rule changes.
