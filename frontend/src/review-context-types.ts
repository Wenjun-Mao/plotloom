export type ReviewContextCode = "source_context_not_ready" | "installed_graph_not_current" |
  "installed_graph_context_mismatch" | "accepted_cast_not_current" | "binding_revision_changed" |
  "binding_content_changed" | "section_context_changed" | "art_render_contract_changed";
export type ReviewContextField = "source_revision" | "outline_revision" | "section_map_revision" |
  "graph_revision" | "cast_revision" | "source_content_hash" | "outline_content_hash" |
  "section_map_content_hash" | "graph_content_hash" | "cast_content_hash";
export interface ReviewContextDiagnostic {
  code: ReviewContextCode;
  owner: "source" | "characters" | "art";
  technicalMessage: string;
  field: ReviewContextField | null;
}
