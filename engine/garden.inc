// SPDX-License-Identifier: LGPL-3.0-or-later
// Compiled in LawnApp.cpp against the pinned PvZ-Portable source.
#include <emscripten/emscripten.h>

static Board* GardenBoard()
{
    if (!gLawnApp || !gLawnApp->mPlayerInfo || gLawnApp->GetDialogCount() ||
        gLawnApp->mGameScene != GameScenes::SCENE_PLAYING)
        return nullptr;
    return gLawnApp->mBoard;
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
        case 2: gLawnApp->mEasyPlantingCheat = value != 0; break;
        case 3:
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
        default: return 0;
    }
    return 1;
}
