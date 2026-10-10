import { signal } from "@preact/signals";

const DISMISS_KEY = "notificationsDismissed";

export const notificationsSupported =
  typeof window !== "undefined" && "Notification" in window;

const readDismissed = (): boolean => {
  if (typeof localStorage === "undefined") return false;
  try {
    return localStorage.getItem(DISMISS_KEY) === "1";
  } catch (_) {
    return false;
  }
};

export const notificationPermission = signal<NotificationPermission | "unsupported">(
  notificationsSupported ? Notification.permission : "unsupported",
);
export const notificationPromptDismissed = signal<boolean>(readDismissed());

export const dismissNotificationPrompt = () => {
  notificationPromptDismissed.value = true;
  try {
    localStorage.setItem(DISMISS_KEY, "1");
  } catch (_) {
    // ignore
  }
};

export const enableNotifications = async () => {
  if (!notificationsSupported) return;
  try {
    notificationPermission.value = await Notification.requestPermission();
  } catch (_) {
    // ignore
  }
  // Don't keep asking if the user blocked notifications.
  if (notificationPermission.value !== "granted") dismissNotificationPrompt();
};

// Only notify when the page is not open in front of the user. Merely
// losing focus (window visible but not active) still counts as "open",
// so we look at tab visibility, not focus.
export const notify = (title: string, body?: string) => {
  if (!notificationsSupported) return;
  if (notificationPermission.value !== "granted") return;
  if (document.visibilityState !== "hidden") return;
  try {
    new Notification(title, { body });
  } catch (_) {
    // ignore
  }
};
