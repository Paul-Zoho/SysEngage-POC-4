"""
RETIRED — domain_cci_membership join table.

Per Domain Derivation Mechanism Spec v0.17 §3.2 MD-4:
  cell_content_item_refs is stored as a JSONB array directly on the domain
  table. The domain_cci_membership join table was retired in migration 016
  after the first PMT production ledger export confirmed it produced Domain
  entities with cell_content_item_refs absent from the canonical payload.

Migration 016 (016_domain_cell_content_item_refs.py) drops this table and
adds the cell_content_item_refs JSONB column to the domain table.

Do NOT import DomainCCIMembershipModel — the table no longer exists.
Do NOT add this file back to models/__init__.py.
"""
