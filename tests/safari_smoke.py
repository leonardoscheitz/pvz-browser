"""Open the built game in Apple's installed Safari and reload a disposable profile."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from time import monotonic, sleep

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


def run(driver, url):
    driver.get(url)
    wait = WebDriverWait(driver, 60)
    wait.until(lambda d: d.execute_script("return document.querySelector('#splash').hidden"))
    canvas = driver.find_element(By.ID, "canvas")

    def click(x, y):
        size = canvas.size
        dx = round((x / 800 - 0.5) * size["width"])
        dy = round((y / 600 - 0.5) * size["height"])
        ActionChains(driver).move_to_element_with_offset(canvas, dx, dy).click().perform()

    end = monotonic() + 65
    while not driver.execute_script("return Boolean(window.Module?.wasmSoftKeyboardState?.active)"):
        if monotonic() >= end:
            raise TimeoutError("Safari did not open the profile dialog")
        click(400, 550)
        sleep(0.7)
    click(390, 312)
    wait.until(lambda d: d.execute_script("return document.activeElement.id === 'pvz-soft-keyboard'"))
    # Send physical keystrokes to the focused editor. Element.send_keys asks Safari
    # to click the transparent keyboard bridge, which intentionally ignores pointer events.
    ActionChains(driver).send_keys("Garden").perform()
    sleep(0.2)
    click(280, 395)
    has_profile = "return window.Module?.FS?.analyzePath('/saves/userdata/users.dat').exists"
    wait.until(lambda d: d.execute_script(has_profile))
    read = "return Array.from(Module.FS.readFile('/saves/userdata/users.dat'))"
    before = bytes(driver.execute_script(read))
    if before[6:14] != b"\x06\x00Garden":
        raise AssertionError("Safari did not store the entered profile name")
    # Wait for IDBFS autoPersist to finish its normal background transaction.
    wait.until(lambda d: d.execute_async_script("""
      const done = arguments[0], req = indexedDB.open('/pvz-browser-goty');
      req.onsuccess = () => {
        const db = req.result;
        const get = db.transaction('FILE_DATA').objectStore('FILE_DATA').get('/pvz-browser-goty/userdata/users.dat');
        get.onsuccess = () => {db.close();done(!!get.result);};
        get.onerror = () => {db.close();done(false);};
      };
      req.onerror = () => done(false);
    """))
    driver.refresh()
    wait.until(lambda d: d.execute_script(has_profile))
    if before != bytes(driver.execute_script(read)):
        raise AssertionError("Safari did not restore the saved profile")
    print("Safari", driver.capabilities.get("browserVersion"), "profile creation and persistence OK")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    with ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(root / "dist"))) as server:
        Thread(target=server.serve_forever, daemon=True).start()
        try:
            with webdriver.Safari() as browser:
                run(browser, f"http://127.0.0.1:{server.server_port}/")
        finally:
            server.shutdown()
