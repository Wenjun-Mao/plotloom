export type ReviewContextCode = "source_context_not_ready" | "installed_graph_not_current" |
  "installed_graph_context_mismatch" | "accepted_cast_not_current" | "binding_revision_changed" |
  "binding_content_changed" | "section_context_changed" | "art_render_contract_changed" | "cast_render_contract_changed" |
  "accepted_art_not_current" | "accepted_script_not_current" | "playthrough_target_missing" | "binding_value_changed";
export type ReviewContextField = "source_revision" | "outline_revision" | "section_map_revision" |
  "graph_revision" | "cast_revision" | "source_content_hash" | "outline_content_hash" |
  "section_map_content_hash" | "graph_content_hash" | "cast_content_hash" |
  "art_revision" | "art_content_hash" | "script_revision" | "script_content_hash" |
  "target_playthrough_seconds" | "route_budget_hash" | "section_bindings" |
  "complete_route_section_ids" | "route_only_section_ids" | "section_ids" |
  "render_contract" | "review_min_cut_seconds" | "review_max_cut_seconds" | "review_max_segment_seconds";
export interface ReviewContextDiagnostic {
  code: ReviewContextCode;
  owner: "source" | "characters" | "art" | "script" | "brief" | "storyboard-review";
  technicalMessage: string;
  field: ReviewContextField | null;
}
