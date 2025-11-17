from playwright.sync_api import sync_playwright

class PlaywrightDriver:
    def __init__(
        self,
        headless=False,
        proxy=None,
        executable_path=None,
        use_cdp=False,
        cdp_url=None,
    ):
        self.playwright = sync_playwright().start()

        # --- CDP Mode -------------------------------------------------
        if use_cdp:
            if not cdp_url:
                raise ValueError("CDP mode requires a cdp_url")
            self.browser = self.playwright.chromium.connect_over_cdp(cdp_url)
            context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
            self.page = context.new_page()
            return

        # --- Launch Browser -------------------------------------------
        launch_args = {"headless": headless}

        if proxy:
            launch_args["proxy"] = proxy
        if executable_path:
            launch_args["executable_path"] = executable_path

        self.browser = self.playwright.chromium.launch(**launch_args)
        self.page = self.browser.new_page()

    # --- Actions -------------------------------------------------------
    def goto(self, url):
        self.page.goto(url)

    def input(self, selector, value):
        self.page.fill(selector, value)

    def select(self, selector, value):
        self.page.select_option(selector, value)

    def click(self, selector):
        self.page.click(selector)

    def wait_for(self, selector, timeout=30000, state="visible"):
        self.page.wait_for_selector(selector, timeout=timeout, state=state)

    # --- Cleanup -------------------------------------------------------
    def close(self):
        try:
            self.browser.close()
        finally:
            self.playwright.stop()
