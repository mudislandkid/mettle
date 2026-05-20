"""Mettle web backend security primitives.

- settings: env-var loader (METTLE_*)
- auth: HTTP middleware + WebSocket handshake helper
- path_jail: path-allow-list enforcement
- startup: one-shot process-aborting gates run at boot
"""
