# Persistence media/control extraction receipt

## Outcome

Project media policy now lives in `persistence/project/media.py`. Provider
profiles/settings live in `persistence/application/profiles.py`; Wan pilot
reservation/event accounting lives in `persistence/application/accounting.py`
and joins the existing video lifecycle transaction. Authoring uses explicit
leases, row guards, and codecs rather than `SQLiteRepository` references.

`ProjectSQLiteRepository` moved to `persistence/project/repository.py` with its
bound-ID/admitted-snapshot safeguards and public import unchanged.

## Evidence

- focused authoring/repository, project-storage, modularization-contract, and
  profile suites: **54 passed**;
- image-job and video-job transaction/recovery suites: **34 passed**;
- structural regression rejects authoring/media/application bounce-backs to
  the retained facade.

No provider call, video replay, schema migration, or frontend asset change was
performed.
