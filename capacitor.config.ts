import type { CapacitorConfig } from "@capacitor/cli";

const remoteOrigin = "https://spymaster.fastapicloud.dev/";

const config: CapacitorConfig = {
  appId: "com.jmftsang.spymaster",
  appName: "Spymaster",
  webDir: "dist/frontend",
  server: {
    url: remoteOrigin,
    allowNavigation: [new URL(remoteOrigin).host],
  },
};

export default config;
