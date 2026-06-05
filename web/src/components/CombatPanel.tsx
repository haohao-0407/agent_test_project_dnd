import type { CombatState, PendingAction, Player, Token } from "../api/types";

type CombatPanelProps = {
  combat: CombatState;
  pendingActions: PendingAction[];
  tokens: Token[];
  currentUser: Player;
  currentUserId: string;
  onStartCombat: () => void;
  onEndTurn: () => void;
  onConfirmPending: (actionId: string) => void;
  onDeclinePending: (actionId: string) => void;
};

export function CombatPanel({
  combat,
  pendingActions,
  tokens,
  currentUser,
  currentUserId,
  onStartCombat,
  onEndTurn,
  onConfirmPending,
  onDeclinePending
}: CombatPanelProps) {
  const currentActorId = combat.active ? combat.initiativeOrder[combat.turnIndex]?.actorId : null;
  const currentToken = tokens.find((token) => token.actorId === currentActorId || token.id === currentActorId);
  const currentTurnState = currentActorId ? combat.turnState[currentActorId] : null;
  const visiblePending = pendingActions.filter((action) => {
    if (action.status !== "pending") return false;
    if (currentUser.role === "dm") return true;
    return action.actorId === currentUser.characterId;
  });

  return (
    <section className="combat-panel" aria-labelledby="combat-title">
      <div className="panel-header compact">
        <div>
          <p className="eyebrow">Combat</p>
          <h2 id="combat-title">{combat.active ? `Round ${combat.round}` : "Ready"}</h2>
        </div>
        <div className="combat-actions">
          {combat.active ? (
            <button type="button" onClick={onEndTurn}>
              End turn
            </button>
          ) : currentUser.role === "dm" ? (
            <button type="button" onClick={onStartCombat}>
              Start
            </button>
          ) : null}
        </div>
      </div>
      <div className="combat-body">
        <div className="turn-card">
          <span>Turn</span>
          <strong>{currentToken?.name || currentActorId || "None"}</strong>
          {currentTurnState ? (
            <div className="action-economy">
              <span className={currentTurnState.actionAvailable ? "" : "spent"}>Action</span>
              <span className={currentTurnState.bonusActionAvailable ? "" : "spent"}>Bonus</span>
              <span className={currentTurnState.reactionAvailable ? "" : "spent"}>Reaction</span>
              <span>{currentTurnState.movementMax - currentTurnState.movementUsed} ft</span>
            </div>
          ) : null}
        </div>
        <ol className="initiative-list">
          {combat.initiativeOrder.map((entry, index) => {
            const token = tokens.find((item) => item.actorId === entry.actorId || item.id === entry.actorId);
            return (
              <li className={index === combat.turnIndex && combat.active ? "active" : ""} key={entry.actorId}>
                <span>{token?.name || entry.name || entry.actorId}</span>
                <strong>{entry.initiative}</strong>
              </li>
            );
          })}
        </ol>
        {visiblePending.length > 0 ? (
          <div className="pending-list">
            {visiblePending.map((action) => (
              <div className="pending-action" key={action.id}>
                <span>{action.summary || action.type}</span>
                <div>
                  <button type="button" onClick={() => onConfirmPending(action.id)}>
                    Confirm
                  </button>
                  <button type="button" onClick={() => onDeclinePending(action.id)}>
                    Decline
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="pending-empty">{combat.active ? "No pending actions." : "Combat is inactive."}</p>
        )}
      </div>
    </section>
  );
}
