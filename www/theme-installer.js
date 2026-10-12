// ThemeInstaller JavaScript bridge
window.ThemeInstaller = {
  install: async ({ themeKey }) => {
    if (!window.Capacitor || !window.Capacitor.Plugins) {
      throw new Error('ThemeInstaller only available on Android device');
    }
    const plugin = window.Capacitor.Plugins.ThemeInstaller;
    if (!plugin) {
      throw new Error('ThemeInstaller native plugin not registered');
    }
    return await plugin.install({ themeKey });
  }
};

// Register with Capacitor's plugin proxy
if (window.Capacitor) {
  window.Capacitor.Plugins.ThemeInstaller = {
    install: async (options) => {
      return await window.ThemeInstaller.install(options);
    }
  };
}
