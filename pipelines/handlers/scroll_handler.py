from pipelines.base_handler import ActionHandler

class ScrollHandler(ActionHandler):
    def can_handle(self, action):
        return action.get("action") == "scroll"

    async def handle(self, action, driver):
        page = driver.page
        selector = action.get("selector")
        direction = action.get("value")

        window_scroll_map = {
            "right":  "window.scrollTo({ left: document.body.scrollWidth });",
            "left":   "window.scrollTo({ left: 0 });",
            "bottom": "window.scrollTo({ top: document.body.scrollHeight });",
            "top":    "window.scrollTo({ top: 0 });"
        }

        element_scroll_map = {
            "right":  "el.scrollTo({ left: el.scrollWidth });",
            "left":   "el.scrollTo({ left: 0 });",
            "bottom": "el.scrollTo({ top: el.scrollHeight });",
            "top":    "el.scrollTo({ top: 0 });"
        }

        if selector in (None, "window", "document", "body"):
            js = window_scroll_map[direction]
            await page.evaluate(f"() => {{ {js} }}")
            return

        element = page.locator(selector)
        js = element_scroll_map[direction]
        await element.evaluate(f"el => {{ {js} }}")
