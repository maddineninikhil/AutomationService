from pipelines.base_handler import ActionHandler

class ClickHandler(ActionHandler):
    def can_handle(self, action):
        return action.get("action") == "click"

    def handle(self, action, driver):
        driver.click(action["selector"])
