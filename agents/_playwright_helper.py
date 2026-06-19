import os as _os


def find_chrome() -> str:
    base = str(_os.path.expanduser("~/Library/Caches/ms-playwright"))
    if not _os.path.isdir(base):
        return ""
    for d in _os.listdir(base):
        if d.startswith("chromium-") and "headless" not in d:
            for p in [
                _os.path.join(base, d, "chrome-mac-arm64",
                              "Google Chrome for Testing.app",
                              "Contents", "MacOS", "Google Chrome for Testing"),
                _os.path.join(base, d, "chrome-mac",
                              "Chromium.app", "Contents", "MacOS", "Chromium"),
            ]:
                if _os.path.isfile(p):
                    return p
    return ""


def play() -> "playwright.sync_api.Playwright":
    from playwright.sync_api import sync_playwright
    return sync_playwright().start()


def launch(pw):
    ch = find_chrome()
    return pw.chromium.launch(
        headless=True,
        executable_path=ch if ch else None,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
