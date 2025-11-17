from pipelines.base_handler import ActionHandler

class GotoHandler(ActionHandler):
    def can_handle(self, action):
        return action.get("action") == "goto"

    def handle(self, action, driver):
        driver.goto(action["value"])
