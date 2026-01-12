"""
Controller Base Abstraction
"""

class Controller:
    """Base controller class"""

    def reconcile(self):
        """Reconcile desired state with actual state"""
        raise NotImplementedError
