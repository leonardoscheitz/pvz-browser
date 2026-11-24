"""Open the built game in Apple's installed Safari and reload a disposable profile."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
from threading import Thread
from time import monotonic, sleep

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait


def run(driver, url):
    driver.get(url)
    wait = WebDriverWait(driver, 60)
    wait.until(lambda d: d.execute_script("return document.querySelector('#splash').hidden"))
    canvas = driver.find_element(By.ID, "canvas")
    mobile = driver.capabilities.get("platformName", "").lower() == "ios"
    if mobile:
        driver.execute_script("window.testTouchCount = 0; document.addEventListener('touchstart', () => testTouchCount++, {passive:true})")
        initial_height = driver.execute_script("return visualViewport.height")

    def click(x, y):
        if mobile:
            left, top, width, height = driver.execute_script("""
                const r = arguments[0].getBoundingClientRect(); return [r.left,r.top,r.width,r.height];
            """, canvas)
            actions = ActionBuilder(driver, mouse=PointerInput("touch", "finger"))
            actions.pointer_action.move_to_location(round(left + x * width / 800), round(top + y * height / 600))
            actions.pointer_action.pointer_down()
            actions.pointer_action.pause(0.08)
            actions.pointer_action.pointer_up()
            actions.perform()
            return
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
    if mobile:
        touches, height = driver.execute_script("return [testTouchCount, visualViewport.height]")
        if touches < 1:
            raise AssertionError("Safari did not receive touch events")
        print("iOS touches", touches, "viewport before and during text entry", initial_height, height, flush=True)
        ActionChains(driver).send_keys(Keys.ENTER).perform()
    else:
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
    if mobile:
        # Use real touchscreen actions for every button, including the opener.
        def tap_element(element):
            x, y = driver.execute_script("""
                arguments[0].scrollIntoView({block: 'nearest'});
                const r = arguments[0].getBoundingClientRect();
                return [r.x + r.width / 2, r.y + r.height / 2];
            """, element)
            pointer = ActionBuilder(driver, mouse=PointerInput("touch", "finger"))
            pointer.pointer_action.move_to_location(round(x), round(y))
            pointer.pointer_action.pointer_down()
            pointer.pointer_action.pause(.08)
            pointer.pointer_action.pointer_up()
            pointer.perform()

        trigger = driver.find_element(By.ID, "garden-trigger")
        end = monotonic() + 60
        while not trigger.is_displayed():
            if monotonic() >= end:
                raise TimeoutError("Adventure did not reach the lawn")
            click(545, 133)
            sleep(.7)
        for turn in range(2):
            tap_element(trigger)
            wait.until(lambda d: d.execute_script("return document.querySelector('#garden-menu').open && Module._gardenState(4) === 1"))
            free = driver.find_element(By.ID, "garden-free")
            tap_element(free)
            wait.until(lambda d: d.execute_script("return Module._gardenState(2)") == (1 - turn))
            tap_element(driver.find_element(By.ID, "garden-back"))
            wait.until(lambda d: d.execute_script("return !document.querySelector('#garden-menu').open && Module._gardenState(4) === 0"))
        print("iOS Safari: two touch cycles opened the garden, changed planting and resumed the game", flush=True)
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
            options = webdriver.SafariOptions()
            if simulator := os.environ.get("PVZ_IOS_SIMULATOR"):
                options.set_capability("platformName", "iOS")
                options.set_capability("safari:useSimulator", True)
                options.set_capability("safari:deviceUDID", simulator)
            with webdriver.Safari(options=options) as browser:
                run(browser, f"http://127.0.0.1:{server.server_port}/")
        finally:
            server.shutdown()
