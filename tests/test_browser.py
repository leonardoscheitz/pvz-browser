"""Browser regressions against the fully built GOTY site. Requires Playwright for Python."""
import functools
import gzip
import os
import struct
import threading
import time
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
MOUNT = "/saves/userdata/"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class WebGame(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        site = ROOT / "dist"
        if not (site / "index.html").is_file():
            raise RuntimeError("Build the site with python scripts/build.py first.")
        server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(site)))
        cls.addClassCleanup(server.server_close)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        cls.addClassCleanup(server.shutdown)
        cls.url = f"http://127.0.0.1:{server.server_port}/"
        pw = sync_playwright().start()
        cls.addClassCleanup(pw.stop)
        name = os.environ.get("PVZ_BROWSER", "chromium")
        cls.touch = name == "chromium"
        opts = {"headless": not (name == "firefox" and os.environ.get("DISPLAY"))}
        if name in ("chromium", "msedge"):
            opts["args"] = ["--enable-unsafe-swiftshader", "--use-angle=swiftshader"]
            if name == "msedge":
                opts["channel"] = "msedge"
            kind = pw.chromium
        else:
            kind = getattr(pw, name)
            if name == "firefox":
                opts["firefox_user_prefs"] = {"webgl.force-enabled": True}
        if os.environ.get("PVZ_BROWSER_EXECUTABLE"):
            opts["executable_path"] = os.environ["PVZ_BROWSER_EXECUTABLE"]
        cls.browser = kind.launch(**opts)
        cls.addClassCleanup(cls.browser.close)

    def setUp(self):
        self.context = self.browser.new_context(has_touch=self.touch, viewport={"width": 390, "height": 844})
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()

    def wait_engine(self):
        self.page.wait_for_function("""() => document.querySelector('#splash').hidden ||
            !document.querySelector('#panel').hidden""", timeout=60000)
        self.assertTrue(self.page.locator("#panel").is_hidden(), self.page.locator("#message").text_content())

    def choose(self, x, y):
        box = self.page.locator("#canvas").bounding_box()
        position = (box["x"] + x * box["width"] / 800, box["y"] + y * box["height"] / 600)
        if self.touch:
            self.page.touchscreen.tap(*position)
        else:
            self.page.mouse.click(*position)

    def read_file(self, name):
        return bytes(self.page.evaluate("p => Array.from(Module.FS.readFile(p))", MOUNT + name))

    def create_profile(self, url=None):
        self.page.goto(url or self.url)
        self.wait_engine()
        # The title button only becomes active after the game's own resource loading and intro.
        end = time.monotonic() + 65
        while not self.page.evaluate("Boolean(Module.wasmSoftKeyboardState?.active)"):
            self.assertLess(time.monotonic(), end, "The New User dialog did not open")
            self.choose(400, 550)
            self.page.wait_for_timeout(700)
        end = time.monotonic() + 12
        while True:
            self.choose(390, 312)
            self.page.wait_for_timeout(200)
            if self.page.evaluate("document.activeElement.id === 'pvz-soft-keyboard'"):
                break
            self.assertLess(time.monotonic(), end, "The profile editor did not receive focus")
        if self.touch:
            self.page.keyboard.insert_text("TouchQA")
            name = b"TouchQA"
        else:
            self.page.keyboard.type("DeskQA")
            name = b"DeskQA"
        self.page.wait_for_timeout(200)
        self.choose(280, 395)
        self.page.wait_for_function("Module.FS.analyzePath('/saves/userdata/users.dat').exists")
        return name

    def test_garden_menu_on_live_board(self):
        self.create_profile()
        trigger = self.page.locator("#garden-trigger")
        self.assertTrue(trigger.is_hidden())
        end = time.monotonic() + 60
        while trigger.is_hidden():
            self.assertLess(time.monotonic(), end, "Adventure did not reach the lawn")
            self.choose(545, 133)
            self.page.wait_for_timeout(700)

        def activate(locator):
            if self.touch:
                locator.tap()
            else:
                locator.click()

        def state(field):
            return self.page.evaluate("field => Module._gardenState(field)", field)

        activate(trigger)
        self.assertEqual(state(4), 1)
        sun = self.page.locator("#garden-sun")
        sun.fill("750")
        activate(sun.locator("..").get_by_role("button"))
        self.assertEqual(state(0), 750)
        coins = self.page.locator("#garden-coins")
        coins.fill("5050")
        activate(coins.locator("..").get_by_role("button"))
        self.assertEqual(state(1), 5050)
        self.assertEqual(struct.unpack_from("<I", self.read_file("user1.dat"), 8)[0], 505)
        activate(self.page.locator("#garden-free"))
        self.assertEqual(state(2), 1)
        self.page.locator("#garden-speed").select_option("2")
        self.assertEqual(state(3), 2)
        activate(self.page.locator("#garden-heal"))
        activate(self.page.locator("#garden-clear"))
        activate(self.page.locator("#garden-back"))
        self.page.wait_for_function("Module._gardenState(4) === 0")
        self.choose(118, 40)
        self.choose(88, 330)
        self.assertEqual(state(0), 750)
        activate(trigger)
        self.assertEqual(sun.input_value(), "750")
        self.page.keyboard.press("Escape")
        self.page.wait_for_function("!document.querySelector('#garden-menu').open && Module._gardenState(4) === 0")
        self.page.set_viewport_size({"width": 844, "height": 390})
        activate(trigger)
        card = self.page.locator(".garden-card").bounding_box()
        self.assertGreater(card["height"], 200)
        self.assertLessEqual(card["y"] + card["height"], 391)
        activate(self.page.locator("#garden-relaxed"))
        self.assertEqual(state(0), 9990)
        self.assertEqual(state(2), 1)
        activate(self.page.locator("#garden-normal"))
        self.assertEqual(state(2), 0)
        self.assertEqual(state(3), 1)
        activate(self.page.locator("#garden-back"))
        self.page.wait_for_function("Module._gardenState(4) === 0")


    def test_offline_and_save_tools(self):
        if not self.touch:
            self.skipTest("Chromium service-worker and download regression")
        import json
        self.create_profile()
        saved = self.read_file("users.dat")
        self.page.evaluate("() => new Promise((resolve,reject) => Module.FS.syncfs(false, e => e ? reject(e) : resolve()))")
        self.page.goto(self.url + "tools.html")
        with self.page.expect_download() as download:
            self.page.locator("#save-export").click(timeout=15000)
        backup = json.loads(Path(download.value.path()).read_text())
        self.assertEqual(backup["format"], "pvz-browser-goty-backup")
        import base64
        self.assertEqual(base64.b64decode(next(row["data"] for row in backup["records"]
                         if row["path"].endswith("/userdata/users.dat"))), saved)
        self.page.locator("#save-file").set_input_files({
            "name": "bad.json", "mimeType": "application/json", "buffer": b'{"version":1}'})
        self.page.locator("#save-import").click()
        self.page.get_by_text("Formato de backup incompatível.").wait_for()
        self.page.locator("#save-file").set_input_files({
            "name": "valid.json", "mimeType": "application/json", "buffer": json.dumps(backup).encode()})
        self.page.once("dialog", lambda dialog: dialog.accept())
        self.page.locator("#save-import").click()
        self.page.get_by_text("Backup restaurado.", exact=False).wait_for()
        with self.page.expect_download() as previous:
            self.page.locator("#save-previous").click()
        self.assertEqual(json.loads(Path(previous.value.path()).read_text())["records"], backup["records"])
        self.page.locator("#offline-prepare").click()
        self.page.get_by_text("Offline preparado.", exact=False).wait_for(timeout=120000)
        self.page.wait_for_function("navigator.serviceWorker.controller !== null")
        self.context.set_offline(True)
        try:
            self.page.goto(self.url)
            self.wait_engine()
            self.assertEqual(self.read_file("users.dat"), saved)
            self.page.goto(self.url + "tools.html")
            self.page.locator("#save-export").wait_for()
        finally:
            self.context.set_offline(False)

    def test_workshop_visual_assets(self):
        if os.environ.get("PVZ_BROWSER", "chromium") != "chromium":
            self.skipTest("Visual kit smoke test on Chromium")
        self.page.goto(self.url + "tools.html")
        self.assertTrue(self.page.locator(".pvz-logo").is_visible())
        self.assertEqual(self.page.locator(".pvz-panel-icon").count(), 3)
        self.assertEqual(self.page.locator(".pvz-panel-art span").count(), 27)
        self.assertTrue(self.page.locator("#save-export").is_visible())
        self.assertTrue(self.page.locator("#save-import").is_disabled())
        self.assertTrue(self.page.evaluate("""async () => {
            const elements = document.querySelectorAll(".pvz-panel-art span, .pvz-panel-icon, #save-export");
            return (await Promise.all([...elements].map(async el => {
                const style = getComputedStyle(el);
                const match = style.backgroundImage.match(/url\\(["']?(.*?)["']?\\)/);
                if (!match || !/\\.(png|jpe?g)$/i.test(new URL(match[1], location.href).pathname)) return false;
                const img = new Image();
                img.src = match[1];
                try { await img.decode(); } catch { return false; }
                return img.naturalWidth > 0;
            }))).every(Boolean);
        }"""))
        for width, height in [(320,568),(390,844),(844,390),(1280,800)]:
            self.page.set_viewport_size({"width": width, "height": height})
            self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
            self.assertGreaterEqual(self.page.locator("#save-export").bounding_box()["height"], 44)
            if os.environ.get("PVZ_UI_SCREENSHOTS"):
                folder = Path(os.environ["PVZ_UI_SCREENSHOTS"])
                folder.mkdir(parents=True, exist_ok=True)
                self.page.screenshot(path=str(folder / f"workshop-{width}x{height}.png"), full_page=True)

    def test_sandbox_never_mounts_campaign(self):
        if os.environ.get("PVZ_BROWSER", "chromium") != "chromium":
            self.skipTest("Sandbox isolation covered on Chromium")
        self.create_profile()
        self.page.evaluate("""() => new Promise((resolve, reject) =>
            Module.FS.syncfs(false, error => error ? reject(error) : resolve()))""")
        before = self.read_file("users.dat")
        self.page.close()
        self.page = self.context.new_page()
        self.page.goto(self.url + "?sandbox=1")
        self.wait_engine()
        self.assertTrue(self.page.locator("#sandbox-indicator").is_visible())
        self.assertFalse(self.page.evaluate("Module.FS.analyzePath('/pvz-browser-goty').exists"))
        self.assertTrue(self.page.evaluate("Module.FS.analyzePath('/saves/userdata/users.dat').exists"))
        self.assertNotEqual(before, self.read_file("users.dat"))
        # The sandbox profile is generated in memory, never loaded from IDBFS.
        # Write a deliberately different file in the isolated filesystem.
        self.page.evaluate("""() => {
            Module.FS.mkdirTree('/saves/userdata');
            Module.FS.writeFile('/saves/userdata/users.dat', new Uint8Array([1,2,3]));
        }""")
        self.page.close()
        self.page = self.context.new_page()
        self.page.goto(self.url)
        self.wait_engine()
        self.assertTrue(self.page.locator("#sandbox-indicator").is_hidden())
        self.assertEqual(before, self.read_file("users.dat"))

    def test_advanced_modifiers(self):
        if not os.environ.get("PVZ_REQUIRE_ADVANCED"):
            self.skipTest("Requires newly compiled native extension")
        self.create_profile()
        trigger = self.page.locator("#garden-trigger")
        end = time.monotonic() + 60
        while trigger.is_hidden():
            self.assertLess(time.monotonic(), end, "Adventure did not reach the lawn")
            self.choose(545, 133)
            self.page.wait_for_timeout(700)
        trigger.click()
        state = lambda field: self.page.evaluate("f => Module._gardenState(f)", field)
        self.assertEqual(state(7), 0)
        self.assertEqual(state(8), 0)
        self.page.locator("#garden-infinite").check()
        self.page.locator("#garden-recharge").check()
        self.assertEqual(state(7), 1)
        self.assertEqual(state(8), 1)
        self.page.locator("#garden-chill").click()
        self.page.locator("#garden-back").click()
        self.page.wait_for_function("Module._gardenState(4) === 0")
        # Spending sun should be replenished by the native update loop.
        self.page.evaluate("Module._gardenChange(0, 250)")
        self.page.wait_for_function("Module._gardenState(0) === 9990")
        trigger.click()
        self.page.locator("#garden-normal").click()
        self.assertEqual(state(7), 0)
        self.assertEqual(state(8), 0)
        self.assertEqual(state(2), 0)
        self.assertEqual(state(3), 1)
        self.page.locator("#garden-back").click()
        self.page.wait_for_function("Module._gardenState(4) === 0")
        self.page.evaluate("Module._gardenChange(0, 250)")
        self.page.wait_for_timeout(250)
        self.assertEqual(state(0), 250)

    def test_new_profile_and_exclusive_tab(self):
        name = self.create_profile()
        saved = self.read_file("users.dat")
        self.assertEqual(int.from_bytes(saved[6:8], "little"), len(name))
        self.assertEqual(saved[8:8 + len(name)], name)
        self.page.set_viewport_size({"width": 844, "height": 390})
        box = self.page.locator("#canvas").bounding_box()
        self.assertAlmostEqual(box["width"] / box["height"], 4 / 3, places=2)

        second = self.context.new_page()
        downloads = []
        second.on("request", lambda req: downloads.append(req.url))
        second.goto(self.url)
        second.locator("#message").get_by_text("outra aba", exact=False).wait_for()
        self.assertFalse(any(url.endswith(".bin") for url in downloads), downloads)
        self.page.close()
        self.page = second
        self.page.locator("#retry").click()
        self.wait_engine()
        self.assertEqual(self.read_file("users.dat"), saved)

    def test_migrate_latest_profile_without_database_enumeration(self):
        # Synthetic GOTY v14 directory and v12 level-one player. No player files are bundled.
        directory = struct.pack("<IHH2sII", 14, 1, 2, b"QA", 1, 1)
        details = struct.pack("<IIII", 12, 1, 0, 0) + bytes((100 + 80 + 21) * 4 + 40 + 26)
        profile = {"users.dat": list(directory), "user1.dat": list(details)}
        self.context.add_init_script("Object.defineProperty(indexedDB, 'databases', {value: undefined})")
        self.page.goto(self.url + "README.txt")
        self.page.evaluate("""async files => {
          for (const [index, mount] of ['/root/key/pvz-goty','/d_drive/key/pvz-goty'].entries()) {
            const db = await new Promise((resolve,reject) => {
              const req = indexedDB.open(mount, 21);
              req.onupgradeneeded = () => req.result.createObjectStore('FILE_DATA');
              req.onsuccess = () => resolve(req.result);
              req.onerror = () => reject(req.error);
            });
            const folder = mount + '/userdata/';
            const tx = db.transaction('FILE_DATA','readwrite');
            const store = tx.objectStore('FILE_DATA');
            for (const [name, bytes] of Object.entries(files)) {
              const contents = Uint8Array.from(bytes);
              // Only progress changed on the latest install. The older profile list has a newer date.
              if (index === 0 && name === 'user1.dat') contents[4] = 5;
              const time = index === 0 ? 200 : (name === 'users.dat' ? 100 : 300);
              store.put({contents, timestamp:new Date(time), mode:33188}, folder+name);
            }
            store.put({contents:new Uint8Array([1]), timestamp:new Date(400)},folder+'game1_0.dat');
            await new Promise((resolve,reject) => {tx.oncomplete=resolve;tx.onabort=()=>reject(tx.error);});
            db.close();
          }
        }""", profile)
        self.page.goto(self.url)
        self.wait_engine()
        self.assertIn("recuperado", self.page.locator("#notice").inner_text())
        for name, expected in profile.items():
            self.assertEqual(self.read_file(name), bytes(expected))
        self.assertFalse(self.page.evaluate("Module.FS.analyzePath('/saves/userdata/game1_0.dat').exists"))
        self.page.reload()
        self.wait_engine()
        self.assertTrue(self.page.locator("#notice").is_hidden())
        self.assertEqual(self.read_file("user1.dat"), bytes(profile["user1.dat"]))

    def test_incomplete_part_releases_profile(self):
        self.page.route("**/lawn-*.bin", lambda route: route.fulfill(
            content_type="application/octet-stream", body=gzip.compress(b"short")), times=1)
        self.page.goto(self.url)
        self.page.locator("#panel:not([hidden])").wait_for()
        self.assertIn("incompleto", self.page.locator("#message").text_content())
        failed_page = self.page
        self.page = self.context.new_page()
        self.page.goto(self.url)
        self.wait_engine()
        self.page.close()
        self.page = failed_page
        self.page.locator("#retry").click()
        self.wait_engine()


if __name__ == "__main__":
    unittest.main(verbosity=2)
