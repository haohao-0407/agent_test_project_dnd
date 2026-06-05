import { useEffect, useMemo, useState } from "react";
import {
  createCharacter,
  createPermanentCharacter,
  getPermanentCharacters,
  updateCharacter,
  updatePermanentCharacter
} from "../api/client";
import type {
  AbilityKey,
  Character,
  CharacterActionDetail,
  CharacterAttack,
  CharacterFeatureDetail,
  CharacterResource,
  ClassLevel,
  GameState,
  Player
} from "../api/types";

const abilityKeys: AbilityKey[] = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];
const slotLevels = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];
const classOptions: Array<{ name: string; hitDie: string; subclasses: string[] }> = [
  { name: "Barbarian", hitDie: "d12", subclasses: ["Path of the Berserker", "Path of the Totem Warrior"] },
  { name: "Bard", hitDie: "d8", subclasses: ["College of Lore", "College of Valor"] },
  { name: "Cleric", hitDie: "d8", subclasses: ["Life Domain", "Light Domain", "Trickery Domain", "War Domain"] },
  { name: "Druid", hitDie: "d8", subclasses: ["Circle of the Land", "Circle of the Moon"] },
  { name: "Fighter", hitDie: "d10", subclasses: ["Champion", "Battle Master", "Eldritch Knight"] },
  { name: "Monk", hitDie: "d8", subclasses: ["Way of the Open Hand", "Way of Shadow", "Way of the Four Elements"] },
  { name: "Paladin", hitDie: "d10", subclasses: ["Oath of Devotion", "Oath of the Ancients", "Oath of Vengeance"] },
  { name: "Ranger", hitDie: "d10", subclasses: ["Hunter", "Beast Master"] },
  { name: "Rogue", hitDie: "d8", subclasses: ["Thief", "Assassin", "Arcane Trickster"] },
  { name: "Sorcerer", hitDie: "d6", subclasses: ["Draconic Bloodline", "Wild Magic"] },
  { name: "Warlock", hitDie: "d8", subclasses: ["The Archfey", "The Fiend", "The Great Old One"] },
  { name: "Wizard", hitDie: "d6", subclasses: ["School of Evocation", "School of Abjuration", "School of Divination", "School of Illusion"] }
];
const raceOptions: Array<{ name: string; subraces: string[] }> = [
  { name: "Human", subraces: ["Standard Human", "Variant Human"] },
  { name: "Elf", subraces: ["High Elf", "Wood Elf", "Drow"] },
  { name: "Dwarf", subraces: ["Hill Dwarf", "Mountain Dwarf"] },
  { name: "Halfling", subraces: ["Lightfoot Halfling", "Stout Halfling"] },
  { name: "Dragonborn", subraces: ["Black", "Blue", "Brass", "Bronze", "Copper", "Gold", "Green", "Red", "Silver", "White"] },
  { name: "Gnome", subraces: ["Forest Gnome", "Rock Gnome"] },
  { name: "Half-Elf", subraces: [""] },
  { name: "Half-Orc", subraces: [""] },
  { name: "Tiefling", subraces: [""] }
];
const backgroundOptions = [
  "Acolyte",
  "Charlatan",
  "Criminal",
  "Entertainer",
  "Folk Hero",
  "Guild Artisan",
  "Hermit",
  "Noble",
  "Outlander",
  "Sage",
  "Sailor",
  "Soldier",
  "Urchin"
];
const alignmentOptions = [
  "Lawful Good",
  "Neutral Good",
  "Chaotic Good",
  "Lawful Neutral",
  "Neutral",
  "Chaotic Neutral",
  "Lawful Evil",
  "Neutral Evil",
  "Chaotic Evil",
  "Unaligned"
];

type HitDie = { die: string; max: number; current: number };

type CharacterCardsPageProps = {
  state?: GameState;
  characters?: Character[];
  currentUserId: string;
  currentUser?: Player;
  mode?: "session" | "permanent";
  onStateChange?: (state: GameState) => void;
  onCharactersChange?: (characters: Character[]) => void;
};

export function CharacterCardsPage({
  state,
  characters: libraryCharacters,
  currentUserId,
  currentUser,
  mode = "session",
  onStateChange,
  onCharactersChange
}: CharacterCardsPageProps) {
  const characters = state?.characters || libraryCharacters || [];
  const [selectedId, setSelectedId] = useState(characters[0]?.id || "");
  const selectedCharacter = useMemo(
    () => characters.find((character) => character.id === selectedId) || characters[0],
    [selectedId, characters]
  );
  const [draft, setDraft] = useState<Character>(() =>
    cloneCharacter(selectedCharacter || createBlankCharacter(currentUserId))
  );
  const [isNew, setIsNew] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [permanentCharacters, setPermanentCharacters] = useState<Character[]>([]);
  const [importCharacterId, setImportCharacterId] = useState("");

  useEffect(() => {
    if (!selectedCharacter || dirty) return;
    setDraft(cloneCharacter(selectedCharacter));
    setIsNew(false);
  }, [dirty, selectedCharacter]);

  function selectCharacter(character: Character) {
    setSelectedId(character.id);
    setDraft(cloneCharacter(character));
    setIsNew(false);
    setDirty(false);
    setNotice(null);
  }

  function startNewCharacter() {
    const next = createBlankCharacter(currentUserId);
    setSelectedId(next.id);
    setDraft(next);
    setIsNew(true);
    setDirty(true);
    setNotice(null);
  }

  function updateDraft(updater: (next: Character) => void) {
    setDraft((current) => {
      const next = cloneCharacter(current);
      updater(next);
      next.class = summarizeClass(next.classes) || next.class;
      next.level = Math.max(
        1,
        next.classes?.reduce((sum, item) => sum + numberValue(item.level), 0) || next.level || 1
      );
      next.abilities = buildAbilities(next.attributes, next.abilities);
      next.attackDetails = getAttackDetails(next);
      next.attacks = next.attackDetails.map((attack) => summarizeAttack(attack, next));
      next.actionDetails = getActionDetails(next);
      next.actions = next.actionDetails.map(summarizeActionDetail);
      next.featureDetails = getFeatureDetails(next, "features");
      next.features = next.featureDetails.map(summarizeFeatureDetail);
      next.traitDetails = getFeatureDetails(next, "traits");
      next.traits = next.traitDetails.map(summarizeFeatureDetail);
      return next;
    });
    setDirty(true);
    setNotice(null);
  }

  async function saveDraft() {
    setSaving(true);
    setNotice(null);
    try {
      const payload = mode === "permanent"
        ? isNew
          ? await createPermanentCharacter({ userId: currentUserId, character: draft })
          : await updatePermanentCharacter({
              characterId: draft.id,
              userId: currentUserId,
              updates: omitId(draft)
            })
        : isNew
          ? await createCharacter({ userId: currentUserId, character: draft })
          : await updateCharacter({
              characterId: draft.id,
              userId: currentUserId,
              updates: omitId(draft)
            });
      if ("state" in payload) {
        onStateChange?.(payload.state);
      } else {
        onCharactersChange?.(payload.characters);
      }
      setDraft(cloneCharacter(payload.character));
      setSelectedId(payload.character.id);
      setIsNew(false);
      setDirty(false);
      setNotice("已保存");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  async function loadPermanentCharacters() {
    const payload = await getPermanentCharacters();
    setPermanentCharacters(payload.characters);
    setImportCharacterId(payload.characters[0]?.id || "");
  }

  async function importPermanentCharacter() {
    if (!state || !importCharacterId) return;
    const source = permanentCharacters.find((character) => character.id === importCharacterId);
    if (!source) return;
    const imported = cloneCharacter(source);
    imported.id = uniqueCharacterId(imported.id, state.characters);
    imported.ownerUserId = currentUserId;
    const payload = await createCharacter({ userId: currentUserId, character: imported });
    onStateChange?.(payload.state);
    setSelectedId(payload.character.id);
    setDraft(cloneCharacter(payload.character));
    setIsNew(false);
    setDirty(false);
    setNotice("已导入");
  }

  const canSave = mode === "permanent" || currentUser?.role === "dm" || draft.ownerUserId === currentUserId || isNew;

  return (
    <section className="character-page" aria-labelledby="character-page-title">
      <aside className="character-sidebar">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Character Cards</p>
            <h2 id="character-page-title">{mode === "permanent" ? "永久角色卡" : "角色卡"}</h2>
          </div>
          <button type="button" onClick={startNewCharacter}>
            新建
          </button>
        </div>
        {mode === "session" ? (
          <div className="import-panel">
            <button type="button" onClick={() => void loadPermanentCharacters()}>
              读取永久卡
            </button>
            <select value={importCharacterId} onChange={(event) => setImportCharacterId(event.target.value)}>
              {permanentCharacters.map((character) => (
                <option key={character.id} value={character.id}>
                  {character.name}
                </option>
              ))}
            </select>
            <button type="button" onClick={() => void importPermanentCharacter()} disabled={!importCharacterId}>
              导入
            </button>
          </div>
        ) : null}
        <div className="character-picker">
          {characters.map((character) => (
            <button
              type="button"
              className={character.id === draft.id && !isNew ? "active" : ""}
              key={character.id}
              onClick={() => selectCharacter(character)}
            >
              <strong>{character.name}</strong>
              <span>{character.race} / {character.class}</span>
            </button>
          ))}
          {isNew ? (
            <button type="button" className="active">
              <strong>{draft.name}</strong>
              <span>{draft.race} / {draft.class}</span>
            </button>
          ) : null}
        </div>
      </aside>

      <form
        className="character-editor"
        onSubmit={(event) => {
          event.preventDefault();
          void saveDraft();
        }}
      >
        <div className="editor-toolbar">
          <div>
            <p className="eyebrow">5e DND</p>
            <h2>{draft.name || "未命名角色"}</h2>
          </div>
          <div className="toolbar-actions">
            {notice ? <span className="save-notice">{notice}</span> : null}
            <button type="submit" disabled={saving || !canSave || !dirty}>
              {saving ? "保存中" : "保存"}
            </button>
          </div>
        </div>

        <div className="editor-scroll">
          <section className="sheet-section">
            <h3>基础</h3>
            <div className="form-grid four">
              <TextField label="名称" value={draft.name} onChange={(value) => updateDraft((next) => (next.name = value))} />
              <TextField label="玩家" value={draft.playerName || ""} onChange={(value) => updateDraft((next) => (next.playerName = value))} />
              <SelectField
                label="种族"
                value={draft.race}
                options={withCurrentOption(raceOptions.map((option) => option.name), draft.race)}
                onChange={(value) => updateDraft((next) => {
                  const selectedRace = raceOptions.find((option) => option.name === value) || raceOptions[0];
                  next.race = selectedRace.name;
                  next.subrace = selectedRace.subraces[0] || "";
                })}
              />
              <SelectField
                label="亚种"
                value={draft.subrace || ""}
                options={withCurrentOption((raceOptions.find((option) => option.name === draft.race) || raceOptions[0]).subraces, draft.subrace || "")}
                onChange={(value) => updateDraft((next) => (next.subrace = value))}
              />
              <SelectField
                label="背景"
                value={draft.background || ""}
                options={withCurrentOption(backgroundOptions, draft.background || "")}
                onChange={(value) => updateDraft((next) => (next.background = value))}
              />
              <SelectField
                label="阵营"
                value={draft.alignment || ""}
                options={withCurrentOption(alignmentOptions, draft.alignment || "")}
                onChange={(value) => updateDraft((next) => (next.alignment = value))}
              />
              <NumberField label="经验" value={draft.experience || 0} onChange={(value) => updateDraft((next) => (next.experience = value))} />
              <NumberField label="熟练加值" value={draft.proficiencyBonus || 2} onChange={(value) => updateDraft((next) => (next.proficiencyBonus = value))} />
            </div>
            <label className="check-row">
              <input
                type="checkbox"
                checked={Boolean(draft.inspiration)}
                onChange={(event) => updateDraft((next) => (next.inspiration = event.target.checked))}
              />
              <span>激励</span>
            </label>
            <ClassTable
              classes={draft.classes || []}
              onChange={(classes) => updateDraft((next) => (next.classes = classes))}
            />
          </section>

          <section className="sheet-section">
            <h3>属性</h3>
            <div className="ability-grid">
              {abilityKeys.map((key) => (
                <label className="ability-edit" key={key}>
                  <span>{key}</span>
                  <input
                    type="number"
                    value={draft.attributes[key] ?? 10}
                    onChange={(event) =>
                      updateDraft((next) => {
                        next.attributes[key] = numberValue(event.target.value);
                      })
                    }
                  />
                  <strong>{formatModifier((draft.attributes[key] ?? 10) - 10)}</strong>
                </label>
              ))}
            </div>
          </section>

          <section className="sheet-section">
            <h3>战斗</h3>
            <div className="form-grid six">
              <NumberField label="当前 HP" value={draft.hp.current} onChange={(value) => updateDraft((next) => (next.hp.current = value))} />
              <NumberField label="最大 HP" value={draft.hp.max} onChange={(value) => updateDraft((next) => (next.hp.max = value))} />
              <NumberField label="临时 HP" value={draft.hp.temp} onChange={(value) => updateDraft((next) => (next.hp.temp = value))} />
              <NumberField label="AC" value={draft.ac} onChange={(value) => updateDraft((next) => (next.ac = value))} />
              <NumberField label="先攻" value={draft.initiative || 0} onChange={(value) => updateDraft((next) => (next.initiative = value))} />
              <NumberField label="速度" value={draft.speed} onChange={(value) => updateDraft((next) => (next.speed = value))} />
              <NumberField label="死亡成功" value={draft.deathSaves?.successes || 0} onChange={(value) => updateDraft((next) => (next.deathSaves = { ...(next.deathSaves || { successes: 0, failures: 0 }), successes: value }))} />
              <NumberField label="死亡失败" value={draft.deathSaves?.failures || 0} onChange={(value) => updateDraft((next) => (next.deathSaves = { ...(next.deathSaves || { successes: 0, failures: 0 }), failures: value }))} />
            </div>
            <div className="form-grid two">
              <HitDiceTable
                hitDice={draft.hitDice || []}
                onChange={(hitDice) => updateDraft((next) => (next.hitDice = hitDice))}
              />
              <StringListTable
                title="状态"
                addLabel="添加状态"
                items={draft.conditions}
                onChange={(items) => updateDraft((next) => (next.conditions = items))}
              />
            </div>
          </section>

          <section className="sheet-section">
            <h3>熟练</h3>
            <div className="form-grid two">
              <StringListTable title="豁免" addLabel="添加豁免" items={draft.savingThrows || []} onChange={(items) => updateDraft((next) => (next.savingThrows = items))} />
              <StringListTable title="技能" addLabel="添加技能" items={draft.skills} onChange={(items) => updateDraft((next) => (next.skills = items))} />
              <StringListTable title="护甲熟练" addLabel="添加熟练" items={draft.proficiencies?.armor || []} onChange={(items) => updateDraft((next) => (ensureProficiencies(next).armor = items))} />
              <StringListTable title="武器熟练" addLabel="添加熟练" items={draft.proficiencies?.weapons || []} onChange={(items) => updateDraft((next) => (ensureProficiencies(next).weapons = items))} />
              <StringListTable title="工具熟练" addLabel="添加熟练" items={draft.proficiencies?.tools || []} onChange={(items) => updateDraft((next) => (ensureProficiencies(next).tools = items))} />
              <StringListTable title="语言" addLabel="添加语言" items={draft.languages || []} onChange={(items) => updateDraft((next) => (next.languages = items))} />
            </div>
          </section>

          <section className="sheet-section">
            <h3>动作</h3>
            <AttackTable
              character={draft}
              attacks={getAttackDetails(draft)}
              onChange={(attacks) => updateDraft((next) => (next.attackDetails = attacks))}
            />
            <div className="form-grid two">
              <ActionDetailTable
                title="动作"
                addLabel="添加动作"
                actions={getActionDetails(draft)}
                onChange={(actions) => updateDraft((next) => (next.actionDetails = actions))}
              />
              <FeatureDetailTable
                title="特性"
                addLabel="添加特性"
                features={getFeatureDetails(draft, "features")}
                onChange={(features) => updateDraft((next) => (next.featureDetails = features))}
              />
              <FeatureDetailTable
                title="种族/职业 traits"
                addLabel="添加 trait"
                features={getFeatureDetails(draft, "traits")}
                onChange={(traits) => updateDraft((next) => (next.traitDetails = traits))}
              />
            </div>
          </section>

          <section className="sheet-section">
            <h3>资源</h3>
            <ResourceTable
              resources={draft.resources || []}
              onChange={(resources) => updateDraft((next) => (next.resources = resources))}
            />
          </section>

          <section className="sheet-section">
            <h3>法术</h3>
            <div className="form-grid six">
              <TextField label="施法属性" value={draft.spellcasting?.ability || ""} onChange={(value) => updateDraft((next) => (ensureSpellcasting(next).ability = value))} />
              <NumberField label="豁免 DC" value={draft.spellcasting?.saveDc || 0} onChange={(value) => updateDraft((next) => (ensureSpellcasting(next).saveDc = value))} />
              <NumberField label="法术攻击" value={draft.spellcasting?.attackBonus || 0} onChange={(value) => updateDraft((next) => (ensureSpellcasting(next).attackBonus = value))} />
              <NumberField label="契约环级" value={draft.spellcasting?.pactSlots?.slotLevel || 0} onChange={(value) => updateDraft((next) => (ensureSpellcasting(next).pactSlots.slotLevel = value))} />
              <NumberField label="契约当前" value={draft.spellcasting?.pactSlots?.current || 0} onChange={(value) => updateDraft((next) => (ensureSpellcasting(next).pactSlots.current = value))} />
              <NumberField label="契约上限" value={draft.spellcasting?.pactSlots?.max || 0} onChange={(value) => updateDraft((next) => (ensureSpellcasting(next).pactSlots.max = value))} />
            </div>
            <SpellSlotTable draft={draft} updateDraft={updateDraft} />
            <div className="form-grid two">
              <StringListTable title="已知法术" addLabel="添加法术" items={draft.spellcasting?.spellsKnown || []} onChange={(items) => updateDraft((next) => (ensureSpellcasting(next).spellsKnown = items))} />
              <StringListTable title="准备法术" addLabel="添加法术" items={draft.spellcasting?.spellsPrepared || []} onChange={(items) => updateDraft((next) => (ensureSpellcasting(next).spellsPrepared = items))} />
            </div>
          </section>

          <section className="sheet-section">
            <h3>装备</h3>
            <div className="form-grid two">
              <StringListTable title="物品" addLabel="添加物品" items={draft.equipment?.items || []} onChange={(items) => updateDraft((next) => (ensureEquipment(next).items = items))} />
              <StringListTable title="已同调" addLabel="添加物品" items={draft.equipment?.attunedItems || []} onChange={(items) => updateDraft((next) => (ensureEquipment(next).attunedItems = items))} />
            </div>
            <div className="form-grid six">
              {(["cp", "sp", "ep", "gp", "pp"] as const).map((coin) => (
                <NumberField
                  key={coin}
                  label={coin.toUpperCase()}
                  value={draft.currency?.[coin] || 0}
                  onChange={(value) => updateDraft((next) => (ensureCurrency(next)[coin] = value))}
                />
              ))}
              <NumberField label="负重" value={draft.equipment?.carryingCapacity || 0} onChange={(value) => updateDraft((next) => (ensureEquipment(next).carryingCapacity = value))} />
            </div>
          </section>

          <section className="sheet-section">
            <h3>叙事</h3>
            <div className="form-grid two">
              <TextArea label="性格" value={draft.personality?.traits || ""} onChange={(value) => updateDraft((next) => (ensurePersonality(next).traits = value))} />
              <TextArea label="理想" value={draft.personality?.ideals || ""} onChange={(value) => updateDraft((next) => (ensurePersonality(next).ideals = value))} />
              <TextArea label="羁绊" value={draft.personality?.bonds || ""} onChange={(value) => updateDraft((next) => (ensurePersonality(next).bonds = value))} />
              <TextArea label="缺点" value={draft.personality?.flaws || ""} onChange={(value) => updateDraft((next) => (ensurePersonality(next).flaws = value))} />
            </div>
            <TextArea label="备注" value={draft.notes || ""} onChange={(value) => updateDraft((next) => (next.notes = value))} />
          </section>
        </div>
      </form>
    </section>
  );
}

function TextField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option || "none"} value={option}>
            {option || "None"}
          </option>
        ))}
      </select>
    </label>
  );
}

function NumberField({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="number" value={value} onChange={(event) => onChange(numberValue(event.target.value))} />
    </label>
  );
}

function TextArea({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function ClassTable({ classes, onChange }: { classes: ClassLevel[]; onChange: (classes: ClassLevel[]) => void }) {
  return (
    <EditableTable
      title="职业等级"
      headers={["职业", "子职", "等级", "职业生命骰", ""]}
      onAdd={() => onChange([...classes, { name: "", subclass: "", level: 1, hitDie: "d8" }])}
      addLabel="添加职业"
    >
      {classes.map((item, index) => {
        const selectedClass = classOptions.find((option) => option.name === item.name) || classOptions[0];
        const subclassOptions = withCurrentOption(selectedClass.subclasses, item.subclass);
        return (
          <tr key={`${item.name}-${index}`}>
            <td>
              <select
                value={item.name}
                onChange={(event) => {
                  const nextClass = classOptions.find((option) => option.name === event.target.value) || classOptions[0];
                  onChange(updateAt(classes, index, {
                    ...item,
                    name: nextClass.name,
                    subclass: nextClass.subclasses[0] || "",
                    hitDie: nextClass.hitDie
                  }));
                }}
              >
                {withCurrentOption(classOptions.map((option) => option.name), item.name).map((name) => (
                  <option key={name} value={name}>{name}</option>
                ))}
              </select>
            </td>
            <td>
              <select
                value={item.subclass}
                onChange={(event) => onChange(updateAt(classes, index, { ...item, subclass: event.target.value }))}
              >
                {subclassOptions.map((subclass) => (
                  <option key={subclass} value={subclass}>{subclass || "None"}</option>
                ))}
              </select>
            </td>
            <td><input type="number" value={item.level} onChange={(event) => onChange(updateAt(classes, index, { ...item, level: Math.max(1, numberValue(event.target.value)) }))} /></td>
            <td><input value={item.hitDie} onChange={(event) => onChange(updateAt(classes, index, { ...item, hitDie: event.target.value }))} /></td>
            <td><button type="button" onClick={() => onChange(removeAt(classes, index))}>删除</button></td>
          </tr>
        );
      })}
    </EditableTable>
  );
}

function HitDiceTable({ hitDice, onChange }: { hitDice: HitDie[]; onChange: (hitDice: HitDie[]) => void }) {
  return (
    <EditableTable
      title="生命骰"
      headers={["骰型", "当前", "上限", ""]}
      onAdd={() => onChange([...hitDice, { die: "d8", current: 1, max: 1 }])}
      addLabel="添加生命骰"
    >
      {hitDice.map((item, index) => (
        <tr key={`${item.die}-${index}`}>
          <td><input value={item.die} onChange={(event) => onChange(updateAt(hitDice, index, { ...item, die: event.target.value }))} /></td>
          <td><input type="number" value={item.current} onChange={(event) => onChange(updateAt(hitDice, index, { ...item, current: numberValue(event.target.value) }))} /></td>
          <td><input type="number" value={item.max} onChange={(event) => onChange(updateAt(hitDice, index, { ...item, max: Math.max(1, numberValue(event.target.value)) }))} /></td>
          <td><button type="button" onClick={() => onChange(removeAt(hitDice, index))}>删除</button></td>
        </tr>
      ))}
    </EditableTable>
  );
}

function ResourceTable({ resources, onChange }: { resources: CharacterResource[]; onChange: (resources: CharacterResource[]) => void }) {
  return (
    <EditableTable
      title="资源"
      headers={["名称", "当前", "上限", "恢复", ""]}
      onAdd={() => onChange([...resources, { name: "", current: 0, max: 0, reset: "long rest" }])}
      addLabel="添加资源"
    >
      {resources.map((item, index) => (
        <tr key={`${item.name}-${index}`}>
          <td><input value={item.name} onChange={(event) => onChange(updateAt(resources, index, { ...item, name: event.target.value }))} /></td>
          <td><input type="number" value={item.current} onChange={(event) => onChange(updateAt(resources, index, { ...item, current: numberValue(event.target.value) }))} /></td>
          <td><input type="number" value={item.max} onChange={(event) => onChange(updateAt(resources, index, { ...item, max: numberValue(event.target.value) }))} /></td>
          <td><input value={item.reset} onChange={(event) => onChange(updateAt(resources, index, { ...item, reset: event.target.value }))} /></td>
          <td><button type="button" onClick={() => onChange(removeAt(resources, index))}>删除</button></td>
        </tr>
      ))}
    </EditableTable>
  );
}

function AttackTable({
  character,
  attacks,
  onChange
}: {
  character: Character;
  attacks: CharacterAttack[];
  onChange: (attacks: CharacterAttack[]) => void;
}) {
  return (
    <EditableTable
      title="攻击"
      headers={["名称", "属性", "熟练", "额外命中", "命中", "伤害骰", "加属性", "额外伤害", "伤害", "类型", "射程", "备注", ""]}
      onAdd={() => onChange([...attacks, blankAttack()])}
      addLabel="添加攻击"
      wide
    >
      {attacks.map((attack, index) => (
        <tr key={`${attack.name}-${index}`}>
          <td><input value={attack.name} onChange={(event) => onChange(updateAt(attacks, index, { ...attack, name: event.target.value }))} /></td>
          <td>
            <select
              value={attack.ability}
              onChange={(event) => onChange(updateAt(attacks, index, { ...attack, ability: event.target.value as AbilityKey }))}
            >
              {abilityKeys.map((key) => (
                <option key={key} value={key}>{key}</option>
              ))}
            </select>
          </td>
          <td>
            <input
              type="checkbox"
              checked={attack.proficient}
              onChange={(event) => onChange(updateAt(attacks, index, { ...attack, proficient: event.target.checked }))}
            />
          </td>
          <td><input type="number" value={attack.extraAttackBonus} onChange={(event) => onChange(updateAt(attacks, index, { ...attack, extraAttackBonus: numberValue(event.target.value) }))} /></td>
          <td><strong>{formatSigned(attackBonus(attack, character))}</strong></td>
          <td><input value={attack.damageDice} onChange={(event) => onChange(updateAt(attacks, index, { ...attack, damageDice: event.target.value }))} /></td>
          <td>
            <input
              type="checkbox"
              checked={attack.damageAbility}
              onChange={(event) => onChange(updateAt(attacks, index, { ...attack, damageAbility: event.target.checked }))}
            />
          </td>
          <td><input type="number" value={attack.extraDamageBonus} onChange={(event) => onChange(updateAt(attacks, index, { ...attack, extraDamageBonus: numberValue(event.target.value) }))} /></td>
          <td><strong>{formatDamage(attack, character)}</strong></td>
          <td><input value={attack.damageType} onChange={(event) => onChange(updateAt(attacks, index, { ...attack, damageType: event.target.value }))} /></td>
          <td><input value={attack.range} onChange={(event) => onChange(updateAt(attacks, index, { ...attack, range: event.target.value }))} /></td>
          <td><input value={attack.notes} onChange={(event) => onChange(updateAt(attacks, index, { ...attack, notes: event.target.value }))} /></td>
          <td><button type="button" onClick={() => onChange(removeAt(attacks, index))}>删除</button></td>
        </tr>
      ))}
    </EditableTable>
  );
}

function ActionDetailTable({
  title,
  addLabel,
  actions,
  onChange
}: {
  title: string;
  addLabel: string;
  actions: CharacterActionDetail[];
  onChange: (actions: CharacterActionDetail[]) => void;
}) {
  return (
    <EditableTable
      title={title}
      headers={["名称", "类型", "说明", ""]}
      onAdd={() => onChange([...actions, { name: "", cost: "action", description: "" }])}
      addLabel={addLabel}
      wide
    >
      {actions.map((action, index) => (
        <tr key={`${title}-${index}`}>
          <td><input value={action.name} onChange={(event) => onChange(updateAt(actions, index, { ...action, name: event.target.value }))} /></td>
          <td><input value={action.cost} onChange={(event) => onChange(updateAt(actions, index, { ...action, cost: event.target.value }))} /></td>
          <td><input value={action.description} onChange={(event) => onChange(updateAt(actions, index, { ...action, description: event.target.value }))} /></td>
          <td><button type="button" onClick={() => onChange(removeAt(actions, index))}>删除</button></td>
        </tr>
      ))}
    </EditableTable>
  );
}

function FeatureDetailTable({
  title,
  addLabel,
  features,
  onChange
}: {
  title: string;
  addLabel: string;
  features: CharacterFeatureDetail[];
  onChange: (features: CharacterFeatureDetail[]) => void;
}) {
  return (
    <EditableTable
      title={title}
      headers={["名称", "来源", "说明", ""]}
      onAdd={() => onChange([...features, { name: "", source: "", description: "" }])}
      addLabel={addLabel}
      wide
    >
      {features.map((feature, index) => (
        <tr key={`${title}-${index}`}>
          <td><input value={feature.name} onChange={(event) => onChange(updateAt(features, index, { ...feature, name: event.target.value }))} /></td>
          <td><input value={feature.source} onChange={(event) => onChange(updateAt(features, index, { ...feature, source: event.target.value }))} /></td>
          <td><input value={feature.description} onChange={(event) => onChange(updateAt(features, index, { ...feature, description: event.target.value }))} /></td>
          <td><button type="button" onClick={() => onChange(removeAt(features, index))}>删除</button></td>
        </tr>
      ))}
    </EditableTable>
  );
}

function StringListTable({
  title,
  addLabel,
  items,
  onChange
}: {
  title: string;
  addLabel: string;
  items: string[];
  onChange: (items: string[]) => void;
}) {
  return (
    <EditableTable
      title={title}
      headers={["内容", ""]}
      onAdd={() => onChange([...items, ""])}
      addLabel={addLabel}
    >
      {items.map((item, index) => (
        <tr key={`${title}-${index}`}>
          <td><input value={item} onChange={(event) => onChange(updateAt(items, index, event.target.value))} /></td>
          <td><button type="button" onClick={() => onChange(removeAt(items, index))}>删除</button></td>
        </tr>
      ))}
    </EditableTable>
  );
}

function SpellSlotTable({
  draft,
  updateDraft
}: {
  draft: Character;
  updateDraft: (updater: (next: Character) => void) => void;
}) {
  return (
    <EditableTable title="法术位" headers={["环级", "当前", "上限"]}>
      {slotLevels.map((level) => (
        <tr key={level}>
          <th scope="row">{level}环</th>
          <td>
            <input
              type="number"
              value={draft.spellcasting?.slots?.[level]?.current || 0}
              onChange={(event) => updateDraft((next) => (ensureSpellSlot(next, level).current = numberValue(event.target.value)))}
            />
          </td>
          <td>
            <input
              type="number"
              value={draft.spellcasting?.slots?.[level]?.max || 0}
              onChange={(event) => updateDraft((next) => (ensureSpellSlot(next, level).max = numberValue(event.target.value)))}
            />
          </td>
        </tr>
      ))}
    </EditableTable>
  );
}

function EditableTable({
  title,
  headers,
  children,
  onAdd,
  addLabel,
  wide = false
}: {
  title: string;
  headers: string[];
  children: React.ReactNode;
  onAdd?: () => void;
  addLabel?: string;
  wide?: boolean;
}) {
  return (
    <div className={wide ? "editable-table wide-table" : "editable-table"}>
      <div className="table-title">
        <span>{title}</span>
        {onAdd ? (
          <button type="button" onClick={onAdd}>
            {addLabel || "添加"}
          </button>
        ) : null}
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {headers.map((header) => (
                <th key={header}>{header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {children}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function createBlankCharacter(userId: string): Character {
  const id = `character-${Date.now()}`;
  return {
    id,
    ownerUserId: userId,
    name: "新角色",
    playerName: "",
    class: "Fighter 1",
    classes: [{ name: "Fighter", subclass: "", level: 1, hitDie: "d10" }],
    level: 1,
    race: "Human",
    subrace: "",
    background: "Adventurer",
    alignment: "Neutral",
    experience: 0,
    inspiration: false,
    proficiencyBonus: 2,
    hp: { current: 10, max: 10, temp: 0 },
    hitDice: [{ die: "d10", max: 1, current: 1 }],
    deathSaves: { successes: 0, failures: 0 },
    ac: 10,
    initiative: 0,
    speed: 30,
    attributes: { STR: 10, DEX: 10, CON: 10, INT: 10, WIS: 10, CHA: 10 },
    abilities: buildAbilities({ STR: 10, DEX: 10, CON: 10, INT: 10, WIS: 10, CHA: 10 }),
    savingThrows: [],
    skills: [],
    skillDetails: [],
    attacks: [],
    attackDetails: [],
    actions: [],
    actionDetails: [],
    conditions: [],
    defenses: { resistances: [], immunities: [], vulnerabilities: [] },
    senses: { passivePerception: 10, passiveInvestigation: 10, passiveInsight: 10, other: [] },
    proficiencies: { armor: [], weapons: [], tools: [] },
    languages: [],
    equipment: { items: [], attunedItems: [], carryingCapacity: 0 },
    currency: { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 },
    features: [],
    featureDetails: [],
    traits: [],
    traitDetails: [],
    spellcasting: {
      ability: "",
      saveDc: 0,
      attackBonus: 0,
      slots: Object.fromEntries(slotLevels.map((level) => [level, { max: 0, current: 0 }])),
      pactSlots: { slotLevel: 0, max: 0, current: 0 },
      spellsKnown: [],
      spellsPrepared: []
    },
    resources: [],
    personality: { traits: "", ideals: "", bonds: "", flaws: "" },
    appearance: { age: "", height: "", weight: "", eyes: "", skin: "", hair: "" },
    notes: ""
  };
}

function cloneCharacter(character: Character): Character {
  return JSON.parse(JSON.stringify(character)) as Character;
}

function omitId(character: Character): Partial<Character> {
  const { id: _id, ...updates } = character;
  return updates;
}

function numberValue(value: string | number): number {
  const parsed = typeof value === "number" ? value : Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : 0;
}

function listToText(items: string[]): string {
  return items.join("\n");
}

function textToList(value: string): string[] {
  return value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function summarizeClass(classes?: ClassLevel[]): string {
  return (classes || []).map((item) => `${item.name} ${item.level}`).join(" / ");
}

function formatModifier(value: number): string {
  const modifier = Math.floor(value / 2);
  return modifier >= 0 ? `+${modifier}` : String(modifier);
}

function buildAbilities(attributes: Record<string, number>, current?: Character["abilities"]): Character["abilities"] {
  return Object.fromEntries(
    abilityKeys.map((key) => {
      const score = attributes[key] ?? 10;
      return [
        key,
        {
          score,
          modifier: Math.floor((score - 10) / 2),
          saveProficient: current?.[key]?.saveProficient || false
        }
      ];
    })
  ) as Character["abilities"];
}

function blankAttack(): CharacterAttack {
  return {
    name: "",
    ability: "STR",
    proficient: true,
    extraAttackBonus: 0,
    damageDice: "1d8",
    damageAbility: true,
    extraDamageBonus: 0,
    damageType: "",
    range: "",
    notes: ""
  };
}

function getAttackDetails(character: Character): CharacterAttack[] {
  if (character.attackDetails?.length) {
    return character.attackDetails.map((attack) => ({ ...blankAttack(), ...attack }));
  }
  return character.attacks.map((attack) => legacyAttackToDetail(attack, character));
}

function legacyAttackToDetail(value: string, character: Character): CharacterAttack {
  const hitMatch = value.match(/([+-]\d+)/);
  const damageMatch = value.match(/(\d+d\d+(?:[+-]\d+)?)/i);
  const hitBonus = hitMatch ? numberValue(hitMatch[1]) : 0;
  const ability = closestAbilityForBonus(hitBonus, character);
  const abilityMod = abilityModifier(character, ability);
  const damageBonusMatch = damageMatch?.[1].match(/[+-]\d+$/);
  const parsedDamageBonus = damageBonusMatch ? numberValue(damageBonusMatch[0]) : 0;
  const damageDice = damageMatch?.[1].replace(/[+-]\d+$/, "") || "1d8";

  return {
    ...blankAttack(),
    name: value.split(/[+-]\d+/)[0]?.trim() || value,
    ability,
    extraAttackBonus: hitBonus - abilityMod - (character.proficiencyBonus || 0),
    damageDice,
    damageAbility: parsedDamageBonus === abilityMod && parsedDamageBonus !== 0,
    extraDamageBonus: parsedDamageBonus === abilityMod ? 0 : parsedDamageBonus,
    notes: value
  };
}

function closestAbilityForBonus(targetBonus: number, character: Character): AbilityKey {
  return abilityKeys.reduce((best, key) => {
    const bestDiff = Math.abs(abilityModifier(character, best) + (character.proficiencyBonus || 0) - targetBonus);
    const nextDiff = Math.abs(abilityModifier(character, key) + (character.proficiencyBonus || 0) - targetBonus);
    return nextDiff < bestDiff ? key : best;
  }, "STR" as AbilityKey);
}

function abilityModifier(character: Character, ability: AbilityKey): number {
  return Math.floor(((character.attributes[ability] ?? 10) - 10) / 2);
}

function attackBonus(attack: CharacterAttack, character: Character): number {
  return (
    abilityModifier(character, attack.ability) +
    (attack.proficient ? character.proficiencyBonus || 0 : 0) +
    numberValue(attack.extraAttackBonus)
  );
}

function damageBonus(attack: CharacterAttack, character: Character): number {
  return (
    (attack.damageAbility ? abilityModifier(character, attack.ability) : 0) +
    numberValue(attack.extraDamageBonus)
  );
}

function summarizeAttack(attack: CharacterAttack, character: Character): string {
  const damage = formatDamage(attack, character);
  const range = attack.range ? ` ${attack.range}` : "";
  const type = attack.damageType ? ` ${attack.damageType}` : "";
  return `${attack.name || "Attack"} ${formatSigned(attackBonus(attack, character))} ${damage}${type}${range}`.trim();
}

function formatDamage(attack: CharacterAttack, character: Character): string {
  const bonus = damageBonus(attack, character);
  return `${attack.damageDice || "1d8"}${bonus ? formatSigned(bonus) : ""}`;
}

function formatSigned(value: number): string {
  return value >= 0 ? `+${value}` : String(value);
}

function getActionDetails(character: Character): CharacterActionDetail[] {
  if (character.actionDetails?.length) {
    return character.actionDetails;
  }
  return (character.actions || []).map((action) => ({
    name: action,
    cost: "action",
    description: ""
  }));
}

function summarizeActionDetail(action: CharacterActionDetail): string {
  const cost = action.cost ? ` (${action.cost})` : "";
  const description = action.description ? `: ${action.description}` : "";
  return `${action.name || "Action"}${cost}${description}`;
}

function getFeatureDetails(character: Character, field: "features" | "traits"): CharacterFeatureDetail[] {
  const detailField = field === "features" ? character.featureDetails : character.traitDetails;
  if (detailField?.length) {
    return detailField;
  }
  return (character[field] || []).map((feature) => ({
    name: feature,
    source: "",
    description: ""
  }));
}

function summarizeFeatureDetail(feature: CharacterFeatureDetail): string {
  const source = feature.source ? ` (${feature.source})` : "";
  const description = feature.description ? `: ${feature.description}` : "";
  return `${feature.name || "Feature"}${source}${description}`;
}

function updateAt<T>(items: T[], index: number, value: T): T[] {
  return items.map((item, itemIndex) => (itemIndex === index ? value : item));
}

function removeAt<T>(items: T[], index: number): T[] {
  return items.filter((_, itemIndex) => itemIndex !== index);
}

function withCurrentOption(options: string[], current: string): string[] {
  if (!current || options.includes(current)) {
    return options;
  }
  return [current, ...options];
}

function uniqueCharacterId(baseId: string, characters: Character[]): string {
  const existing = new Set(characters.map((character) => character.id.toLowerCase()));
  if (!existing.has(baseId.toLowerCase())) {
    return baseId;
  }
  let index = 2;
  while (existing.has(`${baseId}-${index}`.toLowerCase())) {
    index += 1;
  }
  return `${baseId}-${index}`;
}

function ensureProficiencies(character: Character) {
  character.proficiencies ||= { armor: [], weapons: [], tools: [] };
  return character.proficiencies;
}

function ensureSpellcasting(character: Character) {
  character.spellcasting ||= {
    ability: "",
    saveDc: 0,
    attackBonus: 0,
    slots: Object.fromEntries(slotLevels.map((level) => [level, { max: 0, current: 0 }])),
    pactSlots: { slotLevel: 0, max: 0, current: 0 },
    spellsKnown: [],
    spellsPrepared: []
  };
  character.spellcasting.pactSlots ||= { slotLevel: 0, max: 0, current: 0 };
  return character.spellcasting;
}

function ensureSpellSlot(character: Character, level: string) {
  const spellcasting = ensureSpellcasting(character);
  spellcasting.slots[level] ||= { max: 0, current: 0 };
  return spellcasting.slots[level];
}

function ensureEquipment(character: Character) {
  character.equipment ||= { items: [], attunedItems: [], carryingCapacity: 0 };
  return character.equipment;
}

function ensureCurrency(character: Character) {
  character.currency ||= { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 };
  return character.currency;
}

function ensurePersonality(character: Character) {
  character.personality ||= { traits: "", ideals: "", bonds: "", flaws: "" };
  return character.personality;
}
