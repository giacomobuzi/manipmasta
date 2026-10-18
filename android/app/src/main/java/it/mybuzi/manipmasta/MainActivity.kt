package it.mybuzi.manipmasta

import android.annotation.SuppressLint
import android.content.ActivityNotFoundException
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.net.http.SslError
import android.os.Build
import android.os.Bundle
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.view.View
import android.view.WindowManager
import android.webkit.SslErrorHandler
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.TextView
import androidx.activity.OnBackPressedCallback
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.updatePadding
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import com.google.android.material.button.MaterialButton
import com.google.android.material.progressindicator.LinearProgressIndicator
import com.google.android.material.snackbar.Snackbar
import okhttp3.Call
import okhttp3.Callback
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.json.JSONObject
import java.io.IOException

/**
 * WebView a tutto schermo sulla UI del server + barra inferiore nativa con STOP.
 *
 * Token: la UI web legge il token da localStorage["mm_token"]. Al primo onPageFinished
 * sull'origine del server l'app scrive il token configurato in localStorage e, se era
 * diverso, ricarica la pagina una volta. In più il token viene passato come header
 * Authorization nella sola richiesta iniziale della pagina (loadUrl con header), utile
 * se il server/proxy lo richiede già per servire "/".
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var swipe: SwipeRefreshLayout
    private lateinit var progress: LinearProgressIndicator
    private lateinit var errorView: View
    private lateinit var errorDetail: TextView
    private lateinit var bottomBar: View
    private lateinit var stopButton: MaterialButton

    /** Configurazione (url|token) con cui è stata caricata la pagina corrente. */
    private var loadedSignature: String? = null
    private var tokenSynced = false
    private var mainFrameError = false

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webView)
        swipe = findViewById(R.id.swipeRefresh)
        progress = findViewById(R.id.pageProgress)
        errorView = findViewById(R.id.errorView)
        errorDetail = findViewById(R.id.errorDetail)
        bottomBar = findViewById(R.id.bottomBar)
        stopButton = findViewById(R.id.stopButton)

        // Edge-to-edge (obbligatorio con targetSdk 35): padding per barre di sistema e tastiera.
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.root)) { v, insets ->
            val bars = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or
                    WindowInsetsCompat.Type.displayCutout() or
                    WindowInsetsCompat.Type.ime()
            )
            v.updatePadding(left = bars.left, top = bars.top, right = bars.right, bottom = bars.bottom)
            WindowInsetsCompat.CONSUMED
        }

        setupWebView()

        swipe.setOnRefreshListener { reloadPage() }
        // Il pull-to-refresh scatta solo se la pagina è in cima.
        swipe.setOnChildScrollUpCallback { _, _ -> webView.scrollY > 0 }

        findViewById<Button>(R.id.retryButton).setOnClickListener { loadServer() }
        findViewById<Button>(R.id.errorSettingsButton).setOnClickListener { openSettings() }
        findViewById<View>(R.id.settingsButton).setOnClickListener { openSettings() }
        stopButton.setOnClickListener { sendStop() }

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (errorView.visibility != View.VISIBLE && webView.canGoBack()) {
                    webView.goBack()
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                    isEnabled = true
                }
            }
        })

        if (savedInstanceState == null && !Prefs.isUrlConfigured(this)) {
            openSettings()
        }
    }

    override fun onResume() {
        super.onResume()
        webView.onResume()
        applyKeepScreenOn()
        if (loadedSignature != Prefs.connectionSignature(this)) {
            loadServer()
        }
        MonitorService.syncWithPrefs(this)
    }

    override fun onPause() {
        webView.onPause()
        super.onPause()
    }

    override fun onDestroy() {
        (webView.parent as? android.view.ViewGroup)?.removeView(webView)
        webView.stopLoading()
        webView.destroy()
        super.onDestroy()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        with(webView.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            allowFileAccess = false
            allowContentAccess = false
            cacheMode = WebSettings.LOAD_DEFAULT
            // La UI può riconoscere l'app (es. per nascondere il proprio pulsante STOP).
            userAgentString = "$userAgentString ManipMastaApp/${BuildConfig.VERSION_NAME}"
        }

        webView.setWebChromeClient(object : WebChromeClient() {
            override fun onProgressChanged(view: WebView, newProgress: Int) {
                progress.visibility = if (newProgress in 1..99) View.VISIBLE else View.GONE
                progress.setProgressCompat(newProgress, true)
            }
        })

        webView.setWebViewClient(object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val target = request.url
                val base = Uri.parse(Prefs.serverUrl(this@MainActivity))
                if (UrlUtils.sameOrigin(target, base)) return false
                // Link esterni: browser di sistema.
                try {
                    startActivity(Intent(Intent.ACTION_VIEW, target))
                } catch (e: ActivityNotFoundException) {
                    // nessuna app in grado di aprire il link
                }
                return true
            }

            override fun onPageStarted(view: WebView, url: String?, favicon: Bitmap?) {
                mainFrameError = false
            }

            override fun onPageFinished(view: WebView, url: String?) {
                swipe.isRefreshing = false
                if (mainFrameError) return
                hideError()
                syncTokenIfNeeded(url)
            }

            override fun onReceivedError(
                view: WebView,
                request: WebResourceRequest,
                error: WebResourceError
            ) {
                if (request.isForMainFrame) {
                    showError(error.description?.toString().orEmpty())
                }
            }

            override fun onReceivedHttpError(
                view: WebView,
                request: WebResourceRequest,
                errorResponse: WebResourceResponse
            ) {
                // 502/503/504 dal proxy quando la VM o il server sono giù.
                if (request.isForMainFrame && errorResponse.statusCode >= 500) {
                    showError(getString(R.string.err_http, errorResponse.statusCode))
                }
            }

            @SuppressLint("WebViewClientOnReceivedSslError")
            override fun onReceivedSslError(view: WebView, handler: SslErrorHandler, error: SslError) {
                handler.cancel()
                showError(getString(R.string.error_ssl))
            }
        })
    }

    private fun loadServer() {
        val url = Prefs.serverUrl(this)
        val token = Prefs.apiToken(this)
        loadedSignature = Prefs.connectionSignature(this)
        tokenSynced = false
        mainFrameError = false
        hideError()
        val headers = HashMap<String, String>()
        if (token.isNotEmpty()) headers["Authorization"] = "Bearer $token"
        webView.loadUrl("$url/", headers)
    }

    private fun reloadPage() {
        if (errorView.visibility == View.VISIBLE || webView.url.isNullOrEmpty()) {
            loadServer()
        } else {
            webView.reload()
        }
    }

    /** Scrive il token in localStorage["mm_token"]; se è cambiato ricarica una sola volta. */
    private fun syncTokenIfNeeded(url: String?) {
        if (tokenSynced || url == null) return
        val base = Uri.parse(Prefs.serverUrl(this))
        if (!UrlUtils.sameOrigin(Uri.parse(url), base)) return
        tokenSynced = true
        val token = Prefs.apiToken(this)
        if (token.isEmpty()) return
        val js = "(function(){try{var t=" + JSONObject.quote(token) + ";" +
            "if(window.localStorage.getItem('mm_token')!==t){" +
            "window.localStorage.setItem('mm_token',t);return 'changed';}" +
            "return 'same';}catch(e){return 'error';}})();"
        webView.evaluateJavascript(js) { result ->
            if (result == "\"changed\"") webView.reload()
        }
    }

    private fun showError(detail: String) {
        mainFrameError = true
        swipe.isRefreshing = false
        progress.visibility = View.GONE
        errorDetail.text = detail
        errorDetail.visibility = if (detail.isBlank()) View.GONE else View.VISIBLE
        errorView.visibility = View.VISIBLE
    }

    private fun hideError() {
        errorView.visibility = View.GONE
    }

    private fun applyKeepScreenOn() {
        if (Prefs.keepScreenOn(this)) {
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }

    private fun openSettings() {
        startActivity(Intent(this, SettingsActivity::class.java))
    }

    // ------------------------------------------------------------------ STOP

    private fun sendStop() {
        vibrate(VIB_PRESS)
        val token = Prefs.apiToken(this)
        val body = JSONObject().put("cmd", "STOP").toString().toRequestBody(Net.JSON)
        val request = try {
            val b = Request.Builder().url(Prefs.serverUrl(this) + "/api/cmd").post(body)
            if (token.isNotEmpty()) b.header("Authorization", "Bearer $token")
            b.build()
        } catch (e: IllegalArgumentException) {
            onStopResult(false, getString(R.string.stop_invalid_url))
            return
        }
        Net.http.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                val msg = getString(R.string.stop_failed, Net.describe(this@MainActivity, e))
                runOnUiThread { onStopResult(false, msg) }
            }

            override fun onResponse(call: Call, response: Response) {
                val code = response.code
                response.close()
                val msg = when {
                    code in 200..299 -> getString(R.string.stop_sent)
                    code == 401 || code == 403 -> getString(R.string.stop_unauthorized, code)
                    else -> getString(R.string.stop_failed, getString(R.string.err_http, code))
                }
                runOnUiThread { onStopResult(code in 200..299, msg) }
            }
        })
    }

    private fun onStopResult(ok: Boolean, message: String) {
        if (isFinishing || isDestroyed) return
        val snack = Snackbar.make(
            findViewById(R.id.contentFrame),
            message,
            if (ok) Snackbar.LENGTH_SHORT else Snackbar.LENGTH_LONG
        )
        if (!ok) {
            snack.setAction(R.string.retry) { sendStop() }
            vibrate(VIB_ERROR)
        } else {
            vibrate(VIB_OK)
        }
        snack.show()
    }

    private fun vibrate(pattern: LongArray) {
        val vibrator: Vibrator? = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (getSystemService(VIBRATOR_MANAGER_SERVICE) as? VibratorManager)?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            getSystemService(VIBRATOR_SERVICE) as? Vibrator
        }
        if (vibrator == null || !vibrator.hasVibrator()) return
        vibrator.vibrate(VibrationEffect.createWaveform(pattern, -1))
    }

    companion object {
        private val VIB_PRESS = longArrayOf(0, 60)
        private val VIB_OK = longArrayOf(0, 40, 80, 40)
        private val VIB_ERROR = longArrayOf(0, 300, 150, 300, 150, 300)
    }
}
