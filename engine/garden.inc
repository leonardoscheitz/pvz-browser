// SPDX-License-Identifier: LGPL-3.0-or-later
// Compiled in LawnApp.cpp against the pinned PvZ-Portable source.
#include <emscripten/emscripten.h>
#include "Lawn/SeedPacket.h"

// Sandbox is explicitly enabled by the web launcher BEFORE callMain, which
// runs with a fresh MEMFS /saves directory. Classic sessions never set it.
static bool gardenSandbox = false;
static int gardenSandboxStartLevel = 1;

static bool gardenFusion = false;

// Only the isolated mod session may activate this feature, before the engine starts.
extern "C" EMSCRIPTEN_KEEPALIVE int gardenFusionEnable()
{
    if (gLawnApp || !gardenSandbox) return 0;
    gardenFusion = true;
    return 1;
}

bool GardenFusionEnabled() { return gardenSandbox && gardenFusion; }
extern "C" EMSCRIPTEN_KEEPALIVE int gardenFusionActive() { return GardenFusionEnabled() ? 1 : 0; }


extern "C" EMSCRIPTEN_KEEPALIVE int gardenSandboxEnable(int level)
{
    if (gLawnApp || level < 1 || level > 50) return 0;
    gardenSandbox = true;
    gardenSandboxStartLevel = level;
    return 1;
}

static void GardenInitializeSandbox(LawnApp* app)
{
    if (!gardenSandbox) return;
    PlayerInfo* profile = app->mProfileMgr->AddProfile("Sandbox");
    if (!profile) profile = app->mProfileMgr->GetProfile("Sandbox");
    if (!profile) return;
    app->mPlayerInfo = profile;
    profile->mLevel = gardenSandboxStartLevel;
    profile->mFinishedAdventure = 2;
    profile->mCoins = 99999;
    profile->mHasUnlockedMinigames = 1;
    profile->mHasUnlockedPuzzleMode = 1;
    profile->mHasUnlockedSurvivalMode = 1;
    profile->mHasSeenUpsell = 1;
    profile->mNeedsMessageOnGameSelector = 0;
    profile->mNeedsMagicTacoReward = 0;
    profile->mHasSeenStinky = 1;
    const StoreItem unlocks[] = {
        STORE_ITEM_PLANT_GATLINGPEA, STORE_ITEM_PLANT_TWINSUNFLOWER,
        STORE_ITEM_PLANT_GLOOMSHROOM, STORE_ITEM_PLANT_CATTAIL,
        STORE_ITEM_PLANT_WINTERMELON, STORE_ITEM_PLANT_GOLD_MAGNET,
        STORE_ITEM_PLANT_SPIKEROCK, STORE_ITEM_PLANT_COBCANNON,
        STORE_ITEM_PLANT_IMITATER, STORE_ITEM_POOL_CLEANER,
        STORE_ITEM_ROOF_CLEANER, STORE_ITEM_PHONOGRAPH,
        STORE_ITEM_GARDENING_GLOVE, STORE_ITEM_MUSHROOM_GARDEN,
        STORE_ITEM_WHEEL_BARROW, STORE_ITEM_AQUARIUM_GARDEN,
        STORE_ITEM_TREE_OF_WISDOM
    };
    for (auto item : unlocks) profile->mPurchases[item] = 1;
    profile->mPurchases[STORE_ITEM_PACKET_UPGRADE] = 4;
    for (auto item : {STORE_ITEM_FERTILIZER, STORE_ITEM_BUG_SPRAY,
                      STORE_ITEM_CHOCOLATE, STORE_ITEM_TREE_FOOD})
        profile->mPurchases[item] = PURCHASE_COUNT_OFFSET + 5;
    // Same unlock-record convention as upstream's Full Unlock preview profile.
    for (int i = 1; i <= 100; ++i) {
        if (i != static_cast<int>(GameMode::GAMEMODE_TREE_OF_WISDOM) &&
            i != static_cast<int>(GameMode::GAMEMODE_SCARY_POTTER_ENDLESS) &&
            i != static_cast<int>(GameMode::GAMEMODE_PUZZLE_I_ZOMBIE_ENDLESS) &&
            i != static_cast<int>(GameMode::GAMEMODE_SURVIVAL_ENDLESS_STAGE_3))
            profile->mChallengeRecords[i - 1] = 20;
    }
    profile->mChallengeRecords[static_cast<int>(GameMode::GAMEMODE_TREE_OF_WISDOM) - 1] = 1;
    profile->SaveDetails();
    app->mProfileMgr->Save();
}

extern "C" EMSCRIPTEN_KEEPALIVE int gardenSandboxMenu()
{
    if (!gardenSandbox || !gLawnApp || !gLawnApp->mPlayerInfo ||
        gLawnApp->mGameScene != GameScenes::SCENE_MENU || gLawnApp->GetDialogCount() ||
        !gLawnApp->mGameSelector) return 0;
    auto* selector = gLawnApp->mGameSelector.get();
    if (selector->mSelectorState != SelectorAnimState::SELECTOR_IDLE ||
        selector->mStartingGame || selector->mLoading ||
        selector->mSlideCounter || selector->mX || selector->mY) return 0;
    return gLawnApp->mPlayerInfo->mLevel;
}

extern "C" EMSCRIPTEN_KEEPALIVE int gardenSandboxLevel(int level)
{
    if (!gardenSandboxMenu() || level < 1 || level > 50) return 0;
    gLawnApp->mPlayerInfo->mLevel = level;
    // NewGame handles the normal stage intro, seed chooser and board rules.
    gLawnApp->KillGameSelector();
    gLawnApp->PreNewGame(GameMode::GAMEMODE_ADVENTURE, false);
    return 1;
}

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
