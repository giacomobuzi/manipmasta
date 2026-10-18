package it.mybuzi.manipmasta

import android.annotation.SuppressLint
import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONException
import org.json.JSONObject

/**
 * Foreground service (tipo dataSync) che mantiene una WebSocket su /ws?token=… e
 * mostra notifiche per CYCLE_DONE, ALARM… ed ESTOP. Riconnessione con backoff esponenziale.
 *
 * Messaggi attesi dal server (SPEC §5): {"type":"state|event|resp|online","data":…};
 * per "event" data è {"ts":…, "text":"CYCLE_DONE"} (accettata anche una stringa semplice).
 */
class MonitorService : Service() {

    private enum class Status { CONNECTING, CONNECTED, OFFLINE, RECONNECTING, BAD_CONFIG }

    private val handler = Handler(Looper.getMainLooper())
    private var socket: WebSocket? = null
    private var currentSignature: String? = null
    private var generation = 0
    private var backoffMs = INITIAL_BACKOFF_MS
    private var status = Status.CONNECTING
    private val lastNotified = HashMap<String, Long>()

    private val reconnectRunnable = Runnable { if (running) connect() }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        running = true
        Notifications.ensureChannels(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // startForeground va chiamato subito ad ogni avvio (vincolo di startForegroundService).
        if (!goForeground()) return START_NOT_STICKY

        if (intent?.action == ACTION_DISABLE) {
            Prefs.setNotifyCycle(this, false)
            stopSelf()
            return START_NOT_STICKY
        }
        if (!Prefs.notifyCycle(this)) {
            stopSelf()
            return START_NOT_STICKY
        }

        val signature = Prefs.connectionSignature(this)
        if (signature != currentSignature || socket == null) {
            currentSignature = signature
            backoffMs = INITIAL_BACKOFF_MS
            handler.removeCallbacks(reconnectRunnable)
            connect()
        }
        return START_STICKY
    }

    /** Android 15: i servizi dataSync hanno un limite di 6 h ogni 24 h. */
    override fun onTimeout(startId: Int, fgsType: Int) {
        Log.w(TAG, "Timeout foreground service dataSync, arresto")
        stopSelf()
    }

    override fun onDestroy() {
        running = false
        generation++
        handler.removeCallbacksAndMessages(null)
        socket?.close(1000, null)
        socket = null
        super.onDestroy()
    }

    // ------------------------------------------------------------- WebSocket

    private fun connect() {
        socket?.cancel()
        socket = null
        val gen = ++generation

        val token = Prefs.apiToken(this)
        val wsUrl = UrlUtils.toWebSocketUrl(Prefs.serverUrl(this), token)
        val request = try {
            if (wsUrl == null || token.isEmpty()) null
            else Request.Builder().url(wsUrl).header("Authorization", "Bearer $token").build()
        } catch (e: IllegalArgumentException) {
            null
        }
        if (request == null) {
            setStatus(Status.BAD_CONFIG)
            return
        }

        setStatus(Status.CONNECTING)
        socket = Net.ws.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                handler.post {
                    if (gen != generation) return@post
                    backoffMs = INITIAL_BACKOFF_MS
                    setStatus(Status.CONNECTED)
                }
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handler.post {
                    if (gen == generation) handleMessage(text)
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(1000, null)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                handler.post { if (gen == generation) scheduleReconnect() }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.w(TAG, "WebSocket errore (HTTP ${response?.code}): ${t.message}")
                handler.post { if (gen == generation) scheduleReconnect() }
            }
        })
    }

    private fun scheduleReconnect() {
        socket = null
        setStatus(Status.RECONNECTING)
        handler.removeCallbacks(reconnectRunnable)
        handler.postDelayed(reconnectRunnable, backoffMs)
        backoffMs = (backoffMs * 2).coerceAtMost(MAX_BACKOFF_MS)
    }

    private fun handleMessage(text: String) {
        val obj = try {
            JSONObject(text)
        } catch (e: JSONException) {
            return
        }
        when (obj.optString("type")) {
            "event" -> handleEvent(eventText(obj.opt("data")))
            "online" -> {
                val online = when (val d = obj.opt("data")) {
                    is Boolean -> d
                    is Number -> d.toInt() != 0
                    is String -> d == "1" || d.equals("true", ignoreCase = true)
                    else -> true
                }
                setStatus(if (online) Status.CONNECTED else Status.OFFLINE)
            }
        }
    }

    private fun eventText(data: Any?): String {
        val raw: String = when (data) {
            null, JSONObject.NULL -> ""
            is String -> data
            is JSONObject -> data.optString("text").ifEmpty {
                data.optString("event").ifEmpty { data.optString("ev") }
            }
            else -> data.toString()
        }
        return raw.trim()
    }

    private fun handleEvent(event: String) {
        val upper = event.uppercase()
        when {
            upper.startsWith("CYCLE_DONE") -> notifyEvent(
                "CYCLE_DONE", ID_CYCLE,
                getString(R.string.ev_cycle_done_title), getString(R.string.ev_cycle_done_text)
            )
            upper.startsWith("ALARM") -> notifyEvent(
                "ALARM", ID_ALARM,
                getString(R.string.ev_alarm_title), event
            )
            upper.startsWith("ESTOP") -> notifyEvent(
                "ESTOP", ID_ESTOP,
                getString(R.string.ev_estop_title), getString(R.string.ev_estop_text)
            )
        }
    }

    @SuppressLint("MissingPermission")
    private fun notifyEvent(key: String, id: Int, title: String, text: String) {
        val now = SystemClock.elapsedRealtime()
        val last = lastNotified[key]
        if (last != null && now - last < DEDUP_MS) return
        lastNotified[key] = now
        if (!Notifications.canPost(this)) return

        val n = NotificationCompat.Builder(this, Notifications.CH_EVENTS)
            .setSmallIcon(R.drawable.ic_stat_roller)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(if (key == "CYCLE_DONE") NotificationCompat.CATEGORY_STATUS else NotificationCompat.CATEGORY_ALARM)
            .setContentIntent(openAppIntent())
            .setAutoCancel(true)
            .build()
        NotificationManagerCompat.from(this).notify(id, n)
    }

    // ---------------------------------------------------- notifica fissa

    private fun setStatus(s: Status) {
        if (status == s) return
        status = s
        updateOngoing()
    }

    private fun statusText(): String = getString(
        when (status) {
            Status.CONNECTING -> R.string.monitor_connecting
            Status.CONNECTED -> R.string.monitor_connected
            Status.OFFLINE -> R.string.monitor_offline
            Status.RECONNECTING -> R.string.monitor_reconnecting
            Status.BAD_CONFIG -> R.string.monitor_bad_config
        }
    )

    private fun buildOngoing(): Notification {
        val disableIntent = PendingIntent.getService(
            this,
            1,
            Intent(this, MonitorService::class.java).setAction(ACTION_DISABLE),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, Notifications.CH_MONITOR)
            .setSmallIcon(R.drawable.ic_stat_roller)
            .setContentTitle(getString(R.string.monitor_title))
            .setContentText(statusText())
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setContentIntent(openAppIntent())
            .addAction(0, getString(R.string.monitor_disable), disableIntent)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }

    private fun goForeground(): Boolean = try {
        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
        } else {
            0
        }
        ServiceCompat.startForeground(this, ONGOING_ID, buildOngoing(), type)
        true
    } catch (e: Exception) {
        // es. ForegroundServiceStartNotAllowedException o limite dataSync esaurito (Android 15)
        Log.w(TAG, "startForeground fallito", e)
        stopSelf()
        false
    }

    @SuppressLint("MissingPermission")
    private fun updateOngoing() {
        if (!running || !Notifications.canPost(this)) return
        NotificationManagerCompat.from(this).notify(ONGOING_ID, buildOngoing())
    }

    private fun openAppIntent(): PendingIntent = PendingIntent.getActivity(
        this,
        0,
        Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
    )

    companion object {
        private const val TAG = "MonitorService"
        const val ACTION_DISABLE = "it.mybuzi.manipmasta.action.DISABLE_MONITOR"

        private const val ONGOING_ID = 1
        private const val ID_CYCLE = 100
        private const val ID_ALARM = 101
        private const val ID_ESTOP = 102

        private const val INITIAL_BACKOFF_MS = 2_000L
        private const val MAX_BACKOFF_MS = 60_000L
        private const val DEDUP_MS = 3_000L

        @Volatile
        var running = false
            private set

        /** Va chiamato con l'app in primo piano (limiti di avvio FGS da background, Android 12+). */
        fun start(context: Context) {
            try {
                ContextCompat.startForegroundService(context, Intent(context, MonitorService::class.java))
            } catch (e: Exception) {
                Log.w(TAG, "Avvio servizio non consentito", e)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, MonitorService::class.java))
        }

        fun syncWithPrefs(context: Context) {
            if (Prefs.notifyCycle(context)) start(context) else if (running) stop(context)
        }
    }
}
