package it.mybuzi.manipmasta

import android.Manifest
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.text.InputType
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.annotation.StringRes
import androidx.preference.EditTextPreference
import androidx.preference.Preference
import androidx.preference.PreferenceFragmentCompat
import androidx.preference.SwitchPreferenceCompat
import okhttp3.Call
import okhttp3.Callback
import okhttp3.Request
import okhttp3.Response
import java.io.IOException

class SettingsFragment : PreferenceFragmentCompat() {

    private val notificationPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (!granted) toast(R.string.notif_permission_denied)
        }

    override fun onCreatePreferences(savedInstanceState: Bundle?, rootKey: String?) {
        // Tutte le preferenze passano dallo storage cifrato (EncryptedSharedPreferences).
        preferenceManager.preferenceDataStore = SecurePrefsDataStore(Prefs.get(requireContext()))
        setPreferencesFromResource(R.xml.preferences, rootKey)

        findPreference<EditTextPreference>(Prefs.KEY_URL)?.apply {
            setOnBindEditTextListener { edit ->
                edit.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
                edit.setSingleLine(true)
                edit.setSelection(edit.text.length)
            }
            summaryProvider = Preference.SummaryProvider<EditTextPreference> { p ->
                UrlUtils.normalize(p.text) ?: Prefs.DEFAULT_URL
            }
            setOnPreferenceChangeListener { pref, newValue ->
                onUrlChanged(pref as EditTextPreference, newValue as? String)
            }
        }

        findPreference<EditTextPreference>(Prefs.KEY_TOKEN)?.apply {
            setOnBindEditTextListener { edit ->
                edit.inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
                edit.setSingleLine(true)
            }
            summaryProvider = Preference.SummaryProvider<EditTextPreference> { p ->
                if (p.text.isNullOrBlank()) getString(R.string.token_not_set) else getString(R.string.token_set)
            }
            setOnPreferenceChangeListener { pref, newValue ->
                val raw = newValue as? String ?: ""
                val trimmed = raw.trim()
                if (trimmed != raw) {
                    (pref as EditTextPreference).text = trimmed
                    false
                } else {
                    true
                }
            }
        }

        findPreference<Preference>(KEY_TEST)?.setOnPreferenceClickListener { pref ->
            runConnectionTest(pref)
            true
        }

        findPreference<SwitchPreferenceCompat>(Prefs.KEY_NOTIFY)?.setOnPreferenceChangeListener { _, newValue ->
            onNotifyToggled(newValue as Boolean)
            true
        }

        findPreference<Preference>(KEY_VERSION)?.summary =
            "${BuildConfig.VERSION_NAME} (${BuildConfig.VERSION_CODE})"
    }

    private fun onUrlChanged(pref: EditTextPreference, raw: String?): Boolean {
        val normalized = UrlUtils.normalize(raw)
        if (normalized == null) {
            toast(R.string.url_invalid)
            return false
        }
        if (UrlUtils.isHttp(normalized) && !UrlUtils.isLanHost(Uri.parse(normalized).host)) {
            toast(R.string.url_http_not_lan)
            return false
        }
        if (normalized != raw) {
            // Salva la versione normalizzata al posto di quella digitata.
            pref.text = normalized
            return false
        }
        return true
    }

    private fun onNotifyToggled(enabled: Boolean) {
        val ctx = requireContext()
        if (enabled) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && !Notifications.canPost(ctx)) {
                notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
            MonitorService.start(ctx)
        } else {
            MonitorService.stop(ctx)
        }
    }

    // ------------------------------------------------------- test connessione

    private fun runConnectionTest(pref: Preference) {
        val ctx = requireContext().applicationContext
        val base = Prefs.serverUrl(ctx)
        val token = Prefs.apiToken(ctx)
        pref.summary = getString(R.string.test_running)

        val health = try {
            Request.Builder().url("$base/api/health").get().build()
        } catch (e: IllegalArgumentException) {
            showTestResult(pref, getString(R.string.url_invalid))
            return
        }

        Net.http.newCall(health).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                showTestResult(pref, ctx.getString(R.string.test_health_fail, Net.describe(ctx, e)))
            }

            override fun onResponse(call: Call, response: Response) {
                val code = response.code
                response.close()
                if (code !in 200..299) {
                    showTestResult(
                        pref,
                        ctx.getString(R.string.test_health_fail, ctx.getString(R.string.err_http, code))
                    )
                    return
                }
                if (token.isEmpty()) {
                    showTestResult(pref, ctx.getString(R.string.test_ok_no_token))
                    return
                }
                checkToken(pref, base, token)
            }
        })
    }

    /** /api/state richiede il Bearer: 200 = token valido, 401/403 = token errato. */
    private fun checkToken(pref: Preference, base: String, token: String) {
        val ctx = pref.context.applicationContext
        val req = Request.Builder()
            .url("$base/api/state")
            .header("Authorization", "Bearer $token")
            .get()
            .build()
        Net.http.newCall(req).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                showTestResult(pref, ctx.getString(R.string.test_health_fail, Net.describe(ctx, e)))
            }

            override fun onResponse(call: Call, response: Response) {
                val code = response.code
                response.close()
                val msg = when {
                    code in 200..299 -> ctx.getString(R.string.test_ok_token_ok)
                    code == 401 || code == 403 -> ctx.getString(R.string.test_ok_token_bad, code)
                    else -> ctx.getString(R.string.test_ok_state_other, code)
                }
                showTestResult(pref, msg)
            }
        })
    }

    private fun showTestResult(pref: Preference, message: String) {
        val act = activity ?: return
        act.runOnUiThread {
            if (!isAdded) return@runOnUiThread
            pref.summary = message
            Toast.makeText(act, message, Toast.LENGTH_LONG).show()
        }
    }

    private fun toast(@StringRes res: Int) {
        Toast.makeText(requireContext(), res, Toast.LENGTH_LONG).show()
    }

    private companion object {
        const val KEY_TEST = "test_connection"
        const val KEY_VERSION = "version"
    }
}
