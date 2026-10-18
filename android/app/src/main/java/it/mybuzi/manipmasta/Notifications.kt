package it.mybuzi.manipmasta

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat

object Notifications {
    const val CH_MONITOR = "monitor"
    const val CH_EVENTS = "events"

    fun ensureChannels(ctx: Context) {
        val nm = ctx.getSystemService(NotificationManager::class.java) ?: return
        val monitor = NotificationChannel(
            CH_MONITOR,
            ctx.getString(R.string.ch_monitor_name),
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = ctx.getString(R.string.ch_monitor_desc)
            setShowBadge(false)
        }
        val events = NotificationChannel(
            CH_EVENTS,
            ctx.getString(R.string.ch_events_name),
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = ctx.getString(R.string.ch_events_desc)
            enableVibration(true)
        }
        nm.createNotificationChannel(monitor)
        nm.createNotificationChannel(events)
    }

    /** Su Android 13+ serve il permesso runtime POST_NOTIFICATIONS. */
    fun canPost(ctx: Context): Boolean =
        Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED
}
