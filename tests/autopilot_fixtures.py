"""Disposable policy/source builders; never dispatch native specialists."""
from plotloom.autopilot_contracts import LaunchPolicy, CommandAuthority, OperationScope
from plotloom.persistence.codec import stable_hash
from plotloom.source_outline_contracts import SourceMaterial


def policy_for(store):
    return LaunchPolicy(render_style="live-action", art_render_style="live-action",
        image_width=1280, image_height=720,
        specialist_bindings={"text": "00000000-0000-4000-8000-000000000001", "image": "00000000-0000-4000-8000-000000000002"},
        execution_pins={}, brief=store.project().brief.model_dump(mode="json", by_alias=False))


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
