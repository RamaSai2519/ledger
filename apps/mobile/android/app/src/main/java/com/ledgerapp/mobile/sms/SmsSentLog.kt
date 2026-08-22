package com.ledgerapp.mobile.sms

import android.content.Context

/**
 * Tracks which SMS have already been successfully forwarded to
 * /sms/ingest, keyed by "$senderId|$receivedAtIso" (the same pair every
 * ingest path already carries — no message content stored here, just a
 * dedup marker). SmsIngestWorker marks a key sent on a 2xx response;
 * SmsReconciliationWorker consults this before re-submitting an
 * allow-listed message it finds during its periodic inbox re-scan, so a
 * message already delivered by the real-time SmsReceiver path never gets
 * a duplicate suggestion.
 *
 * Capped at MAX_ENTRIES, dropping oldest-inserted first (SharedPreferences
 * has no ordering, so this uses an explicit insertion-order list) — the
 * reconciliation window is only ~48h of messages, so this cap is generous
 * headroom, not a tight budget.
 */
object SmsSentLog {
    private const val PREFS_NAME = "ledger_sms_sent_log"
    private const val KEY_ORDER = "order"
    private const val MAX_ENTRIES = 500

    fun key(senderId: String, receivedAtIso: String): String = "$senderId|$receivedAtIso"

    fun markSent(context: Context, key: String) {
        val prefs = prefs(context)
        if (prefs.getBoolean(key, false)) return
        val order = (prefs.getString(KEY_ORDER, null)?.split(",")?.filter { it.isNotEmpty() } ?: emptyList()) + key
        val trimmed = if (order.size > MAX_ENTRIES) order.drop(order.size - MAX_ENTRIES) else order
        val dropped = order - trimmed.toSet()

        val editor = prefs.edit()
        editor.putBoolean(key, true)
        dropped.forEach { editor.remove(it) }
        editor.putString(KEY_ORDER, trimmed.joinToString(","))
        editor.apply()
    }

    fun hasSent(context: Context, key: String): Boolean = prefs(context).getBoolean(key, false)

    private fun prefs(context: Context) =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
}
