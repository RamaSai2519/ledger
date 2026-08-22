package com.ledgerapp.mobile.sms

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * Shared by SmsReceiver (real-time path, from a broadcast PDU timestamp)
 * and SmsReconciliationWorker (periodic re-scan, from the SMS provider's
 * `date` column) so both produce byte-identical `received_at` strings for
 * the same physical message — SmsSentLog's dedup key depends on that.
 */
object SmsTiming {
    fun isoFormat(millis: Long): String =
        SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US)
            .apply { timeZone = TimeZone.getTimeZone("UTC") }
            .format(Date(millis))
}
