# Media services in a modular Plotloom monorepo

Status: repository direction and implementation approved by the owner on 2026-10-22.
Numbering is deferred until integration, as coordinated with the Plotloom director;
the specialist's historical ADR sequence collides with newer main. Implementation follows the
[boundary-strengthening plan](../roadmap/2026-10-22-media-service-boundaries.md);
no deployment or integration acceptance is implied.

## Context

H3, Qwen-Image, Voice Lab and the gateway dashboard support Plotloom and also
serve direct internal users. Their processes and data already have separate
owners. Repository separation would add release coordination while their shared
generation lane and gateway/dashboard private schema remain operationally coupled.
The immediate maintenance gap is build/dependency ownership: the dashboard uses
Plotloom's root lockfile, whereas the gateway installs a hand-pinned environment.

## Decision

- Retain the services in Plotloom. Continue ADR 0035's HTTP client/runtime boundary;
  Plotloom owns authoring, selection and durable project assets, not remote model
  execution or service databases.
- Keep gateway and dashboard in one service-owned Python package/lock with separate
  deployment entrypoints/images. Keep Voice Lab's independent package and isolated
  inference environments. ComfyUI and SGLang remain separate runtimes.
- Preserve ADR 0097's sole managed generation-admission owner. Independent builds
  and deployments do not authorize concurrent inference or independent dispatch.
- Treat dashboard read access to gateway SQLite as an explicit private contract.
  Preserve fail-closed schema checks and read-only storage access. The dashboard's
  existing protected submission forwarding remains allowed under ADR 0100.
- Maintain service-owned build/test/operations instructions and a small change-impact
  matrix. Check and deploy affected components, not the entire repository by default.
  Contract-affecting changes still require checks of their actual consumers.
- Avoid directory renaming, new public contracts and historical compatibility layers
  merely to improve packaging. An eventual extraction would move the media-services
  subsystem together, leaving Plotloom-specific clients and creative policy behind.

## Alternatives and consequences

Separate repositories now would provide independent permissions/releases, but
would also require cross-repository coordination for the still-evolving shared
lane, take contracts and consumer tests. Reconsider when distinct ownership,
consumers or release needs create an observed benefit that exceeds that cost.

One universal repository environment would be simpler to install initially but
would couple CPU services to Plotloom and incompatible inference stacks. The chosen
boundary instead permits independent locked artifacts and selective restart while
retaining atomic source review when several components must change together.

## Guardrails

Verify clean installed artifacts with no Plotloom import or source-tree dependency;
package workflow/static resources; preserve independent startup and shared-lane
safety; maintain private-schema failure tests and affected HTTP consumer tests.
No new repository, model behavior, storage lifecycle or integration authority is
created by this decision. Write and runtime coordination with the director is
authorized; specialist integration, merge and push remain held.
