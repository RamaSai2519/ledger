package com.ledgerapp.mobile.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Telephony
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileWriter

/**
 * LED-18 dev-only tool: lives entirely under src/debug/, so Gradle's debug
 * source set/manifest merge means it is compiled and registered ONLY in
 * debug builds — this class and its manifest `<receiver>`/`<uses-permission
 * android:name="READ_SMS">` entry (debug/AndroidManifest.xml) never ship in
 * a release build, addressing spec Part 16's ask for a debug-helper
 * exporter rather than relying solely on `adb shell content query`, which
 * is unreliable/restricted on many OEM ROMs.
 *
 * Triggered from the dev machine with:
 *   adb shell am broadcast -a com.ledgerapp.mobile.dev.EXPORT_SMS \
 *     -n com.ledgerapp.mobile/.sms.SmsExportReceiver
 * then pulled with:
 *   adb pull /sdcard/Android/data/com.ledgerapp.mobile/files/sms_export.json
 *
 * Reuses the same READ_SMS permission the app already requests for its
 * production SMS pipeline (plan.md §7) — this receiver does not read
 * anything the app couldn't already read, it just also writes it to a file
 * ADB can retrieve, for local development use only.
 */
class SmsExportReceiver : BroadcastReceiver() {
    companion object {
        const val ACTION_EXPORT_SMS = "com.ledgerapp.mobile.dev.EXPORT_SMS"
        private const val TAG = "SmsExportReceiver"
        private const val EXPORT_FILENAME = "sms_export.json"
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != ACTION_EXPORT_SMS) return

        try {
            val messages = readAllSms(context)
            writeExportFile(context, messages)
            Log.i(TAG, "exported ${messages.length()} SMS to $EXPORT_FILENAME")
        } catch (e: Exception) {
            Log.e(TAG, "SMS export failed", e)
        }
    }

    private fun readAllSms(context: Context): JSONArray {
        val messages = JSONArray()
        val projection = arrayOf("_id", "address", "body", "date", "thread_id", "sub_id")
        val cursor = context.contentResolver.query(
            Uri.parse("content://sms/"),
            projection,
            null,
            null,
            "date DESC",
        ) ?: return messages

        cursor.use {
            val idIdx = it.getColumnIndex("_id")
            val addressIdx = it.getColumnIndex("address")
            val bodyIdx = it.getColumnIndex("body")
            val dateIdx = it.getColumnIndex("date")
            val threadIdx = it.getColumnIndex("thread_id")
            val subIdx = it.getColumnIndex("sub_id")

            while (it.moveToNext()) {
                val entry = JSONObject()
                entry.put("id", if (idIdx >= 0) it.getLong(idIdx) else JSONObject.NULL)
                entry.put("address", if (addressIdx >= 0) it.getString(addressIdx) else JSONObject.NULL)
                entry.put("body", if (bodyIdx >= 0) it.getString(bodyIdx) else JSONObject.NULL)
                entry.put("date_millis", if (dateIdx >= 0) it.getLong(dateIdx) else JSONObject.NULL)
                entry.put("thread_id", if (threadIdx >= 0) it.getLong(threadIdx) else JSONObject.NULL)
                entry.put("sub_id", if (subIdx >= 0) it.getLong(subIdx) else JSONObject.NULL)
                messages.put(entry)
            }
        }
        return messages
    }

    private fun writeExportFile(context: Context, messages: JSONArray) {
        val dir = context.getExternalFilesDir(null) ?: return
        val file = File(dir, EXPORT_FILENAME)
        FileWriter(file).use { writer ->
            writer.write(messages.toString())
        }
    }
}
