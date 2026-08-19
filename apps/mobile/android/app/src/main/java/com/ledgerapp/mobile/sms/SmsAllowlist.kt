package com.ledgerapp.mobile.sms

/**
 * Client-side bank/sender allow-list (plan.md §2.3, §7 step 2 — CLAUDE.md
 * "data minimization" non-negotiable constraint): only SMS from a known
 * transactional sender is ever forwarded off the device. Mirrors the base
 * sender codes seeded server-side in
 * services/api/src/shared/sms_parser_rules_seed.py, but matches by
 * suffix/contains rather than exact string — carriers prepend varying
 * 2-letter DLT prefixes (AD-, VM-, VK-, JD-, ...) to the same base code
 * depending on SIM/operator, and the seed data only enumerates a couple of
 * prefix variants per bank. The server's regex-rule matching stays the
 * source of truth for exact sender_ids; this list only decides whether a
 * message is even allowed to leave the device.
 */
object SmsAllowlist {
    private val BASE_CODES = listOf(
        "AXISBK",
        "HDFCBK",
        "KOTAKB",
        "SBIINB",
        "SBIUPI",
        "ZETPAY",
        "AXIOPL",
        "AMZNPL",
        "JUPCC",
        "CANBNK",
    )

    fun isAllowed(senderId: String?): Boolean {
        if (senderId.isNullOrBlank()) return false
        val normalized = senderId.uppercase().replace("-", "").replace(".", "")
        return BASE_CODES.any { normalized.contains(it) }
    }
}
