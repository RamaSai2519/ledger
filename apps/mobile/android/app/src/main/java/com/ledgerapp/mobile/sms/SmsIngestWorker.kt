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

        const val KEY_SENDER_ID = "sender_id"
        const val KEY_RAW_TEXT = "raw_text"
        const val KEY_RECEIVED_AT = "received_at"
    }

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val senderId = inputData.getString(KEY_SENDER_ID) ?: return@withContext Result.failure()
        val rawText = inputData.getString(KEY_RAW_TEXT) ?: return@withContext Result.failure()
        val receivedAt = inputData.getString(KEY_RECEIVED_AT)

        val refreshToken = AuthTokenStore.getRefreshToken(applicationContext)
        if (refreshToken.isNullOrBlank()) {
            // No signed-in session to attribute this to yet — retry later
            // rather than dropping the SMS, in case sign-in happens shortly after.
            return@withContext Result.retry()
        }

        try {
            val accessToken = refreshAccessToken(refreshToken) ?: return@withContext Result.retry()
            val ingestBody = JSONObject().apply {
                put("sender_id", senderId)
                put("raw_text", rawText)
                if (receivedAt != null) put("received_at", receivedAt)
            }
            val status = postJson("$API_BASE_URL/sms/ingest", ingestBody, accessToken)
            if (status in 200..299) {
                Result.success(workDataOf(KEY_SENDER_ID to senderId))
            } else if (status in 500..599) {
                Result.retry()
            } else {
                Log.w(TAG, "sms/ingest rejected with status $status, not retrying")
                Result.failure()
            }
        } catch (e: Exception) {
            Log.w(TAG, "sms/ingest attempt failed, will retry", e)
            Result.retry()
        }
    }

    private fun refreshAccessToken(refreshToken: String): String? {
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
        if (responseCode !in 200..299) {
            connection.disconnect()
            return null
        }
        val body = connection.inputStream.bufferedReader().use { it.readText() }
        connection.disconnect()
        val data = JSONObject(body).optJSONObject("data") ?: return null
        return data.optString("access_token").takeIf { it.isNotBlank() }
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
