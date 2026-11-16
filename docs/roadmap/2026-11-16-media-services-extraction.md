# media-services repository extraction · design

Status: brainstorm completed on 2026-11-16. Repository scope, name, hosting and audience are agreed. The technical defaults below are proposals for the implementation plan. No repository has been created and no source or production state has been moved. Extend this same record when Relay Plan is explicitly invoked.

## Agreed direction

The gateway has grown into a shared media backend, making a separate source repository useful. Wenjun selected:

- Move the gateway and dashboard together, and include Voice Lab.
- Name the repository `media-services`.
- Use a private GitHub repository under `Wenjun-Mao`: `Wenjun-Mao/media-services`.
- Use the proposed local checkout `/Users/wjmao/projects/HU/media-services`, beside Plotloom.
- Give Wenjun and his backend colleagues access to the repository and its manuals.
- Carry forward the earlier proposal to preserve relevant Git history and leave Plotloom with its client integration.

The intended benefit is clear backend ownership and independent maintenance, testing and releases. Plotloom and direct internal API users remain consumers of the same working services.

## Source-backed starting point

The design starts from local main `f251e6b4`, which contains the implemented optional reference-audio endpoint. Later planning must refresh the source identity and preserve any intervening work. Local history matters: unpublished local changes must not be lost by starting solely from a GitHub clone.

The earlier [ADR 0216](../adr/0216-media-services-monorepo-boundaries.md) kept the services in Plotloom while strengthening package/build ownership. It anticipated eventual extraction of the media-services subsystem together. The new user direction changes repository ownership; the established runtime boundaries remain useful. [ADR 0212](../adr/0212-published-voice-performance-takes-and-shared-admission.md) owns shared admission, and the [operations map](../operations/media-services.md) describes the current deployments.

Current facts:

- Gateway and dashboard already have one service-owned Python package/lock and separate entrypoints/images. The dashboard reads gateway SQLite/output files directly in read-only mode, so they belong in the same source project.
- Voice Lab has its own package, lock, database and engine environments. Production runtime communication with the gateway is authenticated HTTP in both directions; neither imports the other's Python runtime.
- The gateway owns the single managed generation lane for H3, Qwen image and Voice Lab work. Source separation must preserve that execution ownership and uncertainty handling.
- Joint Voice Lab tests and operator tools do use sibling gateway source paths and inspect both services' state. Moving the services together keeps that qualification work with its owning subsystem.
- Some gateway tests, backend manuals, ADRs and deployment tooling currently live outside the gateway subtree. A directory-only copy would miss part of the maintained product.
- Plotloom's H3 adapter owns its client catalog/HTTP transport, not gateway or inference storage.
- Plotloom's GitHub repository is currently public. The new private repository requires explicit colleague access for its backend manuals. This choice does not change Plotloom's visibility.
- The proposed local destination does not exist. A read-only GitHub lookup for the target returned404; availability and account access must be checked again before creation.

## Approaches considered

| Boundary | Benefit | Cost / consequence |
|---|---|---|
| Gateway and dashboard only | Smaller first extraction | Voice Lab and shared queue/restart tests remain split across source repositories |
| Gateway, dashboard and Voice Lab together | Backend protocols, joint tests and operations stay under one source owner | More source/documentation paths must be assigned to the new repository |

Wenjun chose the second boundary. This remains a repository containing distinct services, packages and inference environments.

## Proposed ownership map

| Home | Contents |
|---|---|
| `media-services` | Gateway, dashboard, Voice Lab; owned H3/Comfy and Qwen integration code; deployment/install recipes and pinned manifests; service and joint-contract tests; canonical backend client/operator manuals; relevant technical decisions and verification records |
| Plotloom | Authoring application/UI, story assets, creative policies and application-specific skills; its HTTP adapters, consumer compatibility tests and concise integration instructions linking to backend manuals |
| External runtime/storage | Running databases, published voices/takes, generated videos/images, credentials, inference environments, model weights and retained large QA/research media |

All model weights remain under `/home/wjmao/models`. Existing data lifecycles remain distinct: transient gateway deliveries/inputs versus durable Voice Lab identities and takes.

## Proposed technical defaults

These are engineering recommendations, not additional user-specified requirements:

1. Make the first extraction a source-ownership and path correction. Preserve working API URLs/contracts, package/entrypoint names, model/runtime versions and service/storage locations. Source references in maintained tools will need correction; a storage or deployment redesign is outside this slice.
2. Initially retain the existing service directory names and independent locks. A possible layout is:

   ```text
   media-services/
     services/minimax_h3_gateway/
     services/qwen3_tts_voice_lab/
     tests/
     docs/
   ```

   The plan can choose exact test/doc placement while preserving clear owners and runnable commands. No single shared inference environment is proposed.
3. Give backend source and full backend manuals one canonical home in the new repository. Plotloom retains a concise consumer entrypoint and links, avoiding two maintained copies of the same manual.
4. Keep Plotloom's runtime integration over HTTP. Avoid a permanent vendored service copy, cross-repository Python imports or a new shared SDK merely to support extraction. The implementer can choose ordinary local development tooling within this boundary.
5. Preserve relevant source history for the moved files and record their relationship to the Plotloom baseline. Keep historical evidence truthful; update maintained commands rather than rewriting old receipts to claim they used new paths.
6. Give the new repository service-owned verification and release instructions. It should be possible to install, test and build its services from a clean checkout without Plotloom source or dependencies. Keep shared FIFO/restart/UNKNOWN and private dashboard-schema contracts covered together. Plotloom continues to verify its own adapter compatibility when affected contracts change.
7. Retire the old authoritative service source in Plotloom as part of the eventual verified extraction, so the repositories have unambiguous ownership. Avoid maintaining two active source copies.

## What success means

- A colleague with access can discover the source, install/build/test each service using its own lock and find one current set of backend manuals.
- Backend work can be maintained and released from `media-services`, with compatibility checks for actual consumers.
- Plotloom consumes the existing service interfaces, and direct API users retain their documented workflow.
- Shared generation admission, state ownership, voice/take retention and protected unknown outcomes retain their current semantics.
- Relevant history, the latest optional-audio work and current user-valued assets survive the move.

Voice-identity/continuity listening from the optional-audio qualification remains separately unassessed. This extraction does not resume the caption investigation or add a media-quality experiment.

## Inputs and choices for Relay Plan

The product/repository boundary is settled. Planning should resolve exact source/test/doc/history ownership, required path corrections, consumer handoff, verification, publication and any necessary source-deployment reference updates. It owns execution permissions, estimates and independent reviews; those are not imposed by this brainstorm.

Exact colleague GitHub accounts and intended access must be identified before invitations; do not infer them from public contributors or machine names. The agreed audience does not authorize guessing accounts. GitHub Actions/CI remains off under the standing user instruction; no CI workflow work is included here.

Record implementation details and completion evidence in this file rather than creating another overlapping design/plan document. Wait for the user's explicit next workflow invocation before starting Relay Plan or implementation.
