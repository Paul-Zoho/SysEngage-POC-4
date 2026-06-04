"""
Data Dictionary Service — cross-row standalone service (F93).

Per Data Dictionary Mechanism Spec (Row 4 Physical) v0.1.
Realises ledger v2.14 (DataDictionaryEntry / DataDictionaryRegister).

Public API:
  from mechanisms.data_dictionary.service import (
      resolve_term, record_relationship, record_value,
      resolve_object, aliases_of, relationships_of,
  )
"""
