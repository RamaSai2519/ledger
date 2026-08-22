package com.ledgerapp.mobile.sms

import android.content.Intent
import android.net.Uri
import android.os.PowerManager
import android.provider.Settings
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

/**
 * LED-31: JS-facing bridge for the one user-grantable lever against
 * Doze/App Standby deferring the WorkManager job that actually forwards
 * an already-received SMS — see SettingsScreen's "SMS reliability" row.
 * There's no way to force this from code; the system dialog always
 * requires an explicit tap, so this only ever opens it.
 */
class SmsReliabilityModule(reactContext: ReactApplicationContext) : ReactContextBaseJavaModule(reactContext) {
    override fun getName(): String = "SmsReliabilityModule"

    @ReactMethod
    fun isIgnoringBatteryOptimizations(promise: Promise) {
        val powerManager = reactApplicationContext.getSystemService(PowerManager::class.java)
        promise.resolve(powerManager?.isIgnoringBatteryOptimizations(reactApplicationContext.packageName) ?: false)
    }

    @ReactMethod
    fun requestIgnoreBatteryOptimizations() {
        val intent = Intent(
            Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS,
            Uri.parse("package:${reactApplicationContext.packageName}"),
        ).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        reactApplicationContext.startActivity(intent)
    }
}
