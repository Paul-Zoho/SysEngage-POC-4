"""
SQLAlchemy ORM models for SysEngage persistence layer.

All models must be imported here so SQLAlchemy's mapper registry can resolve
string-based relationship() references (e.g. "ProjectProfileModel") at
configuration time. Importing any one model triggers mapper initialisation for
all models registered on the shared Base, so every model module must appear
in this file.

Per Row 4 Applied §5 and Implementation Spec §5.2.
Each entity has its own module. All models use Base from models/base.py.
"""

from models.project import ProjectModel
from models.stakeholder import StakeholderModel
from models.segment import SegmentModel
from models.source import SourceModel
from models.source_atom import SourceAtomModel
from models.analysis_pass import AnalysisPassModel
from models.project_profile import ProjectProfileModel
from models.signal import SignalModel
from models.concern import ConcernModel
from models.domain import DomainModel
from models.requirement import RequirementModel

__all__ = [
    "ProjectModel",
    "StakeholderModel",
    "SegmentModel",
    "SourceModel",
    "SourceAtomModel",
    "AnalysisPassModel",
    "ProjectProfileModel",
    "SignalModel",
    "ConcernModel",
    "DomainModel",
    "RequirementModel",
]
