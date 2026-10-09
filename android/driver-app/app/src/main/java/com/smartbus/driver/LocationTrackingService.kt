package com.smartbus.driver

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import java.io.IOException
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

class LocationTrackingService : Service(), LocationListener {
    private val networkExecutor = Executors.newSingleThreadExecutor()
    private val sending = AtomicBoolean(false)
    private lateinit var locationManager: LocationManager
    private lateinit var tokenStore: SecureTokenStore
    private var busId = -1L
    private var registration = ""
    private var lastAttemptElapsed = 0L

    override fun onCreate() {
        super.onCreate()
        tokenStore = SecureTokenStore(this)
        locationManager = getSystemService(Context.LOCATION_SERVICE) as LocationManager
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopTracking()
            return START_NOT_STICKY
        }

        val incomingBusId = intent?.getLongExtra(EXTRA_BUS_ID, -1L) ?: -1L
        val incomingRegistration = intent?.getStringExtra(EXTRA_REGISTRATION).orEmpty()
        val token = tokenStore.read()
        if (incomingBusId <= 0 || incomingRegistration.isBlank() || token.isNullOrBlank()) {
            stopSelf()
            return START_NOT_STICKY
        }
        busId = incomingBusId
        registration = incomingRegistration

        val notification = buildNotification("Connexion au GPS…")
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ServiceCompat.startForeground(
                this,
                NOTIFICATION_ID,
                notification,
                android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION,
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }

        if (!hasLocationPermission()) {
            updateNotification("Permission GPS retirée — partage arrêté")
            stopTracking()
            return START_NOT_STICKY
        }

        try {
            locationManager.requestLocationUpdates(
                LocationManager.GPS_PROVIDER,
                LOCATION_INTERVAL_MS,
                MIN_DISTANCE_METERS,
                this,
                Looper.getMainLooper(),
            )
            getSharedPreferences(TRACKING_PREFS, Context.MODE_PRIVATE).edit()
                .putBoolean(TRACKING_ACTIVE, true)
                .putString(TRACKING_REGISTRATION, registration)
                .apply()
            publishState("Partage GPS actif pour $registration", false)
            updateNotification("Recherche de la position GPS…")
        } catch (error: SecurityException) {
            publishState("Autorisation GPS manquante", true)
            stopTracking()
        } catch (error: IllegalArgumentException) {
            publishState("Fournisseur GPS indisponible", true)
            stopTracking()
        }
        return START_NOT_STICKY
    }

    override fun onLocationChanged(location: Location) {
        val now = android.os.SystemClock.elapsedRealtime()
        if (now - lastAttemptElapsed < SEND_INTERVAL_MS || !sending.compareAndSet(false, true)) return
        lastAttemptElapsed = now

        val token = tokenStore.read()
        if (token.isNullOrBlank()) {
            publishState("Session expirée — reconnecte-toi", true)
            stopTracking()
            return
        }

        updateNotification("Envoi de la position de $registration…")
        networkExecutor.execute {
            try {
                ApiClient().reportPosition(
                    token = token,
                    busId = busId,
                    latitude = location.latitude,
                    longitude = location.longitude,
                    speedKph = if (location.hasSpeed()) location.speed * 3.6f else 0f,
                    heading = if (location.hasBearing()) location.bearing else 0f,
                )
                val accuracy = if (location.hasAccuracy()) " · ±${location.accuracy.toInt()} m" else ""
                updateNotification("Position envoyée ${java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.getDefault()).format(java.util.Date())}$accuracy")
                publishState("Position partagée · ${location.latitude}, ${location.longitude}", false)
            } catch (error: ApiException) {
                val expired = error.statusCode == 401 || error.statusCode == 403
                updateNotification(if (expired) "Accès refusé — vérifie ton compte conducteur" else "Envoi en échec — nouvelle tentative au prochain point GPS")
                publishState(error.message ?: "Envoi GPS impossible", true)
                if (expired) stopTracking()
            } catch (error: IOException) {
                updateNotification("Réseau indisponible — nouvelle tentative au prochain point GPS")
                publishState("Position non envoyée : ${error.message ?: "erreur réseau"}", true)
            } finally {
                sending.set(false)
            }
        }
    }

    override fun onProviderDisabled(provider: String) {
        if (provider == LocationManager.GPS_PROVIDER) {
            publishState("Active le GPS du téléphone pour continuer", true)
            updateNotification("GPS désactivé sur le téléphone")
        }
    }

    override fun onProviderEnabled(provider: String) {
        if (provider == LocationManager.GPS_PROVIDER) {
            publishState("GPS disponible — attente de la position", false)
        }
    }

    override fun onStatusChanged(provider: String?, status: Int, extras: android.os.Bundle?) = Unit

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        stopLocationUpdates()
        clearTrackingState()
        networkExecutor.shutdownNow()
        super.onDestroy()
    }

    private fun stopTracking() {
        stopLocationUpdates()
        clearTrackingState()
        publishState("Partage GPS arrêté", false)
        ServiceCompat.stopForeground(this, ServiceCompat.STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    private fun stopLocationUpdates() {
        runCatching { locationManager.removeUpdates(this) }
    }

    private fun clearTrackingState() {
        getSharedPreferences(TRACKING_PREFS, Context.MODE_PRIVATE).edit()
            .putBoolean(TRACKING_ACTIVE, false)
            .remove(TRACKING_REGISTRATION)
            .apply()
    }

    private fun hasLocationPermission(): Boolean =
        checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val channel = NotificationChannel(
            CHANNEL_ID,
            getString(R.string.notification_channel_name),
            NotificationManager.IMPORTANCE_LOW,
        ).apply {
            description = getString(R.string.notification_channel_description)
            setShowBadge(false)
        }
        (getSystemService(NotificationManager::class.java)).createNotificationChannel(channel)
    }

    private fun buildNotification(content: String): Notification {
        val openApp = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val stopIntent = PendingIntent.getService(
            this,
            1,
            Intent(this, LocationTrackingService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setContentTitle("SmartBus · $registration")
            .setContentText(content)
            .setContentIntent(openApp)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .addAction(0, "Arrêter", stopIntent)
            .build()
    }

    private fun updateNotification(text: String) {
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID, buildNotification(text))
    }

    private fun publishState(text: String, isError: Boolean) {
        sendBroadcast(
            Intent(ACTION_STATE)
                .setPackage(packageName)
                .putExtra(EXTRA_STATE, text)
                .putExtra(EXTRA_ERROR, isError),
        )
    }

    companion object {
        const val ACTION_STOP = "com.smartbus.driver.STOP_TRACKING"
        const val ACTION_STATE = "com.smartbus.driver.TRACKING_STATE"
        const val EXTRA_BUS_ID = "bus_id"
        const val EXTRA_REGISTRATION = "registration"
        const val EXTRA_STATE = "state"
        const val EXTRA_ERROR = "error"
        private const val CHANNEL_ID = "smartbus_location_tracking"
        private const val NOTIFICATION_ID = 501
        private const val LOCATION_INTERVAL_MS = 5_000L
        private const val SEND_INTERVAL_MS = 10_000L
        private const val MIN_DISTANCE_METERS = 0f
        const val TRACKING_PREFS = "tracking_state"
        const val TRACKING_ACTIVE = "active"
        const val TRACKING_REGISTRATION = "registration"
    }
}
