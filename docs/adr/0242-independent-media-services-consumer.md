# External media-services source ownership

Date: 2026-11-16. Status: accepted by Wenjun.

Gateway/dashboard and Voice Lab implementation, packaging, owned tests and operator manuals move to private `Wenjun-Mao/media-services`. Relevant history is preserved there; Plotloom history is not rewritten. ADR 0216's monorepo location is superseded. Historical ADRs and receipts retained here remain truthful records, not competing maintained implementation manuals.

Plotloom owns application/UI/story policy, creator-workbench, H3 HTTP adapter/catalog and consumer tests. It imports neither service package and needs no sibling backend checkout at runtime. Root owner selectors now cover retained consumers; backend checks live with their source. Verify changed contracts using the real Plotloom transport against an installed gateway, with only generation/provider behavior faked.

Colleagues are service users and need no GitHub invitations. Existing H3/Qwen usage-guide URLs remain; Voice Lab/take instructions join the existing operations manuals. Full source/operator instructions have one canonical home in media-services.

No HTTP API, runtime, model, service URL or data location changes. Preserve retained deployed workbench snapshots, pending client-IP activation and stopped Tailnet. Source ownership does not itself authorize a production restart or CI run.
