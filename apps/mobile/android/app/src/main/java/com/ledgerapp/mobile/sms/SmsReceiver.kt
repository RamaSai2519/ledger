package com.ledgerapp.mobile.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import androidx.work.Constraints
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.workDataOf
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * Manifest-registered (not JS/dynamically registered) so it keeps working
 * even when the app is backgrounded or killed (plan.md §13, §3, LED-7
 * mobile scope). Filters against SmsAllowlist client-side, before anything
 * touches the network — CLAUDE.md's data-minimization constraint (plan.md
 * §2.3) is enforced right here, not downstream.
 */
class SmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return

        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (messages.isNullOrEmpty()) return

        // A multipart SMS arrives as several PDUs for the same logical
        // message; concatenate bodies but they all share one sender.
        val senderId = messages[0].originatingAddress ?: return
        if (!SmsAllowlist.isAllowed(senderId)) return

        val rawText = messages.joinToString(separator = "") { it.messageBody ?: "" }
        if (rawText.isBlank()) return

        val receivedAt = isoFormat().format(Date(messages[0].timestampMillis))

        val request = OneTimeWorkRequestBuilder<SmsIngestWorker>()
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .setInputData(
                workDataOf(
                    SmsIngestWorker.KEY_SENDER_ID to senderId,
                    SmsIngestWorker.KEY_RAW_TEXT to rawText,
                    SmsIngestWorker.KEY_RECEIVED_AT to receivedAt,
                ),
            )
            .build()

        // Unique-by-timestamp+sender-ish key would be nicer, but APPEND is
        // enough here: WorkManager already dedups retries of the *same*
        // enqueued request, and true duplicate-SMS dedup is handled
        // server-side (plan.md §7 step 11) against actual transactions.
        WorkManager.getInstance(context.applicationContext)
            .enqueueUniqueWork(
                "sms-ingest-${System.currentTimeMillis()}-$senderId",
                ExistingWorkPolicy.APPEND_OR_REPLACE,
                request,
            )
    }

    private fun isoFormat(): SimpleDateFormat =
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }
}
