import os
import json
import pytest
import bot

# Sample HTML to simulate applications page
SAMPLE_HTML = "<html><head><title>Applications</title></head><body id='main-content'>Content</body></html>"

class DummyElement:
    def send_keys(self, value):
        pass
    def click(self):
        pass

class DummyWait:
    def __init__(self, driver, timeout):
        pass
    def until(self, condition):
        return DummyElement()

class DummyDriver:
    def __init__(self):
        self.page_source = SAMPLE_HTML
    def get(self, url):
        pass
    def quit(self):
        pass

@pytest.fixture(autouse=True)
def setup_tmp_dir(tmp_path, monkeypatch):
    # Switch to temporary directory for file creation
    monkeypatch.chdir(tmp_path)
    # Create a valid credentials.json
    creds = {"username": "user", "password": "pass"}
    with open("credentials.json", "w") as f:
        json.dump(creds, f)
    yield

def test_load_credentials():
    username, password = bot.load_credentials()
    assert username == "user"
    assert password == "pass"

def test_run_bot_writes_html(monkeypatch, tmp_path):
    # Monkeypatch init_driver and waits/conditions to avoid real browser
    monkeypatch.setattr(bot, "init_driver", lambda: DummyDriver())
    monkeypatch.setattr(bot, "WebDriverWait", DummyWait)
    monkeypatch.setattr(bot.EC, "element_to_be_clickable", lambda locator: True)
    monkeypatch.setattr(bot.EC, "presence_of_element_located", lambda locator: True)

    # Run the bot
    bot.run_bot()

    # Verify that application_view.html was created with SAMPLE_HTML
    out_file = tmp_path / "application_view.html"
    assert out_file.exists(), "application_view.html was not created"
    content = out_file.read_text(encoding="utf-8")
    assert "<title>Applications</title>" in content
    assert "id='main-content'" in content
