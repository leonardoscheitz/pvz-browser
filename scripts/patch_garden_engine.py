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

# Patch the pinned board at exact, verified anchors. Fail on upstream drift.
board_path = upstream / "src" / "Lawn" / "Board.cpp"
board = board_path.read_text(encoding="utf-8")
for old, new in [["void Board::MouseDownWithPlant(int x, int y, int theClickCount)\n{","extern bool GardenFusionEnabled();\n\n// Fusion recipes use existing native plant types and sprites. No copied Fusion assets.\nstatic SeedType GardenFusionResult(Board* board, Plant* base, SeedType incoming)\n{\n    if (!GardenFusionEnabled() || !base || base->mDead || base->mPlantHealth <= 0 ||\n        base->mOnBungeeState == PlantOnBungeeState::GETTING_GRABBED_BY_BUNGEE ||\n        board->mApp->mGameMode != GameMode::GAMEMODE_ADVENTURE ||\n        board->mApp->mGameScene != GameScenes::SCENE_PLAYING ||\n        board->mLevelComplete || board->mBoardFadeOutCounter >= 0 ||\n        board->HasConveyorBeltSeedBank() || board->mApp->IsWallnutBowlingLevel() ||\n        board->mApp->IsSlotMachineLevel() ||\n        !board->mCursorObject || board->mCursorObject->mCursorType != CursorType::CURSOR_TYPE_PLANT_FROM_BANK ||\n        board->mCursorObject->mType != incoming)\n        return SeedType::SEED_NONE;\n    const SeedType planted = base->mSeedType;\n    if (planted == SeedType::SEED_MELONPULT && incoming == SeedType::SEED_SNOWPEA)\n        return SeedType::SEED_WINTERMELON;\n    if (planted != incoming) return SeedType::SEED_NONE;\n    switch (incoming) {\n        case SeedType::SEED_PEASHOOTER: return SeedType::SEED_REPEATER;\n        case SeedType::SEED_REPEATER: return SeedType::SEED_GATLINGPEA;\n        case SeedType::SEED_SUNFLOWER: return SeedType::SEED_TWINSUNFLOWER;\n        case SeedType::SEED_WALLNUT: return SeedType::SEED_TALLNUT;\n        case SeedType::SEED_FUMESHROOM: return SeedType::SEED_GLOOMSHROOM;\n        case SeedType::SEED_SPIKEWEED: return SeedType::SEED_SPIKEROCK;\n        default: return SeedType::SEED_NONE;\n    }\n}\n\nvoid Board::MouseDownWithPlant(int x, int y, int theClickCount)\n{"],["\tif (aNormalPlant && aNormalPlant->IsUpgradableTo(aPlantingSeedType))\n\t{\n\t\tif (aPlantingSeedType == SeedType::SEED_GLOOMSHROOM)","\tSeedType aFusionSeedType = GardenFusionResult(this, aNormalPlant, aPlantingSeedType);\n\tif (aNormalPlant && (aFusionSeedType != SeedType::SEED_NONE || aNormalPlant->IsUpgradableTo(aPlantingSeedType)))\n\t{\n\t\tif (aPlantingSeedType == SeedType::SEED_GLOOMSHROOM || aFusionSeedType == SeedType::SEED_GLOOMSHROOM)"],["\t\tPlant* aPlant = AddPlant(aGridX, aGridY, mCursorObject->mType, mCursorObject->mImitaterType);\n\t\tif (aIsAwake)","\t\tPlant* aPlant = aFusionSeedType == SeedType::SEED_NONE\n\t\t\t? AddPlant(aGridX, aGridY, mCursorObject->mType, mCursorObject->mImitaterType)\n\t\t\t: AddPlant(aGridX, aGridY, aFusionSeedType, SeedType::SEED_NONE);\n\t\tif (aIsAwake)"],["\t\t// wall-nut first aid\n\t\tif ((theSeedType == SeedType::SEED_WALLNUT || theSeedType == SeedType::SEED_TALLNUT) && aAidPurchased)","\t\tif (GardenFusionResult(this, aNormalPlant, theSeedType) != SeedType::SEED_NONE)\n\t\t\treturn PlantingReason::PLANTING_OK;\n\n\t\t// wall-nut first aid\n\t\tif ((theSeedType == SeedType::SEED_WALLNUT || theSeedType == SeedType::SEED_TALLNUT) && aAidPurchased)"],["\tif ((aPlantingSeedType == SeedType::SEED_WALLNUT || aPlantingSeedType == SeedType::SEED_TALLNUT) && aNormalPlant)","\tif (aFusionSeedType == SeedType::SEED_NONE && (aPlantingSeedType == SeedType::SEED_WALLNUT || aPlantingSeedType == SeedType::SEED_TALLNUT) && aNormalPlant)"]]:
    if board.count(old) != 1:
        raise RuntimeError("Pinned fusion source mismatch: " + old[:80])
    board = board.replace(old, new, 1)
board_path.write_text(board, encoding="utf-8")
