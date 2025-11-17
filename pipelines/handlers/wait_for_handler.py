from pipelines.base_handler import ActionHandler

class WaitForSelectorHandler(ActionHandler):
    def can_handle(self, action):
        return action.get("action") == "wait_for"

    def handle(self, action, driver):
        selector = action["selector"]
        timeout = action.get("timeout", 30000)      # default 30s
        state   = action.get("state", "visible")

        driver.wait_for(selector, timeout=timeout, state=state)