package com.ledgerapp.mobile.sms

import android.content.Context
import android.provider.Telephony
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.TimeUnit

/**
 * Safety net for LED-31: SmsReceiver only fires once, at the moment a
 * message physically arrives — if that single attempt is lost to a
 * process kill mid-broadcast, an OS/OEM background restriction, or any
 * failure mode not yet known, the message is gone forever with the
 * real-time path alone. This re-scans the on-device SMS inbox
 * periodically and re-enqueues ingest for anything allow-listed that
 * SmsSentLog doesn't already have recorded as delivered — the same
 * client-side allow-list gate as the real-time path, just re-applied on a
 * schedule instead of only on arrival.
 */
class SmsReconciliationWorker(appContext: Context, params: WorkerParameters) : CoroutineWorker(appContext, params) {

    companion object {
        private const val UNIQUE_PERIODIC_NAME = "sms-reconciliation"

        // Wide enough to absorb a phone being offline/off for a day or two
        // (the periodic job itself only runs ~daily) without narrow enough
        // to matter for CLAUDE.md's data-minimization purge window (~30d).
        private val LOOKBACK_MILLIS = TimeUnit.HOURS.toMillis(60)

        fun ensureScheduled(context: Context) {
            val request = PeriodicWorkRequestBuilder<SmsReconciliationWorker>(24, TimeUnit.HOURS)
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
            WorkManager.getInstance(context.applicationContext)
                .enqueueUniquePeriodicWork(UNIQUE_PERIODIC_NAME, ExistingPeriodicWorkPolicy.KEEP, request)
        }
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val cutoff = System.currentTimeMillis() - LOOKBACK_MILLIS
        val resolver = applicationContext.contentResolver
        val projection = arrayOf(Telephony.Sms.ADDRESS, Telephony.Sms.BODY, Telephony.Sms.DATE)

        val cursor = try {
            resolver.query(
                Telephony.Sms.Inbox.CONTENT_URI,
                projection,
                "${Telephony.Sms.DATE} > ?",
                arrayOf(cutoff.toString()),
                "${Telephony.Sms.DATE} DESC",
            )
        } catch (e: SecurityException) {
            // READ_SMS not granted (e.g. revoked after install) — nothing
            // to reconcile from until the user re-grants it in Settings.
            return@withContext Result.success()
        }

        cursor.use { c ->
            if (c == null) return@withContext Result.retry()

            val addressIdx = c.getColumnIndexOrThrow(Telephony.Sms.ADDRESS)
            val bodyIdx = c.getColumnIndexOrThrow(Telephony.Sms.BODY)
            val dateIdx = c.getColumnIndexOrThrow(Telephony.Sms.DATE)

            val workManager = WorkManager.getInstance(applicationContext)

            while (c.moveToNext()) {
                val senderId = c.getString(addressIdx) ?: continue
                if (!SmsAllowlist.isAllowed(senderId)) continue

                val rawText = c.getString(bodyIdx)
                if (rawText.isNullOrBlank()) continue

                val receivedAt = SmsTiming.isoFormat(c.getLong(dateIdx))
                val key = SmsSentLog.key(senderId, receivedAt)
                if (SmsSentLog.hasSent(applicationContext, key)) continue

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

                // KEEP, same as SmsReceiver: if the real-time path already
                // has this exact message in flight, don't queue a second
                // attempt alongside it.
                workManager.enqueueUniqueWork("sms-ingest-$key", ExistingWorkPolicy.KEEP, request)
            }
        }

        Result.success()
    }
}
