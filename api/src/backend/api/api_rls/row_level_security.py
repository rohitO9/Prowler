class RowLevelSecurityConstraint:
    def __init__(self, *args, name: str = None, **kwargs):
        self.name = name
        self._kwargs = dict(kwargs)
        if name is not None:
            self._kwargs['name'] = name  # Include name in _kwargs for cloning

    def clone(self):
        return RowLevelSecurityConstraint(**self._kwargs)
    
    def deconstruct(self):
        """
        Required method for Django migration serialization.
        Returns a tuple of (path, args, kwargs) that can be used to recreate this object.
        """
        path = f'{self.__class__.__module__}.{self.__class__.__qualname__}'
        return (
            path,
            [],  # args - empty since we use **kwargs
            self._kwargs  # All the kwargs needed to recreate this constraint
        )