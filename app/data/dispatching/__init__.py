"""
Dispatching models package (Phase 3)
Refactored structure with outcomes decoupled from EventDetailVirtual.

Main components:
- DispatchRequest: The initial request (inherits from EventDetailVirtual)
- VirtualDispatchOutcome: Base class for outcomes (StandardDispatch, Contract, Reimbursement)
- DispatchManager: Interface for managing request-to-event and outcome relationships
- DispatchContext: Primary interface for route interactions, holds references to all related objects
"""




