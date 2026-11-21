import { Capacitor } from "@capacitor/core";
import { LocalNotifications } from "@capacitor/local-notifications";
import { signal } from "@preact/signals";

const DISMISS_KEY = "notificationsDismissed";
const isNative = Capacitor.isNativePlatform();

// The prompt's dismiss flag is local-only. Actual permission is controlled by
// the browser or by the device's OS settings.
const readDismissed = (): boolean => {
  if (typeof localStorage === "undefined") return false;
  try {
    return localStorage.getItem(DISMISS_KEY) === "1";
  } catch (_) {
    return false;
  }
};

const toPermission = (state: string): NotificationPermission => {
  if (state === "granted") return "granted";
  if (state === "denied") return "denied";
  return "default";
};

const webPermission = (): NotificationPermission | "unsupported" => {
  if (typeof window === "undefined" || !("Notification" in window)) {
    return "unsupported";
  }
  return Notification.permission;
};

export const notificationsSupported = isNative || webPermission() !== "unsupported";
export const notificationKind = isNative
  ? "device notifications"
  : "browser notifications";

export const notificationPermission = signal<NotificationPermission | "unsupported">(
  isNative ? "default" : webPermission(),
);
export const notificationPromptDismissed = signal<boolean>(readDismissed());

if (isNative) {
  // Reflect a permission granted in a previous session instead of prompting again.
  void LocalNotifications.checkPermissions()
    .then((status) => {
      notificationPermission.value = toPermission(status.display);
    })
    .catch(() => {
      // ignore
    });
}

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
    if (isNative) {
      const status = await LocalNotifications.requestPermissions();
      notificationPermission.value = toPermission(status.display);
    } else {
      notificationPermission.value = await Notification.requestPermission();
    }
  } catch (_) {
    // ignore
  }
  // Don't keep asking if the user blocked notifications.
  if (notificationPermission.value !== "granted") dismissNotificationPrompt();
};

let nextNotificationId = 1;

export const notify = (title: string, body?: string) => {
  if (!notificationsSupported) return;
  if (notificationPermission.value !== "granted") return;

  if (isNative) {
    // The OS controls presentation; WebView visibility is not a reliable gate.
    void LocalNotifications.schedule({
      notifications: [
        {
          id: nextNotificationId++,
          title,
          body: body ?? "",
          schedule: { at: new Date(Date.now() + 500) },
        },
      ],
    }).catch(() => {
      // ignore
    });
    return;
  }

  // Only notify when the page is not open in front of the user. Merely
  // losing focus (window visible but not active) still counts as "open",
  // so we look at tab visibility, not focus.
  if (document.visibilityState !== "hidden") return;
  try {
    new Notification(title, { body });
  } catch (_) {
    // ignore
  }
};
