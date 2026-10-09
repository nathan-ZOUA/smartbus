package com.smartbus.driver

import android.Manifest
import android.app.Activity
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.Spinner
import android.widget.TextView
import androidx.core.content.ContextCompat
import java.io.IOException
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val executor = Executors.newSingleThreadExecutor()
    private lateinit var tokenStore: SecureTokenStore
    private lateinit var apiClient: ApiClient
    private lateinit var root: LinearLayout
    private lateinit var form: LinearLayout
    private lateinit var controls: LinearLayout
    private lateinit var usernameInput: android.widget.EditText
    private lateinit var passwordInput: android.widget.EditText
    private lateinit var busSpinner: Spinner
    private lateinit var statusText: TextView
    private lateinit var startButton: Button
    private lateinit var stopButton: Button
    private lateinit var loginButton: Button
    private lateinit var progress: ProgressBar
    private var assignedBuses: List<AssignedBus> = emptyList()
    private var loggedInUsername = ""
    private var receiverRegistered = false

    private val trackingReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action != LocationTrackingService.ACTION_STATE) return
            val text = intent.getStringExtra(LocationTrackingService.EXTRA_STATE).orEmpty()
            val error = intent.getBooleanExtra(LocationTrackingService.EXTRA_ERROR, false)
            runOnUiThread {
                setStatus(text, error)
                if (text == "Partage GPS arrêté" || text.startsWith("Session expirée")) {
                    showStoppedState()
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tokenStore = SecureTokenStore(this)
        apiClient = try {
            ApiClient()
        } catch (error: IllegalArgumentException) {
            setContentView(createConfigurationScreen(error.message ?: "URL API non configurée."))
            return
        }
        buildScreen()
        registerStateReceiver()

        val token = tokenStore.read()
        if (token.isNullOrBlank()) {
            showLogin()
        } else {
            loadAssignedBuses(token)
        }
    }

    override fun onDestroy() {
        if (receiverRegistered) unregisterReceiver(trackingReceiver)
        executor.shutdown()
        super.onDestroy()
    }

    private fun buildScreen() {
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(30), dp(24), dp(24))
            setBackgroundColor(0xFF0D1624.toInt())
        }
        setContentView(root)

        addText(root, "SMARTBUS  /  CONDUCTEUR", 12f, 0xFF59D7D0.toInt(), bold = true)
        addText(root, "Partage GPS", 28f, 0xFFF1F5FB.toInt(), bold = true, top = 22)
        addText(
            root,
            "Le partage est désactivé par défaut. Démarre-le au début du service et arrête-le à la fin.",
            14f,
            0xFF9AAABD.toInt(),
            top = 10,
        )

        statusText = addText(root, "Déconnecté", 14f, 0xFFB9C7D7.toInt(), top = 22)
        progress = ProgressBar(this).apply { visibility = View.GONE }
        root.addView(progress, LinearLayout.LayoutParams(dp(34), dp(34)).apply { topMargin = dp(14) })

        form = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
        }
        root.addView(form, matchWidthWrap())
        usernameInput = editText("Nom d'utilisateur").also { form.addView(it, matchWidthWrap(14)) }
        passwordInput = editText("Mot de passe").apply {
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD
        }.also { form.addView(it, matchWidthWrap(12)) }
        loginButton = button("Connexion conducteur").also { form.addView(it, matchWidthWrap(18)) }
        loginButton.setOnClickListener { login() }

        controls = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
        }
        root.addView(controls, matchWidthWrap())
        busSpinner = Spinner(this).also { controls.addView(it, matchWidthWrap(18)) }
        startButton = button("Démarrer le partage GPS").also { controls.addView(it, matchWidthWrap(20)) }
        stopButton = button("Arrêter le partage").apply {
            setBackgroundColor(0xFF49323A.toInt())
            visibility = View.GONE
        }.also { controls.addView(it, matchWidthWrap(10)) }
        val logoutButton = button("Se déconnecter").apply {
            setBackgroundColor(0xFF243247.toInt())
        }.also { controls.addView(it, matchWidthWrap(14)) }

        startButton.setOnClickListener { requestPermissionsAndStart() }
        stopButton.setOnClickListener { stopTracking() }
        logoutButton.setOnClickListener { logout() }

        addText(
            root,
            "SmartBus enregistre les positions du bus associé à ton compte uniquement pendant le partage. Le GPS exige une permission et une connexion Internet.",
            12f,
            0xFF7E91A8.toInt(),
            top = 24,
        )
    }

    private fun login() {
        val username = usernameInput.text.toString().trim()
        val password = passwordInput.text.toString()
        if (username.isBlank() || password.isBlank()) {
            setStatus("Saisis ton identifiant et ton mot de passe.", true)
            return
        }
        setLoading(true)
        executor.execute {
            try {
                val (token, returnedUsername) = apiClient.login(username, password)
                tokenStore.save(token)
                loggedInUsername = returnedUsername
                runOnUiThread { loadAssignedBuses(token) }
            } catch (error: Exception) {
                runOnUiThread {
                    setLoading(false)
                    setStatus(error.message ?: "Connexion impossible.", true)
                }
            }
        }
    }

    private fun loadAssignedBuses(token: String) {
        setLoading(true)
        executor.execute {
            try {
                val buses = apiClient.getAssignedBuses(token)
                runOnUiThread {
                    assignedBuses = buses
                    setLoading(false)
                    form.visibility = View.GONE
                    controls.visibility = View.VISIBLE
                    busSpinner.adapter = ArrayAdapter(
                        this,
                        android.R.layout.simple_spinner_dropdown_item,
                        buses.map { "${it.registration} · ${it.status}" },
                    )
                    val trackingPreferences = getSharedPreferences(
                        LocationTrackingService.TRACKING_PREFS,
                        Context.MODE_PRIVATE,
                    )
                    val trackingActive = trackingPreferences.getBoolean(
                        LocationTrackingService.TRACKING_ACTIVE,
                        false,
                    )
                    if (buses.isEmpty()) {
                        startButton.isEnabled = false
                        busSpinner.isEnabled = false
                        setStatus("Aucun bus affecté. Contacte le gestionnaire de flotte.", true)
                    } else {
                        busSpinner.isEnabled = !trackingActive
                        startButton.isEnabled = !trackingActive
                        startButton.visibility = if (trackingActive) View.GONE else View.VISIBLE
                        stopButton.visibility = if (trackingActive) View.VISIBLE else View.GONE
                        val detail = if (trackingActive) {
                            "Partage GPS actif pour ${trackingPreferences.getString(LocationTrackingService.TRACKING_REGISTRATION, "le bus sélectionné")}."
                        } else {
                            "Partage GPS arrêté."
                        }
                        setStatus(
                            "Connecté${loggedInUsername.takeIf { it.isNotBlank() }?.let { " : $it" } ?: ""}. $detail"
                        )
                    }
                }
            } catch (error: Exception) {
                tokenStore.clear()
                runOnUiThread {
                    setLoading(false)
                    showLogin()
                    setStatus(error.message ?: "Impossible de charger les bus affectés.", true)
                }
            }
        }
    }

    private fun requestPermissionsAndStart() {
        val permissions = mutableListOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        )
        if (Build.VERSION.SDK_INT >= 33) permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        val missing = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isNotEmpty()) {
            requestPermissions(missing.toTypedArray(), REQUEST_PERMISSIONS)
            return
        }
        if (!hasNotificationPermission()) {
            setStatus("Autorise les notifications SmartBus pour afficher le suivi GPS actif.", true)
            return
        }
        startTracking()
    }

    private fun startTracking() {
        val bus = assignedBuses.getOrNull(busSpinner.selectedItemPosition)
        if (bus == null) {
            setStatus("Aucun bus n'est affecté à ce compte.", true)
            return
        }
        if (!isLocationEnabled()) {
            setStatus("Active la localisation/GPS dans les réglages du téléphone.", true)
            return
        }
        val intent = Intent(this, LocationTrackingService::class.java)
            .putExtra(LocationTrackingService.EXTRA_BUS_ID, bus.id)
            .putExtra(LocationTrackingService.EXTRA_REGISTRATION, bus.registration)
        ContextCompat.startForegroundService(this, intent)
        startButton.visibility = View.GONE
        stopButton.visibility = View.VISIBLE
        setStatus("Démarrage du partage GPS pour ${bus.registration}…")
    }

    private fun stopTracking() {
        stopService(Intent(this, LocationTrackingService::class.java))
        showStoppedState()
        setStatus("Partage GPS arrêté.")
    }

    private fun logout() {
        stopTracking()
        val token = tokenStore.read()
        tokenStore.clear()
        loggedInUsername = ""
        assignedBuses = emptyList()
        showLogin()
        if (token != null) {
            executor.execute {
                runCatching { apiClient.logout(token) }
            }
        }
        setStatus("Déconnecté.")
    }

    private fun showLogin() {
        controls.visibility = View.GONE
        form.visibility = View.VISIBLE
        setLoading(false)
    }

    private fun showStoppedState() {
        if (!::startButton.isInitialized) return
        startButton.visibility = View.VISIBLE
        stopButton.visibility = View.GONE
    }

    private fun registerStateReceiver() {
        val filter = IntentFilter(LocationTrackingService.ACTION_STATE)
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(trackingReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("DEPRECATION")
            registerReceiver(trackingReceiver, filter)
        }
        receiverRegistered = true
    }

    private fun isLocationEnabled(): Boolean {
        val manager = getSystemService(Context.LOCATION_SERVICE) as android.location.LocationManager
        return runCatching { manager.isProviderEnabled(android.location.LocationManager.GPS_PROVIDER) }.getOrDefault(false)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode != REQUEST_PERMISSIONS) return
        val locationGranted = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (!locationGranted) {
            setStatus("La permission de localisation est nécessaire au partage GPS.", true)
            return
        }
        if (!hasNotificationPermission()) {
            setStatus("La permission de notification est nécessaire pour rendre le suivi visible.", true)
            return
        }
        startTracking()
    }

    private fun hasNotificationPermission(): Boolean =
        Build.VERSION.SDK_INT < 33 ||
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED

    private fun setLoading(loading: Boolean) {
        progress.visibility = if (loading) View.VISIBLE else View.GONE
        loginButton.isEnabled = !loading
        startButton.isEnabled = !loading && assignedBuses.isNotEmpty()
    }

    private fun setStatus(text: String, error: Boolean = false) {
        statusText.text = text
        statusText.setTextColor(if (error) 0xFFFF8B91.toInt() else 0xFFB9C7D7.toInt())
    }

    private fun createConfigurationScreen(message: String): View {
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(dp(26), dp(30), dp(26), dp(30))
            setBackgroundColor(0xFF0D1624.toInt())
        }
        addText(container, "SMARTBUS · CONDUCTEUR", 13f, 0xFF59D7D0.toInt(), true)
        addText(container, "Configure l'adresse de l'API SmartBus dans le paramètre Gradle smartbusApiBaseUrl, puis reconstruis l'application.", 15f, 0xFFF1F5FB.toInt(), top = 18)
        addText(container, message, 12f, 0xFFFF8B91.toInt(), top = 14)
        return container
    }

    private fun editText(hint: String): android.widget.EditText =
        android.widget.EditText(this).apply {
            this.hint = hint
            setSingleLine(true)
            setTextColor(0xFFF1F5FB.toInt())
            setHintTextColor(0xFF8597AC.toInt())
            setPadding(dp(12), 0, dp(12), 0)
            setBackgroundColor(0xFF18263A.toInt())
        }

    private fun button(label: String): Button =
        Button(this).apply {
            text = label
            isAllCaps = false
            setTextColor(0xFF0D2026.toInt())
            setBackgroundColor(0xFF59D7D0.toInt())
            minHeight = dp(48)
        }

    private fun addText(
        parent: LinearLayout,
        text: String,
        size: Float,
        color: Int,
        bold: Boolean = false,
        top: Int = 0,
    ): TextView {
        val view = TextView(this).apply {
            this.text = text
            textSize = size
            setTextColor(color)
            if (bold) setTypeface(typeface, android.graphics.Typeface.BOLD)
        }
        parent.addView(view, matchWidthWrap(top))
        return view
    }

    private fun matchWidthWrap(top: Int = 0) =
        LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            topMargin = dp(top)
        }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    companion object {
        private const val REQUEST_PERMISSIONS = 70
    }
}
