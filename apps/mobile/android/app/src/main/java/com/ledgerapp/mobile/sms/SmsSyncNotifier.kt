package com.ledgerapp.mobile.sms

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.ledgerapp.mobile.MainActivity
import com.ledgerapp.mobile.R

/**
 * Surfaces SmsIngestWorker's terminal failures to the user. Before this,
 * every failure path (dead refresh token, backend rejection, exhausted
 * retries) ended in Result.retry()/Result.failure() with at most a
 * Log.w() nobody would ever see — a bank SMS could silently stop being
 * forwarded forever with zero signal anywhere. This posts one
 * de-duplicated (fixed notification ID) system notification instead.
 */
object SmsSyncNotifier {
    private const val CHANNEL_ID = "sms_sync_issues"
    private const val NOTIFICATION_ID = 8341

    fun notifySignInRequired(context: Context) {
        show(
            context,
            title = "Bank SMS sync paused",
            text = "Ledger needs you to sign in again to keep auto-detecting bank messages.",
        )
    }

    fun notifyIngestFailing(context: Context) {
        show(
            context,
            title = "Bank SMS sync issue",
            text = "Ledger couldn't process a bank message. Open the app to check your connection.",
        )
    }

    private fun show(context: Context, title: String, text: String) {
        ensureChannel(context)

        if (ContextCompat.checkSelfPermission(context, android.Manifest.permission.POST_NOTIFICATIONS) !=
            android.content.pm.PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        val openAppIntent = Intent(context, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = PendingIntent.getActivity(
            context,
            0,
            openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .build()

        NotificationManagerCompat.from(context).notify(NOTIFICATION_ID, notification)
    }

    private fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val manager = context.getSystemService(NotificationManager::class.java) ?: return
        if (manager.getNotificationChannel(CHANNEL_ID) != null) return
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_ID,
                "Bank SMS sync issues",
                NotificationManager.IMPORTANCE_DEFAULT,
            ).apply {
                description = "Alerts when Ledger can't automatically forward a bank SMS"
            },
        )
    }
}
