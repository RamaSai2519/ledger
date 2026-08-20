# Add project specific ProGuard rules here.
# By default, the flags in this file are appended to flags specified
# in /usr/local/Cellar/android-sdk/24.3.3/tools/proguard/proguard-android.txt
# You can edit the include path and order by changing the proguardFiles
# directive in build.gradle.
#
# For more details, see
#   http://developer.android.com/guide/developing/tools/proguard.html

# Add any project specific keep options here:

# LED-7: WorkManager instantiates Worker subclasses via
# Class.forName(persistedClassName) reflection, not a normal constructor
# call R8 can trace — without this the SMS ingest handoff from
# SmsReceiver silently fails post-minification with a
# ClassNotFoundException swallowed inside WorkManager's own executor.
-keep class com.ledgerapp.mobile.sms.SmsIngestWorker { *; }
