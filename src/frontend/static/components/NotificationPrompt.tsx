import {
  notificationsSupported,
  notificationPermission,
  notificationPromptDismissed,
  enableNotifications,
  dismissNotificationPrompt,
} from "../notifications";

export const NotificationPrompt = () => {
  if (!notificationsSupported) return null;
  if (notificationPromptDismissed.value) return null;
  if (notificationPermission.value !== "default") return null;

  return (
    <div class="alert alert-secondary d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
      <span>
        Would you like browser notifications when you are challenged or when a
        game needs your attention?
      </span>
      <span class="d-flex gap-2">
        <button
          class="btn btn-sm btn-outline-dark"
          onClick={dismissNotificationPrompt}
        >
          No thanks
        </button>
        <button class="btn btn-sm btn-primary" onClick={enableNotifications}>
          Enable notifications
        </button>
      </span>
    </div>
  );
};
