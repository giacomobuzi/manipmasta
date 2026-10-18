package it.mybuzi.manipmasta

import android.net.Uri
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import java.net.URLEncoder

object UrlUtils {
    private val LAN_SUFFIXES = listOf(".local", ".lan", ".home.arpa", ".internal", ".localdomain")

    /**
     * Normalizza l'URL inserito dall'utente: aggiunge https:// se manca lo schema,
     * accetta solo http/https con host valido, toglie gli "/" finali. Null se non valido.
     */
    fun normalize(raw: String?): String? {
        var s = raw?.trim() ?: return null
        if (s.isEmpty()) return null
        if (!s.contains("://")) s = "https://$s"
        val parsed = s.toHttpUrlOrNull() ?: return null
        if (parsed.host.isEmpty()) return null
        return s.trimEnd('/')
    }

    fun isHttp(url: String): Boolean = url.startsWith("http://", ignoreCase = true)

    /** True se l'host è di rete locale: IPv4 privato/loopback/link-local o suffisso LAN. */
    fun isLanHost(host: String?): Boolean {
        val h = host?.lowercase()?.trimEnd('.') ?: return false
        if (h.isEmpty()) return false
        if (h == "localhost") return true
        if (LAN_SUFFIXES.any { h.endsWith(it) }) return true
        val parts = h.split('.')
        if (parts.size != 4) return false
        val o = parts.map { it.toIntOrNull() ?: return false }
        if (o.any { it !in 0..255 }) return false
        return o[0] == 10 ||
            o[0] == 127 ||
            (o[0] == 172 && o[1] in 16..31) ||
            (o[0] == 192 && o[1] == 168) ||
            (o[0] == 169 && o[1] == 254)
    }

    private fun effectivePort(uri: Uri): Int {
        if (uri.port != -1) return uri.port
        return when (uri.scheme?.lowercase()) {
            "https" -> 443
            "http" -> 80
            else -> -1
        }
    }

    fun sameOrigin(a: Uri, b: Uri): Boolean =
        a.scheme.equals(b.scheme, ignoreCase = true) &&
            a.host.equals(b.host, ignoreCase = true) &&
            effectivePort(a) == effectivePort(b)

    /** https://host[/base] → wss://host[/base]/ws?token=… */
    fun toWebSocketUrl(base: String, token: String): String? {
        val wsBase = when {
            base.startsWith("https://", ignoreCase = true) -> "wss://" + base.substring(8)
            base.startsWith("http://", ignoreCase = true) -> "ws://" + base.substring(7)
            else -> return null
        }
        return wsBase + "/ws?token=" + URLEncoder.encode(token, "UTF-8")
    }
}
