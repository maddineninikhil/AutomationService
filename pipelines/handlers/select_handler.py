from pipelines.base_handler import ActionHandler

class SelectHandler(ActionHandler):
    def can_handle(self, action):
        return action.get("action") == "select"

    async def handle(self, action, driver):
        page = driver.page
        selector = action.get("selector")
        value = action.get("value")

        locator = page.locator(selector)
        await locator.select_option(value=value)
