package com.ledgerapp.mobile.sms

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

/**
 * Delivers one allow-listed SMS to POST /sms/ingest natively, without
 * depending on the RN JS runtime being alive (plan.md §13: the receiver
 * "needs to keep working even when the app is backgrounded/killed" —
 * WorkManager persists the request and retries across process death,
 * unlike a JS-only listener).
 *
 * The JS layer never persists an access token (see authStore.ts) — only the
 * longer-lived refresh token, via AuthTokenModule. So every run first mints
 * a fresh access token from /auth/refresh before posting to /sms/ingest.
 */
class SmsIngestWorker(appContext: Context, params: WorkerParameters) : CoroutineWorker(appContext, params) {

    companion object {
        private const val TAG = "SmsIngestWorker"
        // See src/api/client.ts — same base URL, sourced from `terraform output api_url`.
        private const val API_BASE_URL = "https://w7ychchtd1.execute-api.ap-south-1.amazonaws.com"

        // Retrying forever on a permanently-dead refresh token or a
        // persistent network fault wasted battery and, worse, gave the user
        // no signal that their bank SMS pipeline had silently stopped
        // working. Cap attempts and alert instead of retrying past this.
        private const val MAX_ATTEMPTS = 8

        const val KEY_SENDER_ID = "sender_id"
        const val KEY_RAW_TEXT = "raw_text"
        const val KEY_RECEIVED_AT = "received_at"
    }

    private sealed class RefreshOutcome {
        data class Success(val accessToken: String) : RefreshOutcome()
        object Unauthorized : RefreshOutcome()
        object TransientFailure : RefreshOutcome()
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val senderId = inputData.getString(KEY_SENDER_ID) ?: return@withContext Result.failure()
        val rawText = inputData.getString(KEY_RAW_TEXT) ?: return@withContext Result.failure()
        val receivedAt = inputData.getString(KEY_RECEIVED_AT)

        val refreshToken = AuthTokenStore.getRefreshToken(applicationContext)
        if (refreshToken.isNullOrBlank()) {
            // No signed-in session to attribute this to yet — retry (capped)
            // rather than dropping the SMS, in case sign-in happens shortly after.
            return@withContext retryOrGiveUp("no refresh token stored yet")
        }

        try {
            when (val outcome = refreshAccessToken(refreshToken)) {
                is RefreshOutcome.Unauthorized -> {
                    // The stored token is definitively dead (expired/revoked),
                    // not just transiently unreachable — retrying it forever
                    // would never succeed. Clear it and tell the user.
                    AuthTokenStore.clear(applicationContext)
                    Log.w(TAG, "refresh token rejected as unauthorized; giving up and alerting user")
                    SmsSyncNotifier.notifySignInRequired(applicationContext)
                    Result.failure()
                }
                is RefreshOutcome.TransientFailure -> retryOrGiveUp("auth/refresh unreachable or errored")
                is RefreshOutcome.Success -> {
                    val ingestBody = JSONObject().apply {
                        put("sender_id", senderId)
                        put("raw_text", rawText)
                        if (receivedAt != null) put("received_at", receivedAt)
                    }
                    val status = postJson("$API_BASE_URL/sms/ingest", ingestBody, outcome.accessToken)
                    if (status in 200..299) {
                        if (receivedAt != null) {
                            SmsSentLog.markSent(applicationContext, SmsSentLog.key(senderId, receivedAt))
                        }
                        Result.success(workDataOf(KEY_SENDER_ID to senderId))
                    } else if (status in 500..599) {
                        retryOrGiveUp("sms/ingest returned $status")
                    } else {
                        Log.w(TAG, "sms/ingest rejected with status $status, not retrying")
                        SmsSyncNotifier.notifyIngestFailing(applicationContext)
                        Result.failure()
                    }
                }
            }
        } catch (e: Exception) {
            Log.w(TAG, "sms/ingest attempt failed", e)
            retryOrGiveUp("exception: ${e.message}")
        }
    }

    private fun retryOrGiveUp(reason: String): Result {
        if (runAttemptCount + 1 >= MAX_ATTEMPTS) {
            Log.w(TAG, "giving up after $MAX_ATTEMPTS attempts ($reason); alerting user")
            SmsSyncNotifier.notifyIngestFailing(applicationContext)
            return Result.failure()
        }
        return Result.retry()
    }

    private fun refreshAccessToken(refreshToken: String): RefreshOutcome {
        val connection = (URL("$API_BASE_URL/auth/refresh").openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            setRequestProperty("Authorization", "Bearer $refreshToken")
            setRequestProperty("Content-Type", "application/json")
            doOutput = true
            connectTimeout = 15_000
            readTimeout = 15_000
        }
        connection.outputStream.use { it.write(ByteArray(0)) }
        val responseCode = connection.responseCode
        if (responseCode == 401) {
            connection.disconnect()
            return RefreshOutcome.Unauthorized
        }
        if (responseCode !in 200..299) {
            connection.disconnect()
            return RefreshOutcome.TransientFailure
        }
        val body = connection.inputStream.bufferedReader().use { it.readText() }
        connection.disconnect()
        val data = JSONObject(body).optJSONObject("data")
        val accessToken = data?.optString("access_token")?.takeIf { it.isNotBlank() }
        return accessToken?.let { RefreshOutcome.Success(it) } ?: RefreshOutcome.TransientFailure
    }

    private fun postJson(urlString: String, body: JSONObject, accessToken: String): Int {
        val connection = (URL(urlString).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            setRequestProperty("Authorization", "Bearer $accessToken")
            setRequestProperty("Content-Type", "application/json")
            doOutput = true
            connectTimeout = 15_000
            readTimeout = 15_000
        }
        OutputStreamWriter(connection.outputStream).use { it.write(body.toString()) }
        val status = connection.responseCode
        connection.disconnect()
        return status
    }
}
