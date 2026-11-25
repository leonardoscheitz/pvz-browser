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

// Read-only sandbox diagnostics for browser regression tests and future editors.
// Returns the native seed at a cell, or -1 when empty/unavailable.
extern "C" EMSCRIPTEN_KEEPALIVE int gardenInspectPlant(int col, int row)
{
    Board* board = GardenBoard();
    if (!gardenSandbox || !GardenAdvancedAvailable(board) ||
        col < 0 || col >= MAX_GRID_SIZE_X || row < 0 || row >= MAX_GRID_SIZE_Y)
        return -1;
    Plant* plant = board->GetTopPlantAt(col, row, PlantPriority::TOPPLANT_ONLY_NORMAL_POSITION);
    return plant && !plant->mDead ? int(plant->mSeedType) : -1;
}

extern "C" EMSCRIPTEN_KEEPALIVE int gardenInspectPacket(int seed)
{
    Board* board = GardenBoard();
    if (!gardenSandbox || !GardenAdvancedAvailable(board) || !board->mSeedBank) return -1;
    for (int i = 0; i < board->mSeedBank->mNumPackets; ++i) {
        SeedPacket& packet = board->mSeedBank->mSeedPackets[i];
        if (int(packet.mPacketType) == seed && packet.CanPickUp())
            return (packet.mX + packet.mOffsetX + packet.mWidth / 2 + board->mSeedBank->mX + board->mX) +
                   (packet.mY + packet.mHeight / 2 + board->mSeedBank->mY + board->mY) * 1024;
    }
    return -1;
}

extern "C" EMSCRIPTEN_KEEPALIVE int gardenInspectCell(int col, int row)
{
    Board* board = GardenBoard();
    if (!gardenSandbox || !GardenAdvancedAvailable(board) ||
        col < 0 || col >= MAX_GRID_SIZE_X || row < 0 || row >= MAX_GRID_SIZE_Y) return -1;
    return board->GridToPixelX(col, row) + 40 + board->mX +
           (board->GridToPixelY(col, row) + 40 + board->mY) * 1024;
}

// Read seed chooser coordinates only after its native input is enabled.
extern "C" EMSCRIPTEN_KEEPALIVE int gardenInspectChooser(int seed)
{
    if (!gardenSandbox || !gLawnApp || gLawnApp->GetDialogCount() ||
        !gLawnApp->mSeedChooserScreen || !gLawnApp->mBoard) return -1;
    auto* chooser = gLawnApp->mSeedChooserScreen.get();
    if (!chooser->mMouseVisible || chooser->mSeedsInFlight ||
        chooser->mChooseState != SeedChooserState::CHOOSE_NORMAL) return -1;
    if (seed == -1) return chooser->mSeedsInBank == gLawnApp->mBoard->mSeedBank->mNumPackets ? 1 : 0;
    if (seed < 0 || seed >= int(SeedType::SEED_IMITATER) ||
        !gLawnApp->HasSeedType(static_cast<SeedType>(seed))) return -3;
    auto& card = chooser->mChosenSeeds[seed];
    if (card.mSeedState == ChosenSeedState::SEED_IN_BANK) return -2;
    if (card.mSeedState != ChosenSeedState::SEED_IN_CHOOSER) return -3;
    return card.mX + chooser->mX + 24 + (card.mY + chooser->mY + 30) * 1024;
}

// Sandbox 2.0: explicit grid editing, limited to ordinary single-cell plants.
extern "C" EMSCRIPTEN_KEEPALIVE int gardenEditorAvailable()
{
    Board* board = GardenBoard();
    return gardenSandbox && GardenAdvancedAvailable(board) &&
        !gLawnApp->IsWallnutBowlingLevel() && !board->HasLevelAwardDropped();
}

extern "C" EMSCRIPTEN_KEEPALIVE int gardenEditorPlant(int col, int row, int seed)
{
    if (!gardenEditorAvailable() || col < 0 || col >= MAX_GRID_SIZE_X ||
        row < 0 || row >= MAX_GRID_SIZE_Y) return 0;
    Board* board = GardenBoard();
    const SeedType type = static_cast<SeedType>(seed);
    switch (type) {
        case SeedType::SEED_PEASHOOTER: case SeedType::SEED_SUNFLOWER:
        case SeedType::SEED_WALLNUT: case SeedType::SEED_SNOWPEA:
        case SeedType::SEED_REPEATER: case SeedType::SEED_PUFFSHROOM:
        case SeedType::SEED_FUMESHROOM: case SeedType::SEED_TALLNUT: break;
        default: return 0;
    }
    if (board->GetTopPlantAt(col, row, PlantPriority::TOPPLANT_ONLY_NORMAL_POSITION) ||
        board->CanPlantAt(col, row, type) != PlantingReason::PLANTING_OK) return 0;
    board->AddPlant(col, row, type, SeedType::SEED_NONE);
    return 1;
}

extern "C" EMSCRIPTEN_KEEPALIVE int gardenEditorRemove(int col, int row)
{
    if (!gardenEditorAvailable() || col < 0 || col >= MAX_GRID_SIZE_X ||
        row < 0 || row >= MAX_GRID_SIZE_Y) return 0;
    Plant* plant = GardenBoard()->GetTopPlantAt(col, row, PlantPriority::TOPPLANT_ONLY_NORMAL_POSITION);
    if (!plant || plant->mDead || plant->mSeedType == SeedType::SEED_COBCANNON ||
        plant->mOnBungeeState != PlantOnBungeeState::NOT_ON_BUNGEE) return 0;
    plant->Die();
    return 1;
}

// Temporary editor controls; never mutate the serialized structure of entities.
// Damage overrides are transient side tables, not part of native save layouts.
#include <unordered_map>
static std::unordered_map<const Plant*, int> gardenDamagePercent;
static std::unordered_map<const Projectile*, int> gardenShotPercent;
void GardenForgetPlant(const Plant* p) { gardenDamagePercent.erase(p); }
void GardenForgetShot(const Projectile* p) { gardenShotPercent.erase(p); }
int GardenPlantDamage(const Plant* p, int base)
{
    const auto i = gardenDamagePercent.find(p);
    return i == gardenDamagePercent.end() ? base : std::clamp(base * i->second / 100, 1, 100000);
}
void GardenRegisterShot(const Plant* p, const Projectile* shot)
{
    const auto i = gardenDamagePercent.find(p);
    if (i != gardenDamagePercent.end()) gardenShotPercent.insert_or_assign(shot, i->second);
}
int GardenShotDamage(const Projectile* p, int base)
{
    const auto i = gardenShotPercent.find(p);
    return i == gardenShotPercent.end() ? base : std::clamp(base * i->second / 100, 1, 100000);
}

static bool gardenFreezeWaves = false;
static bool gardenRegenerate = false;

bool GardenEditorWavesFrozen()
{
    return gardenFreezeWaves && gardenEditorAvailable();
}

extern "C" EMSCRIPTEN_KEEPALIVE int gardenEditorSpawnZombie(int row, int type, int count)
{
    if (!gardenEditorAvailable() || row < 0 || row >= MAX_GRID_SIZE_Y || count < 1 || count > 20)
        return 0;
    const auto zombieType = static_cast<ZombieType>(type);
    switch (zombieType) {
        case ZombieType::ZOMBIE_NORMAL: case ZombieType::ZOMBIE_FLAG:
        case ZombieType::ZOMBIE_TRAFFIC_CONE: case ZombieType::ZOMBIE_POLEVAULTER:
        case ZombieType::ZOMBIE_PAIL: case ZombieType::ZOMBIE_NEWSPAPER:
        case ZombieType::ZOMBIE_DOOR: case ZombieType::ZOMBIE_FOOTBALL:
        case ZombieType::ZOMBIE_SNORKEL: case ZombieType::ZOMBIE_DOLPHIN_RIDER:
        case ZombieType::ZOMBIE_BALLOON: case ZombieType::ZOMBIE_GARGANTUAR: break;
        default: return 0;
    }
    Board* board = GardenBoard();
    if (!board->RowCanHaveZombieType(row, zombieType)) return 0;
    int spawned = 0;
    for (; spawned < count; ++spawned)
        if (!board->AddZombieInRow(zombieType, row, Zombie::ZOMBIE_WAVE_DEBUG)) break;
    return spawned;
}

static Plant* GardenEditorSelectedPlant(int col, int row)
{
    if (!gardenEditorAvailable() || col < 0 || col >= MAX_GRID_SIZE_X || row < 0 || row >= MAX_GRID_SIZE_Y) return nullptr;
    auto* p = GardenBoard()->GetTopPlantAt(col, row, PlantPriority::TOPPLANT_ONLY_NORMAL_POSITION);
    return p && !p->mDead && p->mPlantHealth > 0 && p->mOnBungeeState == PlantOnBungeeState::NOT_ON_BUNGEE ? p : nullptr;
}
static Zombie* GardenEditorSelectedZombie(int row)
{
    if (!gardenEditorAvailable() || row < 0 || row >= MAX_GRID_SIZE_Y) return nullptr;
    Zombie* selected = nullptr;
    for (Zombie* z : GardenBoard()->mZombies)
        if (z->mRow == row && !z->mDead && !z->IsDeadOrDying() && z->mBodyHealth > 0 &&
            (!selected || z->mPosX < selected->mPosX)) selected = z;
    return selected;
}
extern "C" EMSCRIPTEN_KEEPALIVE int gardenEditorPlantState(int col, int row, int field)
{
    Plant* p = GardenEditorSelectedPlant(col,row);
    if (!p) return -1;
    switch (field) {
        case 0: return int(p->mSeedType);
        case 1: return p->mPlantHealth;
        case 2: return p->mPlantMaxHealth;
        case 3: return p->mLaunchRate;
        case 4: { const auto i = gardenDamagePercent.find(p); return i == gardenDamagePercent.end() ? 100 : i->second; }
        default: return -1;
    }
}
extern "C" EMSCRIPTEN_KEEPALIVE int gardenEditorPlantAttribute(int col, int row, int field, int value)
{
    Plant* p = GardenEditorSelectedPlant(col,row);
    if (!p) return 0;
    if (field == 1 && value >= 1 && value <= 100000) {
        p->mPlantHealth = value;
        p->mPlantMaxHealth = value;
        return 1;
    }
    if (field == 4 && value >= 10 && value <= 1000 && p->mLaunchRate > 0) {
        gardenDamagePercent.insert_or_assign(p, value); return 1;
    }
    if (field == 3 && value >= 80 && value <= 10000 && p->mLaunchRate > 0) {
        p->mLaunchRate = value;
        p->mLaunchCounter = std::min(p->mLaunchCounter, value);
        return 1;
    }
    return 0;
}
extern "C" EMSCRIPTEN_KEEPALIVE int gardenEditorZombieState(int row, int field)
{
    Zombie* z = GardenEditorSelectedZombie(row);
    if (!z) return -1;
    switch (field) {
        case 0: return int(z->mZombieType);
        case 1: return z->mBodyHealth;
        case 2: return z->mBodyMaxHealth;
        case 3: return int(z->mVelX * 1000.0f);
        default: return -1;
    }
}
extern "C" EMSCRIPTEN_KEEPALIVE int gardenEditorZombieAttribute(int row, int field, int value)
{
    Zombie* z = GardenEditorSelectedZombie(row);
    if (!z) return 0;
    if (field == 1 && value >= 1 && value <= 100000) {
        z->mBodyHealth = value; z->mBodyMaxHealth = value; return 1;
    }
    if (field == 3 && value >= 50 && value <= 3000) {
        z->mVelX = value / 1000.0f; return 1;
    }
    return 0;
}
extern "C" EMSCRIPTEN_KEEPALIVE int gardenEditorChooser(int seed)
{
    if (!gardenSandbox || !gLawnApp || gLawnApp->GetDialogCount() ||
        !gLawnApp->mSeedChooserScreen || !gLawnApp->mBoard) return -1;
    auto* chooser = gLawnApp->mSeedChooserScreen.get();
    if (!chooser->mMouseVisible || chooser->mSeedsInFlight ||
        chooser->mChooseState != SeedChooserState::CHOOSE_NORMAL) return -1;
    if (seed == -1) return chooser->mSeedsInBank == gLawnApp->mBoard->mSeedBank->mNumPackets ? 1 : 0;
    if (seed < 0 || seed >= int(SeedType::SEED_IMITATER) ||
        !gLawnApp->HasSeedType(static_cast<SeedType>(seed))) return -3;
    auto& card = chooser->mChosenSeeds[seed];
    if (card.mSeedState != ChosenSeedState::SEED_IN_CHOOSER) return -2;
    return card.mX + chooser->mX + 24 + (card.mY + chooser->mY + 30) * 1024;
}

extern "C" EMSCRIPTEN_KEEPALIVE int gardenEditorWave(int action, int value)
{
    if (!gardenEditorAvailable()) return -1;
    Board* board = GardenBoard();
    switch (action) {
        case 0: return board->mCurrentWave;
        case 1: return board->mNumWaves;
        case 2: gardenFreezeWaves = value != 0; return 1;
        case 3:
            if (board->mCurrentWave >= board->mNumWaves) return 0;
            gardenFreezeWaves = false;
            if (board->mHugeWaveCountDown > 0) board->mHugeWaveCountDown = 1;
            else if (board->mZombieCountDown > 6) board->mZombieCountDown = 6;
            return 1;
        case 4: return int(gardenFreezeWaves);
        case 5: gardenRegenerate = value != 0; return 1;
        case 6: return int(gardenRegenerate);
        default: return -1;
    }
}

static void GardenResetModifiers()
{
    gardenDamagePercent.clear();
    gardenShotPercent.clear();
    gardenFreezeWaves = false;
    gardenRegenerate = false;
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
    if (!gardenInfiniteSun && !gardenInstantRecharge && !gardenRegenerate) return;
    Board* board = GardenBoard();
    if (!GardenAdvancedAvailable(board) || board->mPaused) return;
    if (gardenRegenerate && gardenEditorAvailable())
        for (Plant* p : board->mPlants) if (!p->mDead && p->mPlantHealth > 0) p->mPlantHealth = p->mPlantMaxHealth;
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
