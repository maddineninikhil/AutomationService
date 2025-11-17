from drivers.playwright_driver import PlaywrightDriver
from pipelines.handler_pipeline import HandlerPipeline

actions = [
    {"action": "goto", "value": "https://www.ucr.gov"},
    {"action": "wait_for", "selector": "input.MuiInput-input[type=tel]"},
    {"action": "input", "selector": "input.MuiInput-input[type=tel]", "value": "64"},
    {"action": "click", "selector": "button[aria-label=\"View Privacy Policy\"]"},
    {"action": "click", "selector": "div.MuiDialog-paper:has-text(\"Privacy Policy\") button[aria-label=\"Close\"]"},
    {"action": "click", "selector": "button[aria-label=\"View Terms & Conditions\"]"},
    {"action": "click",
     "selector": "div.MuiDialog-paper:has-text(\"Terms & Conditions\") button[aria-label=\"Close\"]"},
    {"action": "click", "selector": "input[name=agreement]"},
    {"action": "click", "selector": "button[aria-label=\"Submit\"]"},

]

driver = PlaywrightDriver(headless=False)
pipeline = HandlerPipeline()

try:
    pipeline.execute(actions, driver)
finally:
    driver.close()
