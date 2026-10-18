package it.mybuzi.manipmasta

import android.content.Context
import okhttp3.MediaType
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import java.io.IOException
import java.io.InterruptedIOException
import java.net.UnknownHostException
import java.net.UnknownServiceException
import java.util.concurrent.TimeUnit
import javax.net.ssl.SSLException

object Net {
    val JSON: MediaType = "application/json; charset=utf-8".toMediaType()

    /** Client per chiamate REST brevi (STOP, health). */
    val http: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(5, TimeUnit.SECONDS)
            .readTimeout(8, TimeUnit.SECONDS)
            .writeTimeout(8, TimeUnit.SECONDS)
            .callTimeout(12, TimeUnit.SECONDS)
            .build()
    }

    /** Client per la WebSocket: nessun timeout di lettura, ping periodico per rilevare cadute. */
    val ws: OkHttpClient by lazy {
        http.newBuilder()
            .readTimeout(0, TimeUnit.MILLISECONDS)
            .callTimeout(0, TimeUnit.MILLISECONDS)
            .pingInterval(20, TimeUnit.SECONDS)
            .build()
    }

    /** Messaggio leggibile in italiano per un errore di rete. */
    fun describe(ctx: Context, e: IOException): String = when {
        e is UnknownServiceException && (e.message ?: "").contains("CLEARTEXT", ignoreCase = true) ->
            ctx.getString(R.string.err_cleartext)
        e is SSLException -> ctx.getString(R.string.err_ssl)
        e is UnknownHostException -> ctx.getString(R.string.err_host)
        e is InterruptedIOException -> ctx.getString(R.string.err_timeout)
        else -> e.message ?: e.javaClass.simpleName
    }
}
