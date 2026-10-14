"""Disposable policy/source builders; never dispatch native specialists."""
from plotloom.autopilot_contracts import LaunchPolicy, CommandAuthority, OperationScope
from plotloom.codex_exec_contracts import CodexExecProfile
from plotloom.persistence.codec import stable_hash
from plotloom.source_outline_contracts import SourceMaterial


def policy_for(store):
    profile = CodexExecProfile(executable_sha256="0" * 64, cli_version="codex-cli test", model="gpt-6.1-sol",
        reasoning_effort="medium", capabilities=("exec_json_events_v1", "session_rollout_v1", "image_gen_event_v1", "delivery_directory_write_v1"),
        instruction_hash="1" * 64, validator_hash="2" * 64, sandbox_profile="read_only_with_delivery_write",
        max_runtime_seconds=1800, max_event_bytes=1_000_000, max_output_bytes=100_000_000, max_image_outputs=4)
    return LaunchPolicy(version="plotloom.pre-video.v4", render_style="live-action", art_render_style="live-action", code_revision="a" * 40,
        image_width=1280, image_height=720,
        specialist_bindings=None, executor_binding=profile,
        execution_pins={"image": {"contract": "codex_exec.v1"}}, brief=store.project().brief.model_dump(mode="json", by_alias=False))


def start_run(store):
    run = store.repository.autopilot.start(store.manifest.project_id,
        expected_brief_revision=store.project().revision, policy=policy_for(store))
    store.repository.autopilot.claim(store.manifest.project_id, "fixture-controller")
    return run


def authority(run, scope=OperationScope.SOURCE):
    return CommandAuthority(run.id, "fixture-controller", scope)


def exact_source(store):
    project = store.project()
    return SourceMaterial(kind="synopsis", title=project.brief.title, text=project.brief.synopsis,
        brief_origin={"revision": project.revision,
            "contentHash": stable_hash(project.brief.model_dump(mode="json", by_alias=False))})


def make_prior_layout(home):
    """Copy only frozen prior columns into a disposable immediate-prior DB."""
    import sqlite3
    from plotloom.project_storage.schema_upgrade import prior_schema_objects
    database = home / "project.sqlite3"
    destination = home / "prior-transfer.sqlite3"
    source = sqlite3.connect(database)
    target = sqlite3.connect(destination)
    try:
        objects = prior_schema_objects()
        for kind, _name, _table, sql in objects:
            if kind == "table":
                target.execute(sql)
        for kind, name, _table, sql in objects:
            if kind == "table":
                columns = [row[1] for row in target.execute(f'PRAGMA table_info("{name}")')]
                projection = ",".join(f'"{column}"' for column in columns)
                rows = source.execute(f'SELECT {projection} FROM "{name}"').fetchall()
                if rows:
                    target.executemany(f'INSERT INTO "{name}" ({projection}) VALUES ({",".join("?" for _ in columns)})', rows)
            elif kind == "index":
                target.execute(sql)
        target.commit()
    finally:
        target.close()
        source.close()
    database.unlink()
    for suffix in ("-wal", "-shm"):
        database.with_name(database.name + suffix).unlink(missing_ok=True)
    destination.rename(database)
