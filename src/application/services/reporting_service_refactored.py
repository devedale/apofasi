"""Compat layer per mantenere compatibilità con test e import legacy.

Espone `ReportingService` dal modulo aggiornato `reporting_service`.
"""

from .reporting_service import ReportingService  # noqa: F401


