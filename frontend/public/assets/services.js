(() => {
  "use strict";

  const tokenKey = "smartbus_token";
  const byId = (id) => document.getElementById(id);
  let token = sessionStorage.getItem(tokenKey) || "";
  let paymentInstructions;

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
    const element = byId("portal-message");
    element.textContent = text;
    element.classList.toggle("error", error);
  }

  function paginated(payload) {
    return Array.isArray(payload) ? payload : payload.results || [];
  }

  function makeCard(title, detail, status, note = "") {
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
    const description = document.createElement("p");
    description.textContent = detail;
    card.append(description);
    if (note) {
      const help = document.createElement("small");
      help.textContent = note;
      card.append(help);
    }
    return card;
  }

  function actionsFor(card) {
    const actions = document.createElement("div");
    actions.className = "portal-actions";
    card.append(actions);
    return actions;
  }

  function addButton(container, label, onClick, quiet = false) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `button ${quiet ? "button-quiet" : "button-primary"}`;
    button.textContent = label;
    button.addEventListener("click", onClick);
    container.append(button);
    return button;
  }

  function empty(container, text) {
    const item = document.createElement("p");
    item.className = "portal-empty";
    item.textContent = text;
    container.replaceChildren(item);
  }

  function statusLabel(status) {
    return {
      REQUESTED: "À confirmer",
      APPROVED: "Approuvée",
      PENDING: "À vérifier",
      VERIFIED: "Confirmé",
      REJECTED: "Refusé",
      PAID: "Payée",
      COMPLETED: "Terminée",
      CANCELLED: "Annulée",
      CONFIRMED: "Confirmée",
    }[status] || status;
  }

  function money(value) {
    return `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(Number(value))} XAF`;
  }

  function canSubmitPayment() {
    return Boolean(paymentInstructions && paymentInstructions.available);
  }

  function showPaymentDialog(kind, item) {
    if (!canSubmitPayment()) {
      notify("Le gestionnaire doit d'abord configurer le numéro Orange Money de l'agence.", true);
      return;
    }
    byId("payment-order-id").value = String(item.id);
    byId("payment-order-type").value = kind;
    byId("payment-reference").value = "";
    byId("payment-phone").value = "";
    const receiver = paymentInstructions.receiver_number;
    const name = paymentInstructions.receiver_name;
    byId("payment-instructions").textContent = `Envoie le montant exact depuis Orange Money au numéro ${receiver}${name ? ` au nom de ${name}` : ""}. Garde la référence de transaction.`;
    byId("payment-amount").textContent = money(kind === "booking" ? item.total_price : item.amount);
    byId("payment-dialog").showModal();
  }

  function renderInventory(buses, orders) {
    const container = byId("sale-inventory");
    const activeBusIds = new Set(
      orders.filter((order) => ["REQUESTED", "APPROVED", "PAID"].includes(order.status))
        .map((order) => order.bus),
    );
    const available = buses.filter((bus) => bus.status === "FOR_SALE" && Number(bus.sale_price) > 0);
    container.replaceChildren();
    if (!available.length) {
      empty(container, "Aucun véhicule n'est actuellement proposé à la vente.");
      return;
    }
    available.forEach((bus) => {
      const card = makeCard(
        `${bus.make} ${bus.model} · ${bus.year}`,
        `${bus.registration} · ${bus.seats} places · ${money(bus.sale_price)}`,
        "FOR_SALE",
      );
      const action = actionsFor(card);
      if (activeBusIds.has(bus.id)) {
        const note = document.createElement("small");
        note.textContent = "Ta demande ou ta vente pour ce véhicule est déjà enregistrée.";
        action.append(note);
      } else {
        addButton(action, "Demander l'achat", async () => {
          try {
            await api("/sales/orders/", {
              method: "POST",
              body: JSON.stringify({ bus: bus.id }),
            });
            notify("Demande d'achat envoyée; elle sera vérifiée par l'agence.");
            await load();
          } catch (error) {
            notify(error.message, true);
          }
        });
      }
      container.append(card);
    });
  }

  async function downloadContract(path) {
    const response = await fetch(`/api${path}`, {
      headers: { Authorization: `Token ${token}`, Accept: "application/pdf" },
      credentials: "same-origin",
    });
    if (!response.ok) {
      throw new ApiError(`Contrat indisponible (HTTP ${response.status}).`, response.status);
    }
    const file = await response.blob();
    const url = URL.createObjectURL(file);
    const link = document.createElement("a");
    link.href = url;
    link.download = "smartbus-contrat-brouillon.pdf";
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function renderBookings(bookings) {
    const container = byId("customer-bookings");
    container.replaceChildren();
    if (!bookings.length) {
      empty(container, "Aucune réservation dans ton compte.");
      return;
    }
    bookings.forEach((booking) => {
      const card = makeCard(
        `${booking.bus_registration} · RES-${booking.id}`,
        `${booking.start_date} → ${booking.end_date} · ${booking.destination} · ${money(booking.total_price)}`,
        booking.status,
      );
      const actions = actionsFor(card);
      if (["PENDING", "CONFIRMED"].includes(booking.status)) {
        addButton(actions, "Déclarer un paiement", () => showPaymentDialog("booking", booking));
      }
      if (["PAID", "COMPLETED"].includes(booking.status)) {
        addButton(actions, "Télécharger le contrat PDF", async () => {
          try {
            await downloadContract(`/contracts/bookings/${booking.id}/pdf/`);
          } catch (error) {
            notify(error.message, true);
          }
        }, true);
      }
      container.append(card);
    });
  }

  function renderSales(orders) {
    const container = byId("customer-sales");
    container.replaceChildren();
    if (!orders.length) {
      empty(container, "Aucune demande d'achat enregistrée.");
      return;
    }
    orders.forEach((order) => {
      const card = makeCard(
        `${order.bus_registration} · VTE-${order.id}`,
        `${order.bus_make} ${order.bus_model} · ${money(order.amount)}`,
        order.status,
      );
      const actions = actionsFor(card);
      if (order.status === "APPROVED") {
        addButton(actions, "Déclarer un paiement", () => showPaymentDialog("sale_order", order));
      } else if (order.status === "PAID") {
        addButton(actions, "Télécharger le contrat PDF", async () => {
          try {
            await downloadContract(`/contracts/sales/${order.id}/pdf/`);
          } catch (error) {
            notify(error.message, true);
          }
        }, true);
      } else if (["REQUESTED", "APPROVED"].includes(order.status)) {
        addButton(actions, "Annuler la demande", async () => {
          try {
            await api(`/sales/orders/${order.id}/cancel/`, { method: "POST" });
            notify("Demande d'achat annulée.");
            await load();
          } catch (error) {
            notify(error.message, true);
          }
        }, true);
      }
      container.append(card);
    });
  }

  function renderPayments(payments) {
    const container = byId("customer-payments");
    container.replaceChildren();
    if (!payments.length) {
      empty(container, "Aucune référence de paiement déclarée.");
      return;
    }
    payments.forEach((payment) => {
      const card = makeCard(
        `${payment.order_reference} · ${payment.channel.replaceAll("_", " ")}`,
        `${money(payment.amount)} · Référence ${payment.transaction_reference}`,
        payment.status,
        payment.review_note || "",
      );
      container.append(card);
    });
  }

  async function load() {
    paymentInstructions = await api("/payments/instructions/");
    const [busData, bookingsData, salesData, paymentData] = await Promise.all([
      api("/fleet/buses/?page_size=100"),
      api("/bookings/?page_size=100"),
      api("/sales/orders/?page_size=100"),
      api("/payments/attempts/?page_size=100"),
    ]);
    const buses = paginated(busData);
    const bookings = paginated(bookingsData);
    const orders = paginated(salesData);
    renderInventory(buses, orders);
    renderBookings(bookings);
    renderSales(orders);
    renderPayments(paginated(paymentData));
    byId("portal-login").classList.add("hidden");
    byId("services-content").classList.remove("hidden");
    notify(canSubmitPayment()
      ? "Paiements déclaratifs Orange Money disponibles. La confirmation est manuelle."
      : "Avant les paiements, l'agence doit configurer son numéro Orange Money.");
  }

  byId("portal-login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(event.currentTarget).entries());
    try {
      const result = await api("/auth/login/", {
        method: "POST",
        body: JSON.stringify(values),
      });
      token = result.token;
      sessionStorage.setItem(tokenKey, token);
      await load();
    } catch (error) {
      notify(error.message, true);
    }
  });

  byId("payment-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const kind = byId("payment-order-type").value;
    const payload = {
      transaction_reference: byId("payment-reference").value.trim(),
      sender_phone: byId("payment-phone").value.trim(),
      [kind === "booking" ? "booking_id" : "sale_order_id"]: Number(byId("payment-order-id").value),
    };
    try {
      await api("/payments/attempts/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      byId("payment-dialog").close();
      notify("Référence reçue. Le paiement restera en attente jusqu'à vérification de l'agence.");
      await load();
    } catch (error) {
      notify(error.message, true);
    }
  });

  byId("payment-close").addEventListener("click", () => byId("payment-dialog").close());
  byId("payment-dialog").addEventListener("click", (event) => {
    if (event.target === byId("payment-dialog")) byId("payment-dialog").close();
  });

  if (token) {
    load().catch(async (error) => {
      token = "";
      sessionStorage.removeItem(tokenKey);
      byId("portal-login").classList.remove("hidden");
      byId("services-content").classList.add("hidden");
      notify(error.message, true);
    });
  }
})();
