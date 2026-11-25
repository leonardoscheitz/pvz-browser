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
replace_once("void LawnApp::Init()\n{",
             "static void GardenInitializeSandbox(LawnApp* app);\n\nvoid LawnApp::Init()\n{")
replace_once("\tmMaxExecutions = GetInteger(\"MaxExecutions\", 0);",
             "\tGardenInitializeSandbox(this);\n\tmMaxExecutions = GetInteger(\"MaxExecutions\", 0);")
extension = Path(__file__).resolve().parents[1] / "engine" / "garden.inc"
source.write_text(text + "\n" + extension.read_text(encoding="utf-8"), encoding="utf-8")

# Suspend the existing wave scheduler without touching its counters.
board_path = upstream / "src" / "Lawn" / "Board.cpp"
board = board_path.read_text(encoding="utf-8")
anchor = "void Board::UpdateZombieSpawning()\n{"
if board.count(anchor) != 1:
    raise RuntimeError("Pinned wave scheduler mismatch")
board = board.replace(anchor, "extern bool GardenEditorWavesFrozen();\n\n" + anchor + "\n\tif (GardenEditorWavesFrozen()) return;", 1)
board_path.write_text(board, encoding="utf-8")
