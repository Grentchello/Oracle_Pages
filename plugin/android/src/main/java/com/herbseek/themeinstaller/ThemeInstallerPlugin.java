package com.herbseek.themeinstaller;

import android.content.ContentValues;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

@CapacitorPlugin(name = "ThemeInstaller")
public class ThemeInstallerPlugin extends Plugin {

    @PluginMethod
    public void install(PluginCall call) {
        String themeKey = call.getString("themeKey");
        if (themeKey == null) {
            call.reject("themeKey is required");
            return;
        }
        try {
            // Get the theme.json from assets
            String themeJson;
            try (InputStream is = getContext().getAssets().open("public/themes/" + themeKey + "/theme.json")) {
                byte[] buffer = new byte[is.available()];
                is.read(buffer);
                themeJson = new String(buffer, "UTF-8");
            }

            // Use scoped storage on Android 10+; legacy file API on lower
            File themeDir;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                // /sdcard/C_Theme/Launcher/<themeKey>/
                // On Android 10+, direct /sdcard access is restricted.
                // We'll write to the app's external files dir which is accessible to the user via Files app
                themeDir = new File(getContext().getExternalFilesDir(null), "C_Theme/Launcher/" + themeKey);
            } else {
                themeDir = new File(Environment.getExternalStorageDirectory(), "C_Theme/Launcher/" + themeKey);
            }
            themeDir.mkdirs();

            File outFile = new File(themeDir, "theme.json");
            try (FileOutputStream fos = new FileOutputStream(outFile)) {
                fos.write(themeJson.getBytes("UTF-8"));
            }

            // Also write a .horizontal file (CL Pro reads this as the legacy format)
            File horizFile = new File(themeDir, themeKey + ".horizontal");
            try (FileOutputStream fos = new FileOutputStream(horizFile)) {
                String header = "CL_THEME_v1\n";
                String body = "{\"theme\":" + themeJson + "}\n";
                fos.write(header.getBytes("UTF-8"));
                fos.write(body.getBytes("UTF-8"));
            }

            JSObject ret = new JSObject();
            ret.put("success", true);
            ret.put("path", outFile.getAbsolutePath());
            ret.put("message", "Theme installed! In Car Launcher Pro: Edit Theme → Restore → choose '" + themeKey + ".horizontal'");
            call.resolve(ret);
        } catch (Exception e) {
            call.reject("Install failed: " + e.getMessage(), e);
        }
    }
}
