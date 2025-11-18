from pipelines.base_handler import ActionHandler

class WaitForSelectorHandler(ActionHandler):
    def can_handle(self, action):
        return action.get("action") == "wait_for"

    async def handle(self, action, driver):
        page = driver.page
        selector = action.get("selector")
        value = action.get("value", 30000)

        dom_events = {
            "domloaded": "domcontentloaded",
            "domcontentloaded": "domcontentloaded",
            "load": "load",
            "networkidle": "networkidle"
        }

        if selector is None and value in dom_events:
            await page.wait_for_load_state(dom_events[value])
            return

        await page.wait_for_selector(selector, timeout=value)
