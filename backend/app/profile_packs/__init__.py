"""Profile packs: one config-driven way to describe an exception profile (see claude/pex_profile_pack_design.md).

A pack is data (a JSON file in packs/) plus, where the profile repairs something, one small pure resolver function.
The orchestrator (e2e_runner) keeps owning the shared steps. Packs are switched on per profile with the
PEX_PROFILE_PACKS environment variable (default: off, so behaviour is unchanged).
"""
