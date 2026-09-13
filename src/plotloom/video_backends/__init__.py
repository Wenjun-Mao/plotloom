"""Provider-owned video backend implementations.

Generic production lifecycle code deliberately imports only the contracts in
``plotloom.video_provider``.  A backend package owns its private transport,
capability record, and provider-specific request/response handling.
"""
