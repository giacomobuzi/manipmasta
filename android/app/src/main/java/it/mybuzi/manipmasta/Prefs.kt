package it.mybuzi.manipmasta

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import androidx.preference.PreferenceDataStore
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Tutte le impostazioni (URL, token, switch) stanno in EncryptedSharedPreferences.
 * Se il keystore è corrotto (es. dopo ripristino dispositivo) il file viene ricreato;
 * come ultima risorsa si usa un file non cifrato per non bloccare l'app.
 */
object Prefs {
    private const val TAG = "Prefs"
    private const val FILE = "manipmasta_secure_prefs"

    const val KEY_URL = "server_url"
    const val KEY_TOKEN = "api_token"
    const val KEY_KEEP_SCREEN = "keep_screen_on"
    const val KEY_NOTIFY = "notify_cycle"

    const val DEFAULT_URL = "https://manipmasta.example.it"

    @Volatile
    private var instance: SharedPreferences? = null

    fun get(context: Context): SharedPreferences {
        instance?.let { return it }
        return synchronized(this) {
            instance ?: create(context.applicationContext).also { instance = it }
        }
    }

    private fun create(ctx: Context): SharedPreferences {
        return try {
            open(ctx)
        } catch (e: Exception) {
            Log.w(TAG, "EncryptedSharedPreferences non apribili, ricreo il file", e)
            ctx.deleteSharedPreferences(FILE)
            try {
                open(ctx)
            } catch (e2: Exception) {
                Log.e(TAG, "Cifratura non disponibile, uso preferenze in chiaro", e2)
                ctx.getSharedPreferences(FILE + "_fallback", Context.MODE_PRIVATE)
            }
        }
    }

    private fun open(ctx: Context): SharedPreferences {
        val masterKey = MasterKey.Builder(ctx)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        return EncryptedSharedPreferences.create(
            ctx,
            FILE,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    /** URL base normalizzato, senza "/" finale. */
    fun serverUrl(ctx: Context): String =
        UrlUtils.normalize(get(ctx).getString(KEY_URL, null)) ?: DEFAULT_URL

    fun isUrlConfigured(ctx: Context): Boolean = get(ctx).contains(KEY_URL)

    fun apiToken(ctx: Context): String =
        get(ctx).getString(KEY_TOKEN, null)?.trim().orEmpty()

    fun keepScreenOn(ctx: Context): Boolean = get(ctx).getBoolean(KEY_KEEP_SCREEN, true)

    fun notifyCycle(ctx: Context): Boolean = get(ctx).getBoolean(KEY_NOTIFY, false)

    fun setNotifyCycle(ctx: Context, value: Boolean) {
        get(ctx).edit().putBoolean(KEY_NOTIFY, value).apply()
    }

    /** Firma della configurazione di connessione: se cambia, WebView e WebSocket si ricollegano. */
    fun connectionSignature(ctx: Context): String = serverUrl(ctx) + "|" + apiToken(ctx)
}

/** Collega le Preference AndroidX allo storage cifrato. */
class SecurePrefsDataStore(private val prefs: SharedPreferences) : PreferenceDataStore() {
    override fun putString(key: String, value: String?) {
        prefs.edit().putString(key, value).apply()
    }

    override fun getString(key: String, defValue: String?): String? = prefs.getString(key, defValue)

    override fun putBoolean(key: String, value: Boolean) {
        prefs.edit().putBoolean(key, value).apply()
    }

    override fun getBoolean(key: String, defValue: Boolean): Boolean = prefs.getBoolean(key, defValue)
}
