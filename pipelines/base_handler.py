class ActionHandler:
    registry = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        ActionHandler.registry.append(cls)

    def can_handle(self, action):
        raise NotImplementedError

    def handle(self, action, driver):
        raise NotImplementedError
