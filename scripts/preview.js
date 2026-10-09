(() => {
  "use strict";

  const noticeText = "Aperçu seulement : aucune donnée n'est envoyée ni enregistrée.";
  const buses = [
    { id: "DEMO-SB-001", make: "Demo Motors", model: "City 40", seats: 40, status: "En service", rate: 320 },
    { id: "DEMO-SB-002", make: "Demo Motors", model: "Tour 52", seats: 52, status: "Disponible", rate: 450 },
  ];

  function byId(id) {
    return document.getElementById(id);
  }

  function notice(text = noticeText) {
    const message = document.createElement("p");
    message.className = "preview-notice";
    message.setAttribute("role", "status");
    message.textContent = text;
    return message;
  }

  function card(title, details, status, note = "Exemple fictif — aperçu de démonstration.") {
    const article = document.createElement("article");
    article.className = "portal-card";
    const header = document.createElement("div");
    header.className = "portal-card-header";
    const heading = document.createElement("strong");
    heading.textContent = title;
    header.append(heading);
    if (status) {
      const badge = document.createElement("span");
      badge.className = `portal-status ${status.toLowerCase()}`;
      badge.textContent = status;
      header.append(badge);
    }
    article.append(header);
    for (const detail of details) {
      const paragraph = document.createElement("p");
      paragraph.textContent = detail;
      article.append(paragraph);
    }
    if (note) {
      const small = document.createElement("small");
      small.textContent = note;
      article.append(small);
    }
    return article;
  }

  function renderHome() {
    const sidebarStatus = byId("sidebar-api-status");
    const apiStatus = byId("api-status");
    if (sidebarStatus) sidebarStatus.textContent = "Aperçu statique";
    if (apiStatus) apiStatus.textContent = "Mode démo";
    const welcomeState = document.querySelector(".welcome-date");
    if (welcomeState) welcomeState.textContent = "Aperçu visuel";
    if (byId("stat-total")) byId("stat-total").textContent = "2";
    if (byId("stat-available")) byId("stat-available").textContent = "1";
    if (byId("stat-service")) byId("stat-service").textContent = "1";
    if (byId("stat-bookings")) byId("stat-bookings").textContent = "—";
    if (byId("booking-caption")) byId("booking-caption").textContent = "Aucune donnée connectée";
    if (byId("fleet-count")) byId("fleet-count").textContent = "2";

    const fleet = byId("fleet-list");
    if (fleet) {
      fleet.replaceChildren();
      buses.forEach((bus) => {
        const row = document.createElement("div");
        row.className = "fleet-row";
        const icon = document.createElement("span");
        icon.className = "bus-avatar";
        icon.textContent = "▣";
        const name = document.createElement("div");
        name.className = "fleet-name";
        const title = document.createElement("strong");
        title.textContent = bus.id;
        const subtitle = document.createElement("small");
        subtitle.textContent = `${bus.make} ${bus.model} · ${bus.seats} places · DONNÉES DÉMO`;
        name.append(title, subtitle);
        const status = document.createElement("span");
        status.className = `status-badge${bus.status === "Disponible" ? "" : " offline"}`;
        status.textContent = bus.status;
        row.append(icon, name, status);
        fleet.append(row);
      });
    }

    const mapEmpty = byId("map-empty");
    if (mapEmpty) {
      const title = mapEmpty.querySelector("strong");
      const description = mapEmpty.querySelector("p");
      if (title) title.textContent = "Aucune position GPS dans cet aperçu";
      if (description) description.textContent = "Les positions réelles nécessitent l'API et un compte conducteur.";
    }
    const bookingForm = byId("booking-form");
    if (bookingForm) {
      bookingForm.before(notice("Réservations désactivées dans cet aperçu. Les exemples affichés ne sont pas des véhicules réellement réservables."));
      disableForm(bookingForm);
    }
    ["auth-open", "register-open", "logout-button"].forEach((id) => {
      const button = byId(id);
      if (button) {
        button.disabled = true;
        button.classList.add("preview-disabled");
        button.title = "Connexion indisponible dans l'aperçu statique.";
      }
    });
    const bookingSelect = byId("booking-bus");
    if (bookingSelect) bookingSelect.replaceChildren(new Option("Réservation désactivée en mode démo", ""));
    const authDialog = byId("auth-dialog");
    if (authDialog) authDialog.remove();
  }

  function renderServices() {
    const heading = document.querySelector("#portal-login h2");
    const description = document.querySelector("#portal-login > p");
    if (heading) heading.textContent = "Espace client — aperçu";
    if (description) description.textContent = "Les commandes affichées ci-dessous sont des exemples fictifs.";
    const content = byId("services-content");
    if (content) content.classList.remove("hidden");
    const rows = [
      ["sale-inventory", "DEMO-SB-003 · City 40", ["40 places · Exemple de prix : 18 000 000 XAF"], "À vendre"],
      ["customer-bookings", "Réservation d'exemple", ["Bus DEMO-SB-002 · Yaoundé · 2 jours · 900 XAF"], "Démo"],
      ["customer-sales", "Demande d'achat d'exemple", ["Bus DEMO-SB-003 · Exemple sans valeur commerciale"], "À traiter"],
      ["customer-payments", "Paiement d'exemple", ["Référence fictive : DEMO-0000 · Aucun transfert effectué"], "En attente"],
    ];
    rows.forEach(([containerId, title, details, status]) => {
      const container = byId(containerId);
      if (container) container.replaceChildren(card(title, details, status));
    });
    const message = byId("portal-message");
    if (message) message.textContent = "Toutes les commandes, références et valeurs affichées sont fictives.";
    const dialog = byId("payment-dialog");
    if (dialog) dialog.remove();
  }

  function renderOffice() {
    const heading = document.querySelector("#office-login h2");
    const description = document.querySelector("#office-login > p");
    if (heading) heading.textContent = "Gestion agence — aperçu";
    if (description) description.textContent = "Les commandes affichées ci-dessous sont des exemples fictifs.";
    const content = byId("office-content");
    if (content) content.classList.remove("hidden");
    ["sales-section", "payments-section", "maintenance-section"].forEach((id) => {
      const section = byId(id);
      if (section) section.classList.remove("hidden");
    });
    const demoLists = [
      ["office-sales", "Demande de vente d'exemple", ["Bus DEMO-SB-003 · Montant fictif : 18 000 000 XAF"], "À traiter"],
      ["office-payments", "Référence fictive DEMO-0000", ["Aucun paiement réel reçu — exemple visuel uniquement"], "À vérifier"],
      ["office-maintenance", "Révision périodique d'exemple", ["Bus DEMO-SB-001 · Coût fictif : 75 000 XAF"], "En cours"],
    ];
    demoLists.forEach(([containerId, title, details, status]) => {
      const container = byId(containerId);
      if (container) container.replaceChildren(card(title, details, status));
    });
    const message = byId("office-message");
    if (message) message.textContent = "Aucune commande réelle ne peut être vérifiée ou modifiée ici.";
  }

  function renderDriver() {
    const heading = document.querySelector(".driver-panel h1");
    if (heading) heading.textContent = "GPS conducteur — aperçu";
    const controls = byId("driver-controls");
    if (controls) controls.classList.add("hidden");
    const copy = document.querySelector(".driver-copy");
    if (copy) copy.textContent = "Page de présentation uniquement. Le suivi GPS n'est pas actif sur cet aperçu.";
    const message = byId("driver-message");
    if (message) message.textContent = "GPS désactivé — aucune localisation n'est demandée ni transmise.";
    const security = document.querySelector(".driver-security");
    if (security) security.textContent = "Cette version de démonstration ne demande pas l'accès à la localisation et ne transmet aucune donnée.";
  }

  document.addEventListener("submit", (event) => {
    event.preventDefault();
  });
  document.addEventListener("click", (event) => {
    if (event.target.closest("button:disabled")) event.preventDefault();
  });

  const pathname = window.location.pathname;
  if (pathname.endsWith("/services.html")) renderServices();
  else if (pathname.endsWith("/office.html")) renderOffice();
  else if (pathname.endsWith("/driver.html")) renderDriver();
  else renderHome();
})();
