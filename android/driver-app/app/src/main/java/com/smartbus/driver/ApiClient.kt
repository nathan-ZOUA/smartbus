package com.smartbus.driver

import android.os.Build
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

data class AssignedBus(val id: Long, val registration: String, val status: String)

class ApiException(val statusCode: Int, message: String) : IOException(message)

class ApiClient {
    private val baseUrl = BuildConfig.API_BASE_URL.trimEnd('/') + "/"

    init {
        val localEmulator = Build.FINGERPRINT.startsWith("generic") ||
            Build.MODEL.contains("Emulator", ignoreCase = true)
        require(
            baseUrl.startsWith("https://", ignoreCase = true) ||
                (BuildConfig.DEBUG && localEmulator && baseUrl.startsWith("http://10.0.2.2:"))
        ) {
            "Configure l'URL HTTPS de l'API SmartBus pour ce téléphone."
        }
        require(!baseUrl.contains("replace-with-your-smartbus-domain")) {
            "Configure l'URL HTTPS de ton API SmartBus dans smartbusApiBaseUrl."
        }
    }

    fun login(username: String, password: String): Pair<String, String> {
        val response = post(
            "auth/login/",
            JSONObject().put("username", username).put("password", password),
        )
        val user = response.getJSONObject("user")
        val role = user.getString("role")
        if (role != "DRIVER") {
            throw IOException("Ce compte n'a pas le rôle Conducteur.")
        }
        return response.getString("token") to user.getString("username")
    }

    fun getAssignedBuses(token: String): List<AssignedBus> {
        val response = request("GET", "tracking/positions/my-buses/", token, null)
        val json = JSONArray(response)
        return (0 until json.length()).map { index ->
            val item = json.getJSONObject(index)
            AssignedBus(
                id = item.getLong("id"),
                registration = item.getString("registration"),
                status = item.getString("status"),
            )
        }
    }

    fun reportPosition(token: String, busId: Long, latitude: Double, longitude: Double, speedKph: Float, heading: Float) {
        val payload = JSONObject()
            .put("bus", busId)
            .put("latitude", latitude)
            .put("longitude", longitude)
            .put("speed_kph", speedKph.coerceAtLeast(0f).toDouble())
            .put("heading", heading.toInt().coerceIn(0, 359))
        request("POST", "tracking/positions/report/", token, payload)
    }

    fun logout(token: String) {
        request("POST", "auth/logout/", token, JSONObject())
    }

    private fun post(path: String, body: JSONObject): JSONObject =
        JSONObject(request("POST", path, null, body))

    private fun request(method: String, path: String, token: String?, body: JSONObject?): String {
        val encodedPath = path.trim('/').split('/').joinToString("/") {
            URLEncoder.encode(it, "UTF-8")
        } + "/"
        val connection = (URL(baseUrl + encodedPath).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 10_000
            readTimeout = 10_000
            setRequestProperty("Accept", "application/json")
            if (token != null) setRequestProperty("Authorization", "Token $token")
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
            }
        }
        try {
            if (body != null) {
                connection.outputStream.use { stream ->
                    stream.write(body.toString().toByteArray(Charsets.UTF_8))
                }
            }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val response = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (status !in 200..299) {
                val message = runCatching { JSONObject(response).optString("detail") }
                    .getOrNull()
                    ?.takeIf { it.isNotBlank() }
                    ?: "Erreur serveur ($status)."
                throw ApiException(status, message)
            }
            return response
        } finally {
            connection.disconnect()
        }
    }
}
