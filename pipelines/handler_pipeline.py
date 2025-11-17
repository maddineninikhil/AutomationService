from .base_handler import ActionHandler
from . import handlers

class HandlerPipeline:
    def __init__(self):
        self.handlers = [cls() for cls in ActionHandler.registry]

    def execute(self, actions, driver):
        for action in actions:
            for handler in self.handlers:
                if handler.can_handle(action):
                    handler.handle(action, driver)
                    break
            else:
                raise ValueError(f"No handler found for action: {action}")
