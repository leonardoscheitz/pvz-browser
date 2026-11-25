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

# Per-entity damage is stored in temporary maps and captured on projectile launch.
def editor_patch(s, old, new):
    if s.count(old) != 1:
        raise RuntimeError("Pinned editor source mismatch: " + old[:80])
    return s.replace(old, new, 1)

plant_path = upstream / "src" / "Lawn" / "Plant.cpp"
plant = plant_path.read_text(encoding="utf-8")
anchor = "void Plant::PlantInitialize(int theGridX, int theGridY, SeedType theSeedType, SeedType theImitaterType)\n{"
plant = editor_patch(plant, anchor, "extern void GardenForgetPlant(const Plant*);\nextern void GardenRegisterShot(const Plant*, const Projectile*);\nextern int GardenPlantDamage(const Plant*, int);\n\n" + anchor + "\n\tGardenForgetPlant(this);")
plant = editor_patch(plant, "void Plant::Die()\n{", "void Plant::Die()\n{\n\tGardenForgetPlant(this);")
anchor = "Projectile* aProjectile = mBoard->AddProjectile(aOriginX, aOriginY, mRenderOrder - 1, theRow, aProjectileType);"
plant = editor_patch(plant, anchor, anchor + "\n\tGardenRegisterShot(this, aProjectile);")
anchor = "Projectile* aProjectile = mBoard->AddProjectile(mX + 25, mY + 25, mRenderOrder - 1, mRow, ProjectileType::PROJECTILE_STAR);"
plant = editor_patch(plant, anchor, anchor + "\n\t\tGardenRegisterShot(this, aProjectile);")
plant = editor_patch(plant, "int aDamage = theDamage;\n\t\t\t\tif ((aZombie->mZombieType", "int aDamage = GardenPlantDamage(this, theDamage);\n\t\t\t\tif ((aZombie->mZombieType")
plant_path.write_text(plant, encoding="utf-8")

projectile_path = upstream / "src" / "Lawn" / "Projectile.cpp"
projectile = projectile_path.read_text(encoding="utf-8")
anchor = "void Projectile::ProjectileInitialize(int theX, int theY, int theRenderOrder, int theRow, ProjectileType theProjectileType)\n{"
projectile = editor_patch(projectile, anchor, "extern void GardenForgetShot(const Projectile*);\nextern int GardenShotDamage(const Projectile*, int);\n\n" + anchor + "\n\tGardenForgetShot(this);")
projectile = editor_patch(projectile, "void Projectile::Die()\n{", "void Projectile::Die()\n{\n\tGardenForgetShot(this);")
projectile = editor_patch(projectile, "int aOriginalDamage = aProjectileDef.mDamage;\n\tint aSplashDamage = aProjectileDef.mDamage / 3;", "int aOriginalDamage = GardenShotDamage(this, aProjectileDef.mDamage);\n\tint aSplashDamage = aOriginalDamage / 3;")
projectile = editor_patch(projectile, "theZombie->TakeDamage(GetProjectileDef().mDamage, aDamageFlags);", "theZombie->TakeDamage(GardenShotDamage(this, GetProjectileDef().mDamage), aDamageFlags);")
projectile_path.write_text(projectile, encoding="utf-8")

# Patch the pinned board at exact, verified anchors. Fail on upstream drift.
board_path = upstream / "src" / "Lawn" / "Board.cpp"
board = board_path.read_text(encoding="utf-8")
for old, new in [["void Board::MouseDownWithPlant(int x, int y, int theClickCount)\n{","extern bool GardenFusionEnabled();\n\n// Fusion recipes use existing native plant types and sprites. No copied Fusion assets.\nstatic SeedType GardenFusionResult(Board* board, Plant* base, SeedType incoming)\n{\n    if (!GardenFusionEnabled() || !base || base->mDead || base->mPlantHealth <= 0 ||\n        base->mOnBungeeState != PlantOnBungeeState::NOT_ON_BUNGEE ||\n        board->mApp->mGameMode != GameMode::GAMEMODE_ADVENTURE ||\n        board->mApp->mGameScene != GameScenes::SCENE_PLAYING ||\n        board->mLevelComplete || board->mBoardFadeOutCounter >= 0 ||\n        board->HasConveyorBeltSeedBank() || board->mApp->IsWallnutBowlingLevel() ||\n        board->mApp->IsSlotMachineLevel() ||\n        !board->mCursorObject || board->mCursorObject->mCursorType != CursorType::CURSOR_TYPE_PLANT_FROM_BANK ||\n        board->mCursorObject->mType != incoming)\n        return SeedType::SEED_NONE;\n    const SeedType planted = base->mSeedType;\n    if (planted == SeedType::SEED_MELONPULT && incoming == SeedType::SEED_SNOWPEA)\n        return SeedType::SEED_WINTERMELON;\n    if (planted != incoming) return SeedType::SEED_NONE;\n    switch (incoming) {\n        case SeedType::SEED_PEASHOOTER: return SeedType::SEED_REPEATER;\n        case SeedType::SEED_REPEATER: return SeedType::SEED_GATLINGPEA;\n        case SeedType::SEED_SUNFLOWER: return SeedType::SEED_TWINSUNFLOWER;\n        case SeedType::SEED_WALLNUT: return SeedType::SEED_TALLNUT;\n        case SeedType::SEED_FUMESHROOM: return SeedType::SEED_GLOOMSHROOM;\n        case SeedType::SEED_SPIKEWEED: return SeedType::SEED_SPIKEROCK;\n        default: return SeedType::SEED_NONE;\n    }\n}\n\nvoid Board::MouseDownWithPlant(int x, int y, int theClickCount)\n{"],["\tif (aNormalPlant && aNormalPlant->IsUpgradableTo(aPlantingSeedType))\n\t{\n\t\tif (aPlantingSeedType == SeedType::SEED_GLOOMSHROOM)","\tSeedType aFusionSeedType = GardenFusionResult(this, aNormalPlant, aPlantingSeedType);\n\tif (aNormalPlant && (aFusionSeedType != SeedType::SEED_NONE || aNormalPlant->IsUpgradableTo(aPlantingSeedType)))\n\t{\n\t\tif (aPlantingSeedType == SeedType::SEED_GLOOMSHROOM || aFusionSeedType == SeedType::SEED_GLOOMSHROOM)"],["\t\tPlant* aPlant = AddPlant(aGridX, aGridY, mCursorObject->mType, mCursorObject->mImitaterType);\n\t\tif (aIsAwake)","\t\tPlant* aPlant = aFusionSeedType == SeedType::SEED_NONE\n\t\t\t? AddPlant(aGridX, aGridY, mCursorObject->mType, mCursorObject->mImitaterType)\n\t\t\t: AddPlant(aGridX, aGridY, aFusionSeedType, SeedType::SEED_NONE);\n\t\tif (aIsAwake)"],["\t\t// wall-nut first aid\n\t\tif ((theSeedType == SeedType::SEED_WALLNUT || theSeedType == SeedType::SEED_TALLNUT) && aAidPurchased)","\t\tif (GardenFusionResult(this, aNormalPlant, theSeedType) != SeedType::SEED_NONE)\n\t\t\treturn PlantingReason::PLANTING_OK;\n\n\t\t// wall-nut first aid\n\t\tif ((theSeedType == SeedType::SEED_WALLNUT || theSeedType == SeedType::SEED_TALLNUT) && aAidPurchased)"],["\tif ((aPlantingSeedType == SeedType::SEED_WALLNUT || aPlantingSeedType == SeedType::SEED_TALLNUT) && aNormalPlant)","\tif (aFusionSeedType == SeedType::SEED_NONE && (aPlantingSeedType == SeedType::SEED_WALLNUT || aPlantingSeedType == SeedType::SEED_TALLNUT) && aNormalPlant)"]]:
    if board.count(old) != 1:
        raise RuntimeError("Pinned fusion source mismatch: " + old[:80])
    board = board.replace(old, new, 1)
board_path.write_text(board, encoding="utf-8")

# Fusion 0.2. Hybrid state lives outside the saved plant layout.
def patch_hybrid(source, old, new):
    if source.count(old) != 1:
        raise RuntimeError("Pinned hybrid source mismatch: " + old[:80])
    return source.replace(old, new, 1)

board = patch_hybrid(board, "extern bool GardenFusionEnabled();", """extern bool GardenFusionEnabled();
extern int GardenHybridKind(const Plant*);
extern void GardenHybridRegister(Plant*, int);

static int GardenHybridRecipe(SeedType a, SeedType b)
{
    if ((a == SeedType::SEED_PEASHOOTER && b == SeedType::SEED_SUNFLOWER) ||
        (b == SeedType::SEED_PEASHOOTER && a == SeedType::SEED_SUNFLOWER)) return 1;
    if ((a == SeedType::SEED_REPEATER && b == SeedType::SEED_SNOWPEA) ||
        (b == SeedType::SEED_REPEATER && a == SeedType::SEED_SNOWPEA)) return 2;
    if ((a == SeedType::SEED_PEASHOOTER && b == SeedType::SEED_WALLNUT) ||
        (b == SeedType::SEED_PEASHOOTER && a == SeedType::SEED_WALLNUT)) return 3;
    return 0;
}""")
board = patch_hybrid(board, "    const SeedType planted = base->mSeedType;",
"""    if (GardenHybridKind(base)) return SeedType::SEED_NONE;
    const SeedType planted = base->mSeedType;
    const int hybrid = GardenHybridRecipe(planted, incoming);
    if (hybrid == 1 || hybrid == 3) return SeedType::SEED_PEASHOOTER;
    if (hybrid == 2) return SeedType::SEED_REPEATER;""")
board = patch_hybrid(board, "\tSeedType aFusionSeedType = GardenFusionResult(this, aNormalPlant, aPlantingSeedType);",
"""\tSeedType aFusionSeedType = GardenFusionResult(this, aNormalPlant, aPlantingSeedType);
\tconst int aHybridKind = aFusionSeedType != SeedType::SEED_NONE && aNormalPlant
\t\t? GardenHybridRecipe(aNormalPlant->mSeedType, aPlantingSeedType) : 0;
\tif (aFusionSeedType != SeedType::SEED_NONE) Plant::PreloadPlantResources(aFusionSeedType);""")
board = patch_hybrid(board, "\t\t\t: AddPlant(aGridX, aGridY, aFusionSeedType, SeedType::SEED_NONE);",
"\t\t\t: AddPlant(aGridX, aGridY, aFusionSeedType, SeedType::SEED_NONE);\n\t\tif (aHybridKind) GardenHybridRegister(aPlant, aHybridKind);")
board_path.write_text(board, encoding="utf-8")

plant_path = upstream / "src" / "Lawn" / "Plant.cpp"
plant = plant_path.read_text(encoding="utf-8")
plant = patch_hybrid(plant, "void Plant::PlantInitialize(int theGridX, int theGridY, SeedType theSeedType, SeedType theImitaterType)\n{",
"""#include <unordered_map>
extern bool GardenFusionEnabled();
struct GardenHybridState { int kind; int sunTicks; };
static std::unordered_map<const Plant*, GardenHybridState> gardenHybrids;

int GardenHybridKind(const Plant* plant)
{
    if (!GardenFusionEnabled()) return 0;
    const auto it = gardenHybrids.find(plant);
    return it == gardenHybrids.end() ? 0 : it->second.kind;
}
void GardenHybridReset() { gardenHybrids.clear(); }
void GardenHybridRegister(Plant* plant, int kind)
{
    if (!GardenFusionEnabled() || !plant || kind < 1 || kind > 3) return;
    gardenHybrids.insert_or_assign(plant, GardenHybridState{kind, 1200});
    if (kind == 3) {
        plant->mPlantMaxHealth = 4000;
        plant->mPlantHealth = 4000;
    }
}

void Plant::PlantInitialize(int theGridX, int theGridY, SeedType theSeedType, SeedType theImitaterType)
{
    gardenHybrids.erase(this);""")
plant = patch_hybrid(plant, "void Plant::Die()\n{", "void Plant::Die()\n{\n    gardenHybrids.erase(this);")
plant = patch_hybrid(plant, "\tUpdateShooting();\n\n\tif (mStateCountdown > 0)",
"""\tUpdateShooting();
    if (GardenHybridKind(this) == 1 && !mDead && !mBoard->HasLevelAwardDropped()) {
        auto& state = gardenHybrids.at(this);
        if (--state.sunTicks <= 0) {
            state.sunTicks = 2400;
            mApp->PlayFoley(FoleyType::FOLEY_SPAWN_SUN);
            mBoard->AddCoin(mX, mY, CoinType::COIN_SUN, CoinMotion::COIN_MOTION_FROM_PLANT);
        }
    }

\tif (mStateCountdown > 0)""")
plant = patch_hybrid(plant, "\tif (mSeedType == SeedType::SEED_KERNELPULT && thePlantWeapon == PlantWeapon::WEAPON_SECONDARY)\n\t{\n\t\taProjectileType = ProjectileType::PROJECTILE_BUTTER;",
"""    if (GardenHybridKind(this) == 2 && aProjectileType == ProjectileType::PROJECTILE_PEA)
        aProjectileType = ProjectileType::PROJECTILE_SNOWPEA;
\tif (mSeedType == SeedType::SEED_KERNELPULT && thePlantWeapon == PlantWeapon::WEAPON_SECONDARY)
\t{
\t\taProjectileType = ProjectileType::PROJECTILE_BUTTER;""")
plant = patch_hybrid(plant, "\telse if (mSeedType == SeedType::SEED_EXPLODE_O_NUT)\n\t{\n\t\taColorOverride = Color(255, 64, 64);",
"""    else if (GardenHybridKind(this) == 1) { aColorOverride = Color(255, 232, 100); }
    else if (GardenHybridKind(this) == 2) { aColorOverride = Color(140, 215, 255); }
    else if (GardenHybridKind(this) == 3) { aColorOverride = Color(207, 168, 112); }
\telse if (mSeedType == SeedType::SEED_EXPLODE_O_NUT)
\t{
\t\taColorOverride = Color(255, 64, 64);""")
plant_path.write_text(plant, encoding="utf-8")
# Clear temporary identities before any board is destroyed.
app = source.read_text(encoding="utf-8")
app = patch_hybrid(app, "static void GardenResetModifiers();\n\nvoid LawnApp::KillBoard()\n{\n\tGardenResetModifiers();",
"static void GardenResetModifiers();\nextern void GardenHybridReset();\n\nvoid LawnApp::KillBoard()\n{\n\tGardenHybridReset();\n\tGardenResetModifiers();")
source.write_text(app, encoding="utf-8")

# Compose the original game art behind the live animated shooter; no borrowed
# external sprites. These are provisional native compositions, not new reanim rigs.
plant = plant_path.read_text(encoding="utf-8")
anchor = "\t\taOffsetX += mShakeOffsetX;\n\t\taOffsetY += mShakeOffsetY;\n\t\tif (IsInPlay() && mApp->IsIZombieLevel())"
replacement = """\t\taOffsetX += mShakeOffsetX;
\t\taOffsetY += mShakeOffsetY;
        const int hybridKind = GardenHybridKind(this);
        if (hybridKind == 1 || hybridKind == 3)
        {
            Image* part = hybridKind == 1 ? IMAGE_REANIM_SUNFLOWER_HEAD_SING1 : IMAGE_REANIM_WALLNUT_BODY;
            if (part && part->GetWidth() > 0 && part->GetHeight() > 0)
            {
                const float size = hybridKind == 1 ? 64.0f : 72.0f;
                const float scale = size / std::max(part->GetWidth(), part->GetHeight());
                int headX = 0, headY = 0;
                if (hybridKind == 1 && mApp->ReanimationTryToGet(mBodyReanimID))
                    GetPeaHeadOffset(headX, headY);
                const float centerX = hybridKind == 1 ? aOffsetX + headX + 29.0f : aOffsetX + 39.0f;
                const float centerY = hybridKind == 1 ? aOffsetY + headY + 18.0f : aOffsetY + 45.0f;
                PvzpDrawImageScaledF(g, part, centerX - part->GetWidth()*scale/2,
                    centerY - part->GetHeight()*scale/2, scale, scale);
            }
        }
\t\tif (IsInPlay() && mApp->IsIZombieLevel())"""
plant = patch_hybrid(plant, anchor, replacement)
plant = patch_hybrid(plant,
"\tif (mSeedType == SeedType::SEED_SNOWPEA)\n\t{\n\t\tint aRenderPosition = Board::MakeRenderOrder",
"\tif (mSeedType == SeedType::SEED_SNOWPEA || GardenHybridKind(this) == 2)\n\t{\n\t\tint aRenderPosition = Board::MakeRenderOrder")
plant_path.write_text(plant, encoding="utf-8")
