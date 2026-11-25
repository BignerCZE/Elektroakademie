import os

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright


class LandingVideoBrowserTests(StaticLiveServerTestCase):
    def test_preview_and_player_fit_around_breakpoints(self):
        widths = {320, 360, 390, 414, 667, 844, 1024, 1280, 1366, 1440, 1920}
        for breakpoint in (420, 768, 900, 1200):
            widths.update(range(breakpoint - 8, breakpoint + 9))
        sizes = [(width, 768) for width in sorted(widths)]
        sizes += [(320, 568), (390, 844), (667, 375), (844, 390), (1024, 500),
                  (1201, 480), (1366, 768), (1920, 540)]
        with sync_playwright() as playwright:
            options = {}
            if os.getenv("CHROMIUM_EXECUTABLE_PATH"):
                options["executable_path"] = os.environ["CHROMIUM_EXECUTABLE_PATH"]
            browser = playwright.chromium.launch(**options)
            page = browser.new_page()
            page.route("https://www.youtube-nocookie.com/**", lambda route: route.fulfill(
                content_type="text/html", body="<title>Test player</title>",
            ))
            page.goto(self.live_server_url)
            page.locator('[data-cookie-choice="settings"]').click()
            page.locator("#cookie-media").check()
            page.locator('[data-cookie-choice="save"]').click()
            page.locator("#cookie-banner").wait_for(state="hidden")
            preview = page.locator(".video-trigger")
            self.assertTrue(page.locator(".video-thumbnail").evaluate("img => img.naturalWidth > 0"))
            for index, (width, height) in enumerate(sizes):
                with self.subTest(width=width, height=height):
                    page.set_viewport_size({"width": width, "height": height})
                    content, thumbnail = page.evaluate("""
                        () => ['.hero-content', '.video-trigger'].map(selector =>
                            document.querySelector(selector).getBoundingClientRect().toJSON())
                    """)
                    self.assertTrue(
                        thumbnail["x"] >= content["x"] + content["width"] - 1
                        or thumbnail["y"] >= content["y"] + content["height"] - 1,
                        f"Náhled {thumbnail} zasahuje do textu {content}",
                    )
                    self.assertGreaterEqual(thumbnail["x"], -1)
                    self.assertLessEqual(thumbnail["x"] + thumbnail["width"], width + 1)
                    self.assertTrue(page.evaluate("""
                        () => [document.documentElement, document.querySelector('.page-scroll'),
                               document.querySelector('.hero-content')]
                            .every(el => el.scrollWidth <= el.clientWidth + 1)
                    """))
                    # Exercise real pointer interaction at representative sizes.
                    if index % 10 == 0 or (width, height) in sizes[-8:]:
                        preview.click()
                    else:
                        preview.evaluate("button => button.click()")
                    try:
                        self.assertEqual(page.locator("#video-modal iframe").count(), 1)
                        player = page.locator(".video-modal-frame").bounding_box()
                        close = page.locator("#video-modal-close")
                        button = close.bounding_box()
                        self.assertGreaterEqual(button["y"], 0)
                        self.assertLessEqual(player["y"] + player["height"], height + 1)
                        self.assertLessEqual(player["x"] + player["width"], width + 1)
                        if index % 10 == 0 or (width, height) in sizes[-8:]:
                            close.click()
                            self.assertEqual(page.locator("#video-modal iframe").count(), 0)
                    finally:
                        page.keyboard.press("Escape")
            browser.close()
