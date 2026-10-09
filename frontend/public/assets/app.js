(() => {
  "use strict";

  const API = "/api";
  const tokenKey = "smartbus_token";
  const byId = (id) => document.getElementById(id);
  let token = sessionStorage.getItem(tokenKey) || "";
  let currentRole = "";
  let registerMode = false;
  let buses = [];
  let toastTimer;

  async function request(path, options = {}) {
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    if (options.body) headers["Content-Type"] = "application/json";
    if (token) headers.Authorization = `Token ${token}`;
    const response = await fetch(`${API}${path}`, {
      ...options,
      headers,
      credentials: "same-origin",
    });
    if (response.status === 204) return null;
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = payload.detail || Object.values(payload).flat().join(" ") || "Une erreur est survenue.";
      throw new Error(message);
    }
    return payload;
  }

  function notify(message, isError = false) {
    const toast = byId("toast");
    toast.textContent = message;
    toast.style.borderColor = isError ? "#8e454e" : "";
    toast.classList.add("show");
    window.clearTimeout(toastTimer);
    toastTimer = window.setTimeout(() => toast.classList.remove("show"), 3500);
  }

  function setMessage(element, text, error = false) {
    element.textContent = text;
    element.classList.toggle("error", error);
  }

  function formatStatus(status) {
    return {
      AVAILABLE: "Disponible",
      IN_SERVICE: "En service",
      RENTED: "Loué",
      MAINTENANCE: "Maintenance",
      OFFLINE: "Hors ligne",
      FOR_SALE: "À vendre",
      SOLD: "Vendu",
    }[status] || status;
  }

  function formatMoney(value) {
    return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(Number(value));
  }

  function renderFleet(items) {
    const list = byId("fleet-list");
    const empty = byId("fleet-empty");
    byId("fleet-count").textContent = String(items.length);
    byId("stat-total").textContent = String(items.length);
    byId("stat-available").textContent = String(items.filter((bus) => bus.status === "AVAILABLE").length);
    byId("stat-service").textContent = String(items.filter((bus) => bus.status === "IN_SERVICE").length);
    list.replaceChildren();
    empty.classList.toggle("hidden", items.length !== 0);
    items.slice(0, 6).forEach((bus) => {
      const row = document.createElement("div");
      row.className = "fleet-row";
      const icon = document.createElement("span");
      icon.className = "bus-avatar";
      icon.textContent = "▣";
      const name = document.createElement("div");
      name.className = "fleet-name";
      const title = document.createElement("strong");
      title.textContent = bus.registration;
      const subtitle = document.createElement("small");
      subtitle.textContent = `${bus.make} ${bus.model} · ${bus.seats} places`;
      if (bus.is_demo) subtitle.textContent += " · DEMO DATA";
      name.append(title, subtitle);
      const status = document.createElement("span");
      status.className = `status-badge${["OFFLINE", "MAINTENANCE", "SOLD"].includes(bus.status) ? " offline" : ""}`;
      status.textContent = formatStatus(bus.status);
      row.append(icon, name, status);
      list.append(row);
    });
    if (!items.length) list.classList.add("hidden");
    else list.classList.remove("hidden");

    const select = byId("booking-bus");
    select.replaceChildren(new Option("Choisir un bus disponible", ""));
    items.filter((bus) => bus.status === "AVAILABLE").forEach((bus) => {
      select.add(new Option(`${bus.registration} · ${bus.make} ${bus.model} · ${formatMoney(bus.daily_rate)} XAF/jour`, String(bus.id)));
    });
  }

  function renderPositions(items) {
    const pins = byId("map-pins");
    pins.replaceChildren();
    byId("map-empty").classList.toggle("hidden", items.length > 0);
    const emptyTitle = byId("map-empty").querySelector("strong");
    const emptyCopy = byId("map-empty").querySelector("p");
    if (!["SUPER_ADMIN", "ADMIN", "FLEET_MANAGER"].includes(currentRole)) {
      emptyTitle.textContent = token ? "Accès flotte requis" : "Connectez-vous à l'espace flotte";
      emptyCopy.textContent = "Les positions GPS sont réservées aux rôles de gestion de flotte et aux conducteurs.";
    } else {
      emptyTitle.textContent = "Aucune position GPS reçue";
      emptyCopy.textContent = "Les positions apparaîtront ici lorsqu'un tracker publiera des données.";
    }
    const latitudes = items.map((item) => Number(item.latitude));
    const longitudes = items.map((item) => Number(item.longitude));
    const minLat = Math.min(...latitudes);
    const maxLat = Math.max(...latitudes);
    const minLng = Math.min(...longitudes);
    const maxLng = Math.max(...longitudes);
    items.slice(0, 20).forEach((position, index) => {
      const pin = document.createElement("span");
      pin.className = "map-pin";
      pin.title = `${position.registration}: ${position.latitude}, ${position.longitude}`;
      const longitudeRange = maxLng - minLng;
      const latitudeRange = maxLat - minLat;
      pin.style.left = `${12 + (longitudeRange ? ((Number(position.longitude) - minLng) / longitudeRange) * 76 : 38)}%`;
      pin.style.top = `${15 + (latitudeRange ? ((maxLat - Number(position.latitude)) / latitudeRange) * 65 : 32)}%`;
      pins.append(pin);
    });
  }

  async function loadData() {
    const [busResult, positionResult] = await Promise.all([
      request("/fleet/buses/?page_size=100"),
      ["SUPER_ADMIN", "ADMIN", "FLEET_MANAGER"].includes(currentRole)
        ? request("/tracking/positions/latest/")
        : Promise.resolve([]),
    ]);
    byId("api-status").lastChild.textContent = "API DISPONIBLE";
    byId("sidebar-api-status").textContent = "API disponible";
    buses = busResult.results || busResult;
    renderFleet(buses);
    renderPositions(positionResult.results || positionResult);
    if (token) {
      try {
        const dashboard = await request("/dashboard/");
        byId("stat-bookings").textContent = String(dashboard.bookings.total);
        byId("booking-caption").textContent = `${dashboard.bookings.pending} en attente`;
      } catch (error) {
        byId("stat-bookings").textContent = "—";
      }
      await loadBookings();
    }
  }

  async function loadBookings() {
    const list = byId("booking-list");
    list.replaceChildren();
    if (!token) return;
    try {
      const data = await request("/bookings/?page_size=5");
      (data.results || data).slice(0, 5).forEach((booking) => {
        const row = document.createElement("div");
        row.className = "booking-item";
        const detail = document.createElement("span");
        detail.textContent = `${booking.bus_registration} · ${booking.start_date} → ${booking.end_date} · ${formatMoney(booking.total_price)} XAF`;
        const status = document.createElement("span");
        status.textContent = booking.status;
        row.append(detail, status);
        if (booking.status === "PENDING") {
          const cancel = document.createElement("button");
          cancel.type = "button";
          cancel.className = "booking-cancel";
          cancel.dataset.bookingId = String(booking.id);
          cancel.textContent = "Annuler";
          row.append(cancel);
        }
        list.append(row);
      });
    } catch (error) {
      notify(error.message, true);
    }
  }

  function updateIdentity(user) {
    currentRole = user ? user.role : "";
    byId("user-name").textContent = user ? user.username : "Visiteur";
    byId("user-role").textContent = user ? user.role.replaceAll("_", " ") : "Espace public";
    byId("logout-button").classList.toggle("hidden", !user);
    byId("auth-open").classList.toggle("hidden", Boolean(user));
    byId("register-open").classList.toggle("hidden", Boolean(user));
  }

  function showAuth(isRegister) {
    registerMode = isRegister;
    byId("auth-title").textContent = isRegister ? "Créer votre espace" : "Bienvenue";
    byId("auth-eyebrow").textContent = isRegister ? "NOUVEAU COMPTE CLIENT" : "ACCÈS SÉCURISÉ";
    byId("auth-description").textContent = isRegister
      ? "Créez un compte client pour demander une réservation."
      : "Connectez-vous pour gérer vos réservations.";
    byId("auth-submit").textContent = isRegister ? "Créer mon compte" : "Se connecter";
    byId("auth-mode-toggle").textContent = isRegister ? "J'ai déjà un compte" : "Créer un compte client";
    byId("email-field").classList.toggle("hidden", !isRegister);
    byId("confirm-field").classList.toggle("hidden", !isRegister);
    byId("auth-message").textContent = "";
    byId("auth-dialog").showModal();
  }

  byId("auth-open").addEventListener("click", () => showAuth(false));
  byId("register-open").addEventListener("click", () => showAuth(true));
  byId("auth-mode-toggle").addEventListener("click", () => showAuth(!registerMode));

  byId("auth-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload = Object.fromEntries(form.entries());
    const endpoint = registerMode ? "/auth/register/" : "/auth/login/";
    try {
      const result = await request(endpoint, { method: "POST", body: JSON.stringify(payload) });
      token = result.token;
      sessionStorage.setItem(tokenKey, token);
      updateIdentity(result.user);
      byId("auth-dialog").close();
      formElement.reset();
      notify("Connexion établie.");
      await loadData();
    } catch (error) {
      setMessage(byId("auth-message"), error.message, true);
    }
  });

  byId("logout-button").addEventListener("click", async () => {
    try {
      await request("/auth/logout/", { method: "POST" });
    } catch (error) {
      notify(`Déconnexion locale effectuée, mais le serveur n'a pas confirmé la révocation : ${error.message}`, true);
    }
    token = "";
    sessionStorage.removeItem(tokenKey);
    updateIdentity(null);
    byId("stat-bookings").textContent = "—";
    byId("booking-caption").textContent = "Connectez-vous pour voir les vôtres";
    byId("booking-list").replaceChildren();
    notify("Vous êtes déconnecté.");
  });

  byId("booking-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!token) {
      showAuth(false);
      setMessage(byId("auth-message"), "Connectez-vous avant de réserver.");
      return;
    }
    const formElement = event.currentTarget;
    const values = Object.fromEntries(new FormData(formElement).entries());
    values.bus = Number(values.bus);
    values.passengers = Number(values.passengers);
    try {
      await request("/bookings/", { method: "POST", body: JSON.stringify(values) });
      setMessage(byId("booking-message"), "Demande envoyée. Vous la retrouverez dans votre espace.");
      formElement.reset();
      await loadData();
    } catch (error) {
      setMessage(byId("booking-message"), error.message, true);
    }
  });

  byId("booking-list").addEventListener("click", async (event) => {
    const button = event.target.closest(".booking-cancel");
    if (!button) return;
    button.disabled = true;
    try {
      await request(`/bookings/${button.dataset.bookingId}/cancel/`, { method: "POST" });
      notify("Réservation annulée.");
      await loadData();
    } catch (error) {
      button.disabled = false;
      notify(error.message, true);
    }
  });

  const today = new Date();
  const localToday = new Date(today.getTime() - today.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
  byId("booking-form").elements.start_date.min = localToday;
  byId("booking-form").elements.end_date.min = localToday;
  byId("booking-form").elements.start_date.addEventListener("change", (event) => {
    const endDate = byId("booking-form").elements.end_date;
    endDate.min = event.target.value || localToday;
    if (endDate.value && endDate.value < endDate.min) endDate.value = "";
  });

  (async () => {
    if (token) {
      try {
        updateIdentity(await request("/auth/me/"));
      } catch (error) {
        token = "";
        sessionStorage.removeItem(tokenKey);
        updateIdentity(null);
        notify(`Session à renouveler : ${error.message}`, true);
      }
    } else {
      updateIdentity(null);
    }
    await loadData();
  })().catch((error) => {
    byId("api-status").lastChild.textContent = "API INDISPONIBLE";
    byId("sidebar-api-status").textContent = "API indisponible";
    notify(`API indisponible : ${error.message}`, true);
    byId("fleet-list").classList.add("hidden");
    byId("fleet-empty").classList.remove("hidden");
  });
})();
