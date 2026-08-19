package com.ledgerapp.mobile.sms

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * CLAUDE.md's data-minimization/allow-list guard, exercised client-side
 * (LED-7): a non-bank sender must never be treated as allowed, whatever the
 * carrier prefix on a real bank sender looks like.
 */
class SmsAllowlistTest {

    @Test
    fun `allows known bank base codes`() {
        assertTrue(SmsAllowlist.isAllowed("HDFCBK"))
        assertTrue(SmsAllowlist.isAllowed("AXISBK"))
        assertTrue(SmsAllowlist.isAllowed("SBIUPI"))
        assertTrue(SmsAllowlist.isAllowed("CANBNK"))
    }

    @Test
    fun `allows known bank codes with carrier DLT prefixes`() {
        assertTrue(SmsAllowlist.isAllowed("AD-HDFCBK"))
        assertTrue(SmsAllowlist.isAllowed("VM-AXISBK"))
        assertTrue(SmsAllowlist.isAllowed("VK-KOTAKB"))
        assertTrue(SmsAllowlist.isAllowed("JD-JUPCC"))
    }

    @Test
    fun `allows Amazon Pay Later under the Axio code family`() {
        assertTrue(SmsAllowlist.isAllowed("AMZNPL"))
        assertTrue(SmsAllowlist.isAllowed("AD-AXIOPL"))
    }

    @Test
    fun `rejects personal and unknown senders`() {
        assertFalse(SmsAllowlist.isAllowed("+919876543210"))
        assertFalse(SmsAllowlist.isAllowed("MOM"))
        assertFalse(SmsAllowlist.isAllowed("RANDOMSHOP"))
    }

    @Test
    fun `rejects null and blank senders`() {
        assertFalse(SmsAllowlist.isAllowed(null))
        assertFalse(SmsAllowlist.isAllowed(""))
        assertFalse(SmsAllowlist.isAllowed("   "))
    }

    @Test
    fun `is case-insensitive`() {
        assertTrue(SmsAllowlist.isAllowed("hdfcbk"))
        assertTrue(SmsAllowlist.isAllowed("ad-hdfcbk"))
    }
}
