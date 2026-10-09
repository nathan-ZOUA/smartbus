(() => {
  "use strict";

  const tokenKey = "smartbus_driver_token";
  const byId = (id) => document.getElementById(id);
  let token = sessionStorage.getItem(tokenKey) || "";
  let watchId = null;
  let sendTimer = null;
  let latestPosition = null;
  let lastSentPositionTimestamp = null;
  let lastAttemptAt = 0;
  let sending = false;

  class ApiError extends Error {
    constructor(message, status) {
      super(message);
      this.status = status;
    }
  }

  async function api(path, options = {}) {
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    if (options.body) headers["Content-Type"] = "application/json";
    if (token) headers.Authorization = `Token ${token}`;
    const response = await fetch(`/api${path}`, { ...options, headers, credentials: "same-origin" });
    if (response.status === 204) return null;
    let payload;
    try {
      payload = await response.json();
    } catch {
      if (response.ok) throw new Error("Le serveur a renvoyé une réponse invalide.");
      payload = null;
    }
    if (!response.ok) {
      const detail = payload && typeof payload === "object"
        ? payload.detail || Object.values(payload).flat().filter((value) => typeof value === "string").join(" ")
        : "";
      throw new ApiError(detail || `Erreur API ${response.status}`, response.status);
    }
    return payload;
  }

  function message(text, error = false) {
    byId("driver-message").textContent = text;
    byId("driver-message").classList.toggle("error", error);
  }

  function stopSharing() {
    if (watchId !== null && navigator.geolocation) {
      navigator.geolocation.clearWatch(watchId);
    }
    watchId = null;
    if (sendTimer !== null) window.clearInterval(sendTimer);
    sendTimer = null;
    latestPosition = null;
    lastSentPositionTimestamp = null;
    lastAttemptAt = 0;
    byId("start-sharing").classList.remove("hidden");
    byId("stop-sharing").classList.add("hidden");
    byId("gps-dot").classList.remove("active");
    byId("gps-state").textContent = "Partage désactivé";
    byId("gps-detail").textContent = "La position n'est pas transmise.";
  }

  async function sendLatestPosition() {
    if (watchId === null || !latestPosition || sending || Date.now() - lastAttemptAt < 10000) return;
    if (lastSentPositionTimestamp !== null && latestPosition.timestamp <= lastSentPositionTimestamp) return;
    if (Date.now() - latestPosition.timestamp > 60000) {
      byId("gps-state").textContent = "En attente d'une position GPS récente";
      byId("gps-detail").textContent = "Garde cette page ouverte et vérifie le signal GPS.";
      return;
    }
    const busId = Number(byId("driver-bus").value);
    if (!busId) {
      stopSharing();
      message("Aucun bus affecté à ce compte. Contacte le gestionnaire de flotte.", true);
      return;
    }
    const position = latestPosition;
    sending = true;
    lastAttemptAt = Date.now();
    try {
      await api("/tracking/positions/report/", {
        method: "POST",
        body: JSON.stringify({
          bus: busId,
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          speed_kph: position.coords.speed == null
            ? 0
            : Math.min(400, Math.max(0, position.coords.speed * 3.6)),
          heading: position.coords.heading == null
            ? 0
            : Math.round(position.coords.heading) % 360,
        }),
      });
      if (watchId === null) return;
      lastSentPositionTimestamp = position.timestamp;
      byId("gps-dot").classList.add("active");
      byId("gps-state").textContent = "Position partagée";
      byId("gps-detail").textContent = `Dernier envoi ${new Date().toLocaleTimeString()} · précision ±${Math.round(position.coords.accuracy)} m`;
      message("Position envoyée à SmartBus.");
    } catch (error) {
      if (watchId === null) return;
      byId("gps-dot").classList.add("error");
      byId("gps-state").textContent = "Envoi impossible";
      byId("gps-detail").textContent = error.message;
      message(error.message, true);
      if (error instanceof ApiError && [401, 403].includes(error.status)) {
        stopSharing();
        message("Session invalide ou accès refusé. Déconnecte-toi puis reconnecte-toi.", true);
      }
    } finally {
      sending = false;
    }
  }

  function receivePosition(position) {
    latestPosition = position;
    void sendLatestPosition();
  }

  async function loadDriverBuses() {
    const buses = await api("/tracking/positions/my-buses/");
    const select = byId("driver-bus");
    select.replaceChildren();
    buses.forEach((bus) => select.add(new Option(`${bus.registration} · ${bus.status}`, String(bus.id))));
    if (!buses.length) {
      select.add(new Option("Aucun bus affecté", ""));
      byId("start-sharing").disabled = true;
      message("Le gestionnaire doit affecter un bus à ton profil conducteur.", true);
      return;
    }
    byId("start-sharing").disabled = false;
  }

  async function showDriverControls() {
    const user = await api("/auth/me/");
    if (user.role !== "DRIVER") throw new Error("Ce compte n'a pas le rôle Conducteur.");
    byId("driver-login").classList.add("hidden");
    byId("driver-controls").classList.remove("hidden");
    await loadDriverBuses();
  }

  byId("driver-login").addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      const result = await api("/auth/login/", { method: "POST", body: JSON.stringify(values) });
      token = result.token;
      sessionStorage.setItem(tokenKey, token);
      await showDriverControls();
    } catch (error) {
      token = "";
      sessionStorage.removeItem(tokenKey);
      message(error.message, true);
    }
  });

  byId("start-sharing").addEventListener("click", () => {
    if (!navigator.geolocation) {
      message("Ce navigateur ne propose pas la géolocalisation.", true);
      return;
    }
    if (!window.isSecureContext) {
      message("La géolocalisation du téléphone exige une connexion HTTPS sécurisée.", true);
      return;
    }
    if (!byId("driver-bus").value) {
      message("Aucun bus affecté à ton compte. Contacte le gestionnaire.", true);
      return;
    }
    message("Demande d'autorisation GPS…");
    try {
      latestPosition = null;
      lastSentPositionTimestamp = null;
      lastAttemptAt = 0;
      watchId = navigator.geolocation.watchPosition(
        receivePosition,
        (error) => {
          if (watchId === null) return;
          byId("gps-dot").classList.add("error");
          byId("gps-state").textContent = "Position indisponible";
          const reason = error.code === 1
            ? "Autorisation refusée. Autorise la localisation dans les réglages du navigateur."
            : error.code === 2
              ? "Signal GPS indisponible. Réessaie à l'extérieur."
              : "Délai dépassé en attendant le GPS.";
          byId("gps-detail").textContent = reason;
          message(reason, true);
          if (error.code === 1) stopSharing();
        },
        { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 },
      );
      sendTimer = window.setInterval(() => void sendLatestPosition(), 10000);
      byId("start-sharing").classList.add("hidden");
      byId("stop-sharing").classList.remove("hidden");
      byId("gps-dot").classList.remove("error");
      byId("gps-state").textContent = "Recherche du GPS";
      byId("gps-detail").textContent = "Garde cette page ouverte pour transmettre la position.";
    } catch (error) {
      stopSharing();
      message(`Impossible de démarrer le GPS : ${error.message}`, true);
    }
  });

  byId("stop-sharing").addEventListener("click", stopSharing);
  document.addEventListener("visibilitychange", () => {
    if (watchId === null) return;
    if (document.visibilityState === "hidden") {
      byId("gps-state").textContent = "Page en arrière-plan";
      byId("gps-detail").textContent = "Le navigateur peut suspendre le GPS. Rouvre cette page pour reprendre.";
      return;
    }
    byId("gps-state").textContent = "Partage GPS actif";
    byId("gps-detail").textContent = "Page visible. En attente de la prochaine position.";
    void sendLatestPosition();
  });
  window.addEventListener("offline", () => {
    if (watchId === null) return;
    byId("gps-dot").classList.add("error");
    byId("gps-state").textContent = "Hors connexion";
    byId("gps-detail").textContent = "Le partage reprendra à la prochaine position GPS quand Internet reviendra.";
    message("Connexion Internet perdue; aucune position ne peut être envoyée.", true);
  });
  window.addEventListener("online", () => {
    if (watchId === null) return;
    byId("gps-dot").classList.remove("error");
    byId("gps-state").textContent = "Connexion rétablie";
    byId("gps-detail").textContent = "En attente de la prochaine position GPS.";
    message("Connexion rétablie; le partage GPS reprend.");
    void sendLatestPosition();
  });
  byId("driver-logout").addEventListener("click", async () => {
    stopSharing();
    try {
      await api("/auth/logout/", { method: "POST" });
    } catch (error) {
      message(`Déconnexion locale; le serveur n'a pas confirmé la révocation : ${error.message}`, true);
    }
    token = "";
    sessionStorage.removeItem(tokenKey);
    byId("driver-controls").classList.add("hidden");
    byId("driver-login").classList.remove("hidden");
  });
  window.addEventListener("pagehide", stopSharing);

  if (token) {
    showDriverControls().catch((error) => {
      token = "";
      sessionStorage.removeItem(tokenKey);
      message(error.message, true);
    });
  }
})();
