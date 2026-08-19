package com.ledgerapp.mobile.sms

import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

/**
 * JS-facing bridge for AuthTokenStore (see that class for why this exists).
 * Called from src/state/authStore.ts on setSession/clearSession.
 */
class AuthTokenModule(reactContext: ReactApplicationContext) : ReactContextBaseJavaModule(reactContext) {
    override fun getName(): String = "AuthTokenModule"

    @ReactMethod
    fun setRefreshToken(token: String) {
        AuthTokenStore.setRefreshToken(reactApplicationContext, token)
    }

    @ReactMethod
    fun clearRefreshToken() {
        AuthTokenStore.clear(reactApplicationContext)
    }
}
