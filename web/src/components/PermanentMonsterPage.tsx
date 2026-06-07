import { useEffect, useMemo, useState } from "react";
import {
  ApiError,
  createPermanentMonster,
  getPermanentMonsters,
  logout,
  me,
  updatePermanentMonster,
  type AuthSession
} from "../api/client";
import type { AbilityKey, MonsterCard } from "../api/types";
import { JoinScreen } from "./JoinScreen";

const abilityKeys: AbilityKey[] = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];

const basicFields: Array<{ key: keyof MonsterCard; label: string }> = [
  { key: "name", label: "名称" },
  { key: "source", label: "来源" },
  { key: "page", label: "页码" },
  { key: "size", label: "体型" },
  { key: "type", label: "类型" },
  { key: "alignment", label: "阵营" },
  { key: "armorClass", label: "AC" },
  { key: "hitPoints", label: "HP" },
  { key: "speed", label: "速度" },
  { key: "challengeRating", label: "CR" }
];

const defenseFields: Array<{ key: keyof MonsterCard; label: string }> = [
  { key: "savingThrows", label: "豁免骰" },
  { key: "skills", label: "技能" },
  { key: "damageVulnerabilities", label: "伤害易伤" },
  { key: "damageResistances", label: "伤害抗性" },
  { key: "damageImmunities", label: "伤害免疫" },
  { key: "conditionImmunities", label: "状态免疫" },
  { key: "senses", label: "感官" },
  { key: "languages", label: "语言" }
];

const blockFields: Array<{ key: keyof MonsterCard; label: string }> = [
  { key: "traits", label: "特质" },
  { key: "actions", label: "动作" },
  { key: "bonusActions", label: "附赠动作" },
  { key: "reactions", label: "反应" },
  { key: "legendaryActions", label: "传奇动作" },
  { key: "mythicActions", label: "神话动作" },
  { key: "lairActions", label: "巢穴动作" },
  { key: "regionalEffects", label: "区域效应" },
  { key: "environment", label: "环境" },
  { key: "treasure", label: "宝藏" },
  { key: "notes", label: "备注" }
];

export function PermanentMonsterPage() {
  const [monsters, setMonsters] = useState<MonsterCard[]>([]);
  const [identity, setIdentity] = useState<AuthSession | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [selectedId, setSelectedId] = useState("");
  const [draft, setDraft] = useState<MonsterCard>(() => createBlankMonster());
  const [isNew, setIsNew] = useState(true);
  const [dirty, setDirty] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const selectedMonster = useMemo(
    () => monsters.find((monster) => monster.id === selectedId) || monsters[0],
    [monsters, selectedId]
  );

  useEffect(() => {
    me()
      .then((session) => {
        setIdentity(session);
        return loadMonsters();
      })
      .catch((apiError: Error) => {
        if (apiError instanceof ApiError && apiError.status === 401) {
          setIdentity(null);
          return;
        }
        setError(apiError.message);
      })
      .finally(() => setAuthChecked(true));
  }, []);

  useEffect(() => {
    if (!selectedMonster || dirty) return;
    setDraft(cloneMonster(selectedMonster));
    setIsNew(false);
  }, [dirty, selectedMonster]);

  async function loadMonsters() {
    const payload = await getPermanentMonsters();
    setMonsters(payload.monsters);
    setSelectedId(payload.monsters[0]?.id || "");
    if (payload.monsters[0]) {
      setDraft(cloneMonster(payload.monsters[0]));
      setIsNew(false);
      setDirty(false);
    }
  }

  async function handleJoined(session: AuthSession) {
    setIdentity(session);
    await loadMonsters();
  }

  async function handleLogout() {
    await logout();
    setIdentity(null);
    setMonsters([]);
  }

  function selectMonster(monster: MonsterCard) {
    setSelectedId(monster.id);
    setDraft(cloneMonster(monster));
    setIsNew(false);
    setDirty(false);
    setNotice(null);
  }

  function startNewMonster() {
    const next = createBlankMonster();
    setSelectedId(next.id);
    setDraft(next);
    setIsNew(true);
    setDirty(true);
    setNotice(null);
  }

  function updateDraft(updater: (next: MonsterCard) => void) {
    setDraft((current) => {
      const next = cloneMonster(current);
      updater(next);
      return next;
    });
    setDirty(true);
    setNotice(null);
  }

  async function saveDraft() {
    setSaving(true);
    setNotice(null);
    try {
      const payload = isNew
        ? await createPermanentMonster({ monster: draft })
        : await updatePermanentMonster({ monsterId: draft.id, updates: omitId(draft) });
      setMonsters(payload.monsters);
      setDraft(cloneMonster(payload.monster));
      setSelectedId(payload.monster.id);
      setIsNew(false);
      setDirty(false);
      setNotice("已保存");
    } catch (saveError) {
      setNotice(saveError instanceof Error ? saveError.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  if (error) {
    return <main className="app-shell">{error}</main>;
  }

  if (!authChecked) {
    return <main className="app-shell">Loading monster library...</main>;
  }

  if (!identity) {
    return <JoinScreen title="Join to edit the monster library" onJoined={(session) => void handleJoined(session)} />;
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Monster Library</p>
          <h1>怪物库</h1>
        </div>
        <div className="session-strip">
          <span>{identity.player?.displayName || identity.userId}</span>
          <a className="nav-link" href="/">返回战棋</a>
          <a className="nav-link" href="/characters/permanent">永久角色库</a>
          <button type="button" onClick={() => void handleLogout()}>
            Logout
          </button>
        </div>
      </header>

      <section className="character-page" aria-labelledby="monster-page-title">
        <aside className="character-sidebar">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Monster Cards</p>
              <h2 id="monster-page-title">怪物卡</h2>
            </div>
            <button type="button" onClick={startNewMonster}>
              新建
            </button>
          </div>
          <div className="character-picker">
            {monsters.map((monster) => (
              <button
                type="button"
                className={monster.id === draft.id && !isNew ? "active" : ""}
                key={monster.id}
                onClick={() => selectMonster(monster)}
              >
                <strong>{monster.name}</strong>
                <span>{monster.size || "未知体型"} / {monster.type || "未知类型"} / CR {monster.challengeRating || "-"}</span>
              </button>
            ))}
            {isNew ? (
              <button type="button" className="active">
                <strong>{draft.name}</strong>
                <span>{draft.size || "未知体型"} / {draft.type || "未知类型"} / CR {draft.challengeRating || "-"}</span>
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
              <p className="eyebrow">Monster Manual Format</p>
              <h2>{draft.name || "未命名怪物"}</h2>
            </div>
            <div className="toolbar-actions">
              {notice ? <span className="save-notice">{notice}</span> : null}
              <button type="submit" disabled={saving || !dirty}>
                {saving ? "保存中" : "保存"}
              </button>
            </div>
          </div>

          <div className="editor-scroll">
            <section className="sheet-section">
              <h3>基础</h3>
              <div className="form-grid five monster-basic-grid">
                {basicFields.map((field) => (
                  <TextField
                    key={field.key}
                    label={field.label}
                    value={String(draft[field.key] || "")}
                    onChange={(value) => updateDraft((next) => {
                      setMonsterTextField(next, field.key, value);
                    })}
                  />
                ))}
              </div>
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
                    <strong>{formatModifier(draft.attributes[key] ?? 10)}</strong>
                  </label>
                ))}
              </div>
            </section>

            <section className="sheet-section">
              <h3>防御与感知</h3>
              <div className="form-grid four">
                {defenseFields.map((field) => (
                  <TextField
                    key={field.key}
                    label={field.label}
                    value={String(draft[field.key] || "")}
                    onChange={(value) => updateDraft((next) => {
                      setMonsterTextField(next, field.key, value);
                    })}
                  />
                ))}
              </div>
            </section>

            <section className="sheet-section">
              <h3>能力文本</h3>
              <div className="form-grid two">
                {blockFields.map((field) => (
                  <TextArea
                    key={field.key}
                    label={field.label}
                    value={String(draft[field.key] || "")}
                    onChange={(value) => updateDraft((next) => {
                      setMonsterTextField(next, field.key, value);
                    })}
                  />
                ))}
              </div>
            </section>
          </div>
        </form>
      </section>
    </main>
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

function TextArea({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function createBlankMonster(): MonsterCard {
  const id = `monster-${Date.now()}`;
  return {
    id,
    name: "新怪物",
    source: "MM'25",
    page: "",
    size: "中型",
    type: "",
    alignment: "无阵营",
    armorClass: "10",
    hitPoints: "1",
    speed: "30 尺",
    attributes: { STR: 10, DEX: 10, CON: 10, INT: 10, WIS: 10, CHA: 10 },
    savingThrows: "",
    skills: "",
    damageVulnerabilities: "",
    damageResistances: "",
    damageImmunities: "",
    conditionImmunities: "",
    senses: "被动察觉 10",
    languages: "—",
    challengeRating: "",
    traits: "",
    actions: "",
    bonusActions: "",
    reactions: "",
    legendaryActions: "",
    mythicActions: "",
    lairActions: "",
    regionalEffects: "",
    environment: "",
    treasure: "",
    notes: ""
  };
}

function cloneMonster(monster: MonsterCard): MonsterCard {
  return JSON.parse(JSON.stringify(monster)) as MonsterCard;
}

function setMonsterTextField(monster: MonsterCard, key: keyof MonsterCard, value: string): void {
  (monster as unknown as Record<string, string>)[key] = value;
}

function omitId(monster: MonsterCard): Partial<MonsterCard> {
  const { id: _id, ...updates } = monster;
  return updates;
}

function numberValue(value: string | number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatModifier(score: number): string {
  const modifier = Math.floor((score - 10) / 2);
  return modifier >= 0 ? `+${modifier}` : String(modifier);
}
