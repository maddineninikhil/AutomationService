from pipelines.base_handler import ActionHandler

class InputHandler(ActionHandler):
    def can_handle(self, action):
        return action.get("action") == "input"

    def handle(self, action, driver):
        driver.input(action["selector"], action["value"])
