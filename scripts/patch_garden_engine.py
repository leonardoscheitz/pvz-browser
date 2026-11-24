"""Apply the optional garden extension to the pinned upstream source."""
from pathlib import Path
import sys

upstream = Path(sys.argv[1])
source = upstream / "src" / "LawnApp.cpp"
text = source.read_text(encoding="utf-8")

def replace_once(old, new):
    global text
    if text.count(old) != 1:
        raise RuntimeError("Pinned source mismatch: " + old[:80])
    text = text.replace(old, new, 1)

replace_once("void LawnApp::KillBoard()\n{",
             "static void GardenResetModifiers();\n\nvoid LawnApp::KillBoard()\n{\n\tGardenResetModifiers();")
replace_once("void LawnApp::UpdateFrames()\n{",
             "static void GardenTick();\n\nvoid LawnApp::UpdateFrames()\n{")
replace_once("\t\tSexyApp::UpdateFrames();\n\n\t\tmMusic->MusicUpdate();",
             "\t\tGardenTick();\n\t\tSexyApp::UpdateFrames();\n\n\t\tmMusic->MusicUpdate();")
extension = Path(__file__).resolve().parents[1] / "engine" / "garden.inc"
source.write_text(text + "\n" + extension.read_text(encoding="utf-8"), encoding="utf-8")
