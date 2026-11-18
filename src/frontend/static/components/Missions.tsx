export const MissionButton = ({
  value,
  disabled,
}: {
  value: number;
  disabled?: boolean;
}) => (
  <button class="btn btn-warning mission" disabled={disabled}>
    {String(value)}
  </button>
);

type RemainingMissionsProps = {
  remainingMissions: number[];
  currentMission: number | null;
  missionRevealed: boolean;
};

export const RemainingMissions = ({
  remainingMissions,
  currentMission,
  missionRevealed,
}: RemainingMissionsProps) => (
  <div class="d-flex flex-column justify-content-center align-items-center mb-md-3">
    <span class="d-none d-md-block">Remaining missions</span>
    <div class="d-flex flex-column flex-md-row justify-content-center align-items-center">
      {Array.from({ length: 16 }, (_, i) => {
        const value = i + 1;
        const remaining = remainingMissions.includes(value);
        // Keep the drawn mission looking like it is still to come
        // until the player acknowledges it.
        const hiddenCurrent = !missionRevealed && value === currentMission;
        return (
          <MissionButton
            key={i}
            value={value}
            disabled={!remaining && !hiddenCurrent}
          />
        );
      })}
    </div>
  </div>
);
