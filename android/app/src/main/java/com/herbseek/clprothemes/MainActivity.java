package com.herbseek.clprothemes;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;
import com.herbseek.themeinstaller.ThemeInstallerPlugin;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(ThemeInstallerPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
