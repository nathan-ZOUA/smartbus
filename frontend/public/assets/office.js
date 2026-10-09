(() => {
  "use strict";

  const tokenKey = "smartbus_token";
  const byId = (id) => document.getElementById(id);
  let token = sessionStorage.getItem(tokenKey) || "";
  let role = "";
  let canManageSales = false;
  let canManageMaintenance = false;

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
    const response = await fetch(`/api${path}`, {
      ...options,
      headers,
      credentials: "same-origin",
    });
    if (response.status === 204) return null;
    let data;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    if (!response.ok) {
      const message = data && typeof data === "object"
        ? data.detail || Object.values(data).flat().filter((value) => typeof value === "string").join(" ")
        : "";
      throw new ApiError(message || `Erreur API ${response.status}`, response.status);
    }
    return data;
  }

  function notify(text, error = false) {
    const element = byId("office-message");
    element.textContent = text;
    element.classList.toggle("error", error);
  }

  function rows(data) {
    return Array.isArray(data) ? data : data.results || [];
  }

  function statusLabel(status) {
    return {
      REQUESTED: "À traiter",
      APPROVED: "Approuvée",
      PENDING: "À vérifier",
      VERIFIED: "Confirmé",
      REJECTED: "Refusé",
      PAID: "Payée",
      IN_PROGRESS: "En cours",
      COMPLETED: "Terminée",
      CANCELLED: "Annulée",
      NORMAL: "Normale",
      LOW: "Faible",
      HIGH: "Haute",
      URGENT: "Urgente",
    }[status] || status;
  }

  function money(value) {
    return `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(Number(value))} XAF`;
  }

  function makeCard(title, details, status) {
    const card = document.createElement("article");
    card.className = "portal-card";
    const header = document.createElement("div");
    header.className = "portal-card-header";
    const heading = document.createElement("strong");
    heading.textContent = title;
    header.append(heading);
    if (status) {
      const badge = document.createElement("span");
      badge.className = `portal-status ${status.toLowerCase()}`;
      badge.textContent = statusLabel(status);
      header.append(badge);
    }
    card.append(header);
    details.forEach((detail) => {
      const text = document.createElement("p");
      text.textContent = detail;
      card.append(text);
    });
    const actions = document.createElement("div");
    actions.className = "portal-actions";
    card.append(actions);
    return { card, actions };
  }

  function button(container, label, handler, quiet = false) {
    const element = document.createElement("button");
    element.type = "button";
    element.className = `button ${quiet ? "button-quiet" : "button-primary"}`;
    element.textContent = label;
    element.addEventListener("click", async () => {
      element.disabled = true;
      try {
        await handler();
      } catch (error) {
        notify(error.message, true);
      } finally {
        element.disabled = false;
      }
    });
    container.append(element);
  }

  function empty(container, text) {
    const note = document.createElement("p");
    note.className = "portal-empty";
    note.textContent = text;
    container.replaceChildren(note);
  }

  async function transition(path, body) {
    await api(path, {
      method: "POST",
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    notify("Opération enregistrée.");
    await load();
  }

  function renderSales(orders) {
    const container = byId("office-sales");
    container.replaceChildren();
    if (!orders.length) {
      empty(container, "Aucune demande de vente.");
      return;
    }
    orders.forEach((order) => {
      const { card, actions } = makeCard(
        `${order.bus_registration} · ${order.customer_name}`,
        [`${order.bus_make} ${order.bus_model}`, `${money(order.amount)} · VTE-${order.id}`],
        order.status,
      );
      if (order.status === "REQUESTED") {
        button(actions, "Approuver", () => transition(`/sales/orders/${order.id}/approve/`));
      }
      if (["REQUESTED", "APPROVED"].includes(order.status)) {
        button(actions, "Annuler", () => transition(`/sales/orders/${order.id}/cancel/`), true);
      }
      container.append(card);
    });
  }

  function renderPayments(payments) {
    const container = byId("office-payments");
    container.replaceChildren();
    const pending = payments.filter((payment) => payment.status === "PENDING");
    if (!pending.length) {
      empty(container, "Aucune déclaration de paiement en attente.");
      return;
    }
    pending.forEach((payment) => {
      const { card, actions } = makeCard(
        `${payment.order_reference} · ${payment.customer}`,
        [
          `${payment.bus_registration} · ${money(payment.amount)}`,
          `Orange Money · référence ${payment.transaction_reference}`,
          payment.sender_phone ? `Émetteur : ${payment.sender_phone}` : "Numéro émetteur non indiqué",
          `Déclaré le ${new Date(payment.created_at).toLocaleString("fr-FR")}`,
        ],
        payment.status,
      );
      button(actions, "Confirmer après vérification", () => transition(`/payments/attempts/${payment.id}/verify/`));
      button(actions, "Refuser", async () => {
        const reason = window.prompt("Motif du refus (obligatoire) :");
        if (reason === null) return;
        if (!reason.trim()) {
          throw new Error("Un motif est nécessaire avant de refuser une référence.");
        }
        await transition(`/payments/attempts/${payment.id}/reject/`, { reason: reason.trim() });
      }, true);
      container.append(card);
    });
  }

  function renderMaintenance(orders) {
    const container = byId("office-maintenance");
    container.replaceChildren();
    if (!orders.length) {
      empty(container, "Aucun ordre de maintenance.");
      return;
    }
    orders.forEach((order) => {
      const details = [`${order.priority} · ${order.description}`];
      if (order.odometer_km !== null) details.push(`Kilométrage : ${order.odometer_km.toLocaleString("fr-FR")} km`);
      if (order.estimated_cost !== null) details.push(`Estimé : ${money(order.estimated_cost)}`);
      if (order.actual_cost !== null) details.push(`Réel : ${money(order.actual_cost)}`);
      const { card, actions } = makeCard(
        `${order.bus_registration} · MNT-${order.id}`,
        details,
        order.status,
      );
      if (order.status === "REQUESTED") {
        button(actions, "Approuver", () => transition(`/maintenance/orders/${order.id}/approve/`));
        button(actions, "Annuler", () => transition(`/maintenance/orders/${order.id}/cancel/`), true);
      } else if (order.status === "APPROVED") {
        button(actions, "Démarrer les travaux", () => transition(`/maintenance/orders/${order.id}/start/`));
        button(actions, "Annuler", () => transition(`/maintenance/orders/${order.id}/cancel/`), true);
      } else if (order.status === "IN_PROGRESS") {
        button(actions, "Terminer les travaux", async () => {
          const actualCost = window.prompt("Coût réel des travaux en XAF :");
          if (actualCost === null) return;
          if (!/^\d+(\.\d{1,2})?$/.test(actualCost.trim())) {
            throw new Error("Saisis un coût valide, par exemple 85000.");
          }
          await transition(`/maintenance/orders/${order.id}/complete/`, {
            actual_cost: actualCost.trim(),
          });
        });
      }
      container.append(card);
    });
  }

  function fillMaintenanceBuses(buses) {
    const select = byId("maintenance-bus");
    select.replaceChildren();
    const available = buses.filter((bus) => ["AVAILABLE", "OFFLINE"].includes(bus.status));
    if (!available.length) {
      select.add(new Option("Aucun bus disponible", ""));
      return;
    }
    select.add(new Option("Choisir un bus", ""));
    available.forEach((bus) => {
      select.add(new Option(`${bus.registration} · ${bus.status}`, String(bus.id)));
    });
  }

  async function load() {
    const result = await api("/auth/me/");
    role = result.role;
    canManageSales = ["SUPER_ADMIN", "ADMIN", "FLEET_MANAGER", "SALES_AGENT"].includes(role);
    canManageMaintenance = ["SUPER_ADMIN", "ADMIN", "FLEET_MANAGER", "MAINTENANCE_MANAGER"].includes(role);
    if (!canManageSales && !canManageMaintenance) {
      throw new Error("Ce compte n'a pas de rôle de gestionnaire pour cet espace.");
    }

    byId("office-login").classList.add("hidden");
    byId("office-content").classList.remove("hidden");
    byId("sales-section").classList.toggle("hidden", !canManageSales);
    byId("payments-section").classList.toggle("hidden", !canManageSales);
    byId("maintenance-section").classList.toggle("hidden", !canManageMaintenance);

    const requests = [];
    if (canManageSales) {
      requests.push(api("/sales/orders/?page_size=100"), api("/payments/attempts/?page_size=100"));
    }
    if (canManageMaintenance) {
      requests.push(
        api("/maintenance/orders/?page_size=100"),
        api("/fleet/buses/?page_size=100"),
      );
    }
    const data = await Promise.all(requests);
    let index = 0;
    if (canManageSales) {
      renderSales(rows(data[index++]));
      renderPayments(rows(data[index++]));
    }
    if (canManageMaintenance) {
      renderMaintenance(rows(data[index++]));
      fillMaintenanceBuses(rows(data[index++]));
    }
    notify(`Connecté · ${role.replaceAll("_", " ")}`);
  }

  byId("office-login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const credentials = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      const session = await api("/auth/login/", {
        method: "POST",
        body: JSON.stringify(credentials),
      });
      token = session.token;
      sessionStorage.setItem(tokenKey, token);
      await load();
    } catch (error) {
      notify(error.message, true);
    }
  });

  byId("maintenance-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());
    values.bus = Number(values.bus);
    values.odometer_km = values.odometer_km ? Number(values.odometer_km) : null;
    values.estimated_cost = values.estimated_cost || null;
    try {
      await api("/maintenance/orders/", {
        method: "POST",
        body: JSON.stringify(values),
      });
      form.reset();
      notify("Ordre de maintenance créé.");
      await load();
    } catch (error) {
      notify(error.message, true);
    }
  });

  if (token) {
    load().catch((error) => {
      token = "";
      sessionStorage.removeItem(tokenKey);
      byId("office-login").classList.remove("hidden");
      byId("office-content").classList.add("hidden");
      notify(error.message, true);
    });
  }
})();
