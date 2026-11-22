import type { CapacitorConfig } from "@capacitor/cli";

const remoteOrigin = "https://spymaster.jmft.dev/";

const config: CapacitorConfig = {
  appId: "dev.jmft.spymaster",
  appName: "Spymaster",
  webDir: "dist/frontend",
  server: {
    url: remoteOrigin,
    allowNavigation: [new URL(remoteOrigin).host],
  },
};

export default config;
