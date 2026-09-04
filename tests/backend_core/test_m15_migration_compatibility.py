from __future__ import annotations

import json

from alembic import command
from sqlalchemy import create_engine, inspect, text

from plotloom.api import create_app
from plotloom.domain import ProjectBrief, RunKind, StageName
from plotloom.persistence import SQLiteRepository
from plotloom.schema import SchemaMigrator


def test_0005_to_head_preserves_sealed_history_json_and_hash_bytes(tmp_path) -> None:
    """A head upgrade must copy sealed 0005 evidence without re-serializing it.

    In particular, 0007 batch-rebuilds ``v2_generation_runs`` on SQLite.  The
    assertion deliberately reads raw SQLite JSON text rather than ORM values:
    normal JSON decoding would hide an accidental reserialization that changes
    immutable historical evidence.
    """

    database_url = f"sqlite:///{tmp_path / '0005-to-head.sqlite3'}"
    migrator = SchemaMigrator(database_url)
    configuration = migrator._config()
    command.upgrade(configuration, "0005_v2_generation_work_units")
    engine = create_engine(database_url)

    run_id = "run-0005-terminal"
    stage_plan_id = "stage-plan-0005"
    plan_hash = "1" * 64
    dependency_hash = "2" * 64
    stage_plan_hash = "3" * 64
    manifest_hash = "4" * 64
    raw_json = {
        "provider_snapshot": '{  "profile" : "legacy", "locale" : "zh-Hans" }',
        "requested_stages": '[ "story_bible" ]',
        "canonical_snapshot": '{ "story_bible" : { "revision" : 1, "hash" : "evidence" } }',
        "result_revision_ids": '[ "revision-0005" ]',
        "plan": '{ "run_id" : "run-0005-terminal", "requested_stages" : [ "story_bible" ], "policy" : { "version" : 5 } }',
        "stage_plan": '{ "stage" : "story_bible", "units" : [ ], "selector" : { "scope" : "sealed" } }',
        "manifest": '{ "artifact_ids" : [ ], "sealed" : true }',
        "payload": '{ "story_bible" : { "logline" : "历史证据必须原样保留", "tags" : [ "sealed", "v5" ] } }',
    }
    expected_hashes = {
        "plan_hash": plan_hash,
        "generation_plan_hash": plan_hash,
        "dependency_hash": dependency_hash,
        "stage_plan_hash": stage_plan_hash,
        "manifest_hash": manifest_hash,
    }

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO v2_projects (id, revision, brief, created_at, updated_at)
                    VALUES ('project-0005', 1, '{ "title" : "历史项目" }', :now, :now)
                    """
                ),
                {"now": "2026-09-02 12:00:00"},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO v2_generation_runs
                    (id, project_id, kind, parent_run_id, repair_stage, repair_source,
                     provider_snapshot, requested_stages, status, canonical_snapshot,
                     instructions, legacy_unsealed, result_revision_ids, error,
                     created_at, started_at, finished_at)
                    VALUES
                    (:run_id, 'project-0005', 'pipeline', NULL, NULL, NULL,
                     :provider_snapshot, :requested_stages, 'completed', :canonical_snapshot,
                     NULL, 0, :result_revision_ids, NULL, :now, :now, :now)
                    """
                ),
                {"run_id": run_id, "now": "2026-09-02 12:00:00", **raw_json},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO v2_generation_plans (run_id, plan_hash, plan, created_at)
                    VALUES (:run_id, :plan_hash, :plan, :now)
                    """
                ),
                {
                    "run_id": run_id,
                    "plan_hash": plan_hash,
                    "plan": raw_json["plan"],
                    "now": "2026-09-02 12:00:00",
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO v2_generation_stage_plans
                    (id, run_id, stage, generation_plan_hash, dependency_hash,
                     stage_plan_hash, plan, created_at)
                    VALUES (:stage_plan_id, :run_id, 'story_bible', :generation_plan_hash,
                            :dependency_hash, :stage_plan_hash, :stage_plan, :now)
                    """
                ),
                {
                    "stage_plan_id": stage_plan_id,
                    "run_id": run_id,
                    "generation_plan_hash": plan_hash,
                    "dependency_hash": dependency_hash,
                    "stage_plan_hash": stage_plan_hash,
                    "stage_plan": raw_json["stage_plan"],
                    "now": "2026-09-02 12:00:00",
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO v2_sealed_stage_aggregates
                    (id, run_id, stage_plan_id, stage, manifest_hash, manifest, payload, created_at)
                    VALUES ('seal-0005', :run_id, :stage_plan_id, 'story_bible', :manifest_hash,
                            :manifest, :payload, :now)
                    """
                ),
                {
                    "run_id": run_id,
                    "stage_plan_id": stage_plan_id,
                    "manifest_hash": manifest_hash,
                    "manifest": raw_json["manifest"],
                    "payload": raw_json["payload"],
                    "now": "2026-09-02 12:00:00",
                },
            )

        command.upgrade(configuration, "head")

        with engine.connect() as connection:
            migrated = connection.execute(
                text(
                    """
                    SELECT runs.provider_snapshot, runs.requested_stages,
                           runs.canonical_snapshot, runs.result_revision_ids,
                           plans.plan, plans.plan_hash,
                           stage_plans.plan AS stage_plan,
                           stage_plans.generation_plan_hash, stage_plans.dependency_hash,
                           stage_plans.stage_plan_hash,
                           seals.manifest, seals.payload, seals.manifest_hash,
                           seals.schema_version AS seal_schema_version
                    FROM v2_generation_runs AS runs
                    JOIN v2_generation_plans AS plans ON plans.run_id = runs.id
                    JOIN v2_generation_stage_plans AS stage_plans ON stage_plans.run_id = runs.id
                    JOIN v2_sealed_stage_aggregates AS seals ON seals.stage_plan_id = stage_plans.id
                    WHERE runs.id = :run_id
                    """
                ),
                {"run_id": run_id},
            ).mappings().one()

        for column, expected in raw_json.items():
            assert migrated[column].encode("utf-8") == expected.encode("utf-8")
        for column, expected in expected_hashes.items():
            assert migrated[column].encode("utf-8") == expected.encode("utf-8")
        assert migrated["seal_schema_version"] == 1

        run_columns = {column["name"] for column in inspect(engine).get_columns("v2_generation_runs")}
        assert {"failure_code", "failed_stage"} <= run_columns
    finally:
        engine.dispose()


def test_0010_versions_legacy_stage_payloads_without_rewriting_payload_or_media_bytes(tmp_path) -> None:
    """Schema labels are additive; historical JSON evidence is not migrated in place."""

    database_url = f"sqlite:///{tmp_path / '0010-versioning.sqlite3'}"
    migrator = SchemaMigrator(database_url)
    configuration = migrator._config()
    command.upgrade(configuration, "0009_v2_work_unit_repair_scopes")
    engine = create_engine(database_url)
    payload = '{  "legacyDialogue" : "不要由 V2 默认值重写我" }'
    media_components = '{ "legacyPrompt" : [ "byte", "preserve" ] }'
    now = "2026-09-03 12:00:00"

    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO v2_projects
                    (id, revision, lifecycle_revision, lifecycle_status, archived_at, brief, created_at, updated_at)
                    VALUES ('project-0010', 1, 1, 'active', NULL, '{ "title" : "legacy" }', :now, :now)
                    """
                ),
                {"now": now},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO v2_entity_revisions
                    (id, project_id, stage, revision, parent_revision_id, content_hash, input_revisions, payload, created_at)
                    VALUES ('revision-0010', 'project-0010', 'storyboard', 1, NULL, :hash, '{}', :payload, :now)
                    """
                ),
                {"hash": "a" * 64, "payload": payload, "now": now},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO v2_stage_heads
                    (id, project_id, stage, status, revision, entity_revision_id, content_hash, input_revisions, stale_reasons, updated_at)
                    VALUES ('project-0010:storyboard', 'project-0010', 'storyboard', 'ready', 1,
                            'revision-0010', :hash, '{}', '[]', :now)
                    """
                ),
                {"hash": "a" * 64, "now": now},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO v2_media_tasks
                    (id, project_id, shot_id, storyboard_revision, kind, status, derived_prompt,
                     prompt_components, provider, public_settings, provider_task_id, output_uri,
                     error, created_at, updated_at, started_at, finished_at)
                    VALUES ('media-0010', 'project-0010', 'shot-1', 1, 'image', 'succeeded', 'legacy',
                            :components, NULL, '{}', NULL, 'file:///historical', NULL, :now, :now, :now, :now)
                    """
                ),
                {"components": media_components, "now": now},
            )

        command.upgrade(configuration, "head")

        with engine.connect() as connection:
            entity = connection.execute(
                text("SELECT schema_version, payload FROM v2_entity_revisions WHERE id = 'revision-0010'")
            ).one()
            head = connection.execute(
                text("SELECT schema_version FROM v2_stage_heads WHERE id = 'project-0010:storyboard'")
            ).scalar_one()
            media = connection.execute(
                text("SELECT prompt_components FROM v2_media_tasks WHERE id = 'media-0010'")
            ).scalar_one()

        assert entity.schema_version == 1
        assert head == 1
        assert entity.payload.encode("utf-8") == payload.encode("utf-8")
        assert media.encode("utf-8") == media_components.encode("utf-8")
    finally:
        engine.dispose()


def test_0006_keeps_historic_v1_run_snapshot_and_plan_bytes_while_terminating_live_work(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'migration.sqlite3'}"
    repository = SQLiteRepository(database_url)
    project = repository.create_project(ProjectBrief(title="历史", synopsis="不能改写已冻结证据。"))
    run = repository.create_run(project.id, RunKind.PIPELINE, [StageName.STORY_BIBLE])
    before_snapshot = repository.get_run(run.id).provider_snapshot
    before_plan = repository.get_generation_plan(run.id).model_dump(mode="json", by_alias=False)
    before_hash = repository.get_generation_plan(run.id).plan_hash
    repository.close()

    migrator = SchemaMigrator(database_url)
    command.downgrade(migrator._config(), "0005_v2_generation_work_units")
    command.upgrade(migrator._config(), "0006_v2_model_profiles")

    reopened = SQLiteRepository(database_url)
    try:
        # 0006 deliberately writes a secret-free legacy seed. Runtime startup,
        # which is the trusted owner of environment defaults, materializes it.
        create_app(reopened)
        migrated = reopened.get_run(run.id)
        assert migrated.provider_snapshot == before_snapshot
        assert reopened.get_generation_plan(run.id).plan_hash == before_hash
        assert reopened.get_generation_plan(run.id).model_dump(mode="json", by_alias=False) == before_plan
        assert migrated.status.value == "failed"
        assert migrated.failure_code == "migration.execution_contract_changed"
        assert migrated.failed_stage is None
        assert "predates the frozen model-profile/topology contract" in (migrated.error or "")
        assert reopened.get_text_provider_profile("default").revision == 0
    finally:
        reopened.close()


def test_0006_removes_legacy_api_keys_from_old_and_named_provider_settings(
    tmp_path,
) -> None:
    database_url = f"sqlite:///{tmp_path / 'legacy-secrets.sqlite3'}"
    migrator = SchemaMigrator(database_url)
    command.upgrade(migrator._config(), "0005_v2_generation_work_units")
    engine = create_engine(database_url)
    legacy_settings = {
        "textModel": "safe-model",
        "apiKey": "legacy-top-level-secret",
        "nested": {
            "access_token": "legacy-nested-secret",
            "publicFlag": True,
        },
    }
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO v2_provider_settings "
                    "(id, settings, revision, updated_at) "
                    "VALUES (1, :settings, 4, CURRENT_TIMESTAMP)"
                ),
                {"settings": json.dumps(legacy_settings)},
            )

        command.upgrade(migrator._config(), "0006_v2_model_profiles")

        with engine.connect() as connection:
            old_value = connection.execute(
                text("SELECT settings FROM v2_provider_settings WHERE id = 1")
            ).scalar_one()
            profile_value = connection.execute(
                text(
                    "SELECT settings FROM v2_text_provider_profiles "
                    "WHERE id = 'default'"
                )
            ).scalar_one()
        old_settings = json.loads(old_value) if isinstance(old_value, str) else old_value
        profile_settings = (
            json.loads(profile_value)
            if isinstance(profile_value, str)
            else profile_value
        )
        assert old_settings == {
            "textModel": "safe-model",
            "nested": {"publicFlag": True},
        }
        assert profile_settings == old_settings
        serialized = json.dumps(
            {"old": old_settings, "profile": profile_settings},
            sort_keys=True,
        )
        assert "legacy-top-level-secret" not in serialized
        assert "legacy-nested-secret" not in serialized
    finally:
        engine.dispose()
