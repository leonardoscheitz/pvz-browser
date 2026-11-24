// SPDX-License-Identifier: LGPL-3.0-or-later
// Compiled in LawnApp.cpp against the pinned PvZ-Portable source.
#include <emscripten/emscripten.h>
#include "Lawn/SeedPacket.h"

// Session-only modifiers, never serialized. Reset before destroying a board.
static bool gardenInfiniteSun = false;
static bool gardenInstantRecharge = false;
static bool gardenTouchedFree = false;
static bool gardenTouchedSpeed = false;

static Board* GardenBoard()
{
    if (!gLawnApp || !gLawnApp->mPlayerInfo || gLawnApp->GetDialogCount() ||
        gLawnApp->mGameScene != GameScenes::SCENE_PLAYING)
        return nullptr;
    return gLawnApp->mBoard;
}

// Only Adventure is enabled for continuous modifiers until special modes are tested.
static bool GardenAdvancedAvailable(Board* board)
{
    return board && gLawnApp->mGameMode == GameMode::GAMEMODE_ADVENTURE &&
        !board->mLevelComplete && board->mBoardFadeOutCounter < 0 &&
        !board->HasConveyorBeltSeedBank() && !gLawnApp->IsSlotMachineLevel();
}

static void GardenResetModifiers()
{
    gardenInfiniteSun = false;
    gardenInstantRecharge = false;
    if (gardenTouchedFree) gLawnApp->mEasyPlantingCheat = false;
    if (gardenTouchedSpeed) {
        if (gFastMo) gLawnApp->ToggleFastMo();
        if (gSlowMo) gLawnApp->ToggleSlowMo();
    }
    gardenTouchedFree = false;
    gardenTouchedSpeed = false;
}

static void GardenTick()
{
    if (!gardenInfiniteSun && !gardenInstantRecharge) return;
    Board* board = GardenBoard();
    if (!GardenAdvancedAvailable(board) || board->mPaused) return;
    if (gardenInfiniteSun) board->mSunMoney = 9990;
    if (gardenInstantRecharge && board->mSeedBank) board->mSeedBank->RefreshAllPackets();
}

extern "C" EMSCRIPTEN_KEEPALIVE int gardenState(int field)
{
    Board* board = GardenBoard();
    if (!board) return -1;
    switch (field) {
        case 0: return board->mSunMoney;
        case 1: return gLawnApp->mPlayerInfo->mCoins * 10;
        case 2: return gLawnApp->mEasyPlantingCheat;
        case 3: return gFastMo ? 2 : gSlowMo ? 0 : 1;
        case 4: return board->mPaused;
        case 7: return GardenAdvancedAvailable(board) ? int(gardenInfiniteSun) : -1;
        case 8: return GardenAdvancedAvailable(board) ? int(gardenInstantRecharge) : -1;
        case 9: return GardenAdvancedAvailable(board) ? 1 : -1;
        default: return -1;
    }
}

extern "C" EMSCRIPTEN_KEEPALIVE int gardenChange(int field, int value)
{
    Board* board = GardenBoard();
    if (!board) return 0;
    switch (field) {
        case 0: board->mSunMoney = std::clamp(value, 0, 9990); break;
        case 1: {
            auto* player = gLawnApp->mPlayerInfo;
            player->AddCoins(std::clamp(value, 0, 999990) / 10 - player->mCoins);
            gLawnApp->WriteCurrentUserConfig();
            break;
        }
        case 2: gardenTouchedFree = true; gLawnApp->mEasyPlantingCheat = value != 0; break;
        case 3:
            gardenTouchedSpeed = true;
            if (gFastMo) gLawnApp->ToggleFastMo();
            if (gSlowMo) gLawnApp->ToggleSlowMo();
            if (value == 2) gLawnApp->ToggleFastMo();
            if (value == 0) gLawnApp->ToggleSlowMo();
            break;
        case 4: board->Pause(value != 0); break;
        case 5:
            for (Plant* plant : board->mPlants)
                if (!plant->mDead && plant->mPlantHealth > 0) plant->mPlantHealth = plant->mPlantMaxHealth;
            break;
        case 6: board->RemoveAllZombies(); break;
        case 7:
            if (!GardenAdvancedAvailable(board)) return 0;
            gardenInfiniteSun = value != 0;
            if (gardenInfiniteSun) board->mSunMoney = 9990;
            break;
        case 8:
            if (!GardenAdvancedAvailable(board)) return 0;
            gardenInstantRecharge = value != 0;
            if (gardenInstantRecharge && board->mSeedBank) board->mSeedBank->RefreshAllPackets();
            break;
        case 9:
            if (!GardenAdvancedAvailable(board)) return 0;
            for (Zombie* zombie : board->mZombies)
                if (!zombie->mDead && zombie->mBodyHealth > 0) zombie->ApplyChill(false);
            break;
        default: return 0;
    }
    return 1;
}
