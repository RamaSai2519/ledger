package com.ledgerapp.mobile.sms

import android.content.Context

/**
 * Small SharedPreferences-backed handoff of the refresh token from JS
 * (`useAuthStore`, the only place a token is durably persisted today) to the
 * native SmsIngestWorker — which runs via WorkManager and may execute after
 * the RN JS runtime has been killed, so it cannot rely on reading zustand
 * state or reverse-engineering AsyncStorage's SQLite format. JS calls
 * AuthTokenModule.setRefreshToken/clearRefreshToken alongside its existing
 * AsyncStorage writes in authStore.ts.
 */
object AuthTokenStore {
    private const val PREFS_NAME = "ledger_auth"
    private const val KEY_REFRESH_TOKEN = "refresh_token"

    fun setRefreshToken(context: Context, token: String) {
        prefs(context).edit().putString(KEY_REFRESH_TOKEN, token).apply()
    }

    fun clear(context: Context) {
        prefs(context).edit().remove(KEY_REFRESH_TOKEN).apply()
    }

    fun getRefreshToken(context: Context): String? =
        prefs(context).getString(KEY_REFRESH_TOKEN, null)

    private fun prefs(context: Context) =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
}
