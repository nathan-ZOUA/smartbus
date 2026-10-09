<?php
declare(strict_types=1);
?><!doctype html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <meta name="theme-color" content="#101b2b">
    <title>SmartBus — Achats et paiements</title>
    <link rel="stylesheet" href="/assets/app.css">
    <link rel="stylesheet" href="/assets/mobile.css">
    <link rel="stylesheet" href="/assets/portal.css">
    <script defer src="/assets/services.js"></script>
</head>
<body class="portal-page" data-page="services">
    <main class="portal-shell">
        <header class="portal-header">
            <a class="brand" href="/"><span class="brand-mark">S</span><span>smart<span class="brand-accent">bus</span></span></a>
            <nav aria-label="Navigation du compte"><a href="/">Accueil</a><a href="/driver.php">Partage GPS</a><a href="/office.php">Gestion agence</a></nav>
        </header>
        <section class="portal-intro">
            <p class="eyebrow">ESPACE CLIENT</p>
            <h1>Achats et paiements</h1>
            <p>Demande l'achat d'un véhicule, règle ta réservation ou consulte ton dossier.</p>
        </section>
        <section id="portal-login" class="portal-panel">
            <h2>Connecte-toi à ton compte client</h2>
            <p>Le suivi de tes réservations et de tes paiements est privé.</p>
            <form id="portal-login-form" class="portal-form">
                <label>Identifiant<input name="username" autocomplete="username" required></label>
                <label>Mot de passe<input name="password" type="password" autocomplete="current-password" required></label>
                <button class="button button-primary" type="submit">Se connecter</button>
            </form>
        </section>
        <p id="portal-message" class="portal-message" role="status"></p>
        <div id="services-content" class="portal-columns hidden">
            <section class="portal-panel">
                <div class="portal-heading"><h2>Véhicules proposés à la vente</h2><span class="portal-currency">Prix en XAF</span></div>
                <div id="sale-inventory" class="portal-list"></div>
            </section>
            <section class="portal-panel">
                <h2>Mes réservations</h2>
                <div id="customer-bookings" class="portal-list"></div>
            </section>
            <section class="portal-panel">
                <h2>Mes demandes d'achat</h2>
                <div id="customer-sales" class="portal-list"></div>
            </section>
            <section class="portal-panel">
                <h2>Mes références Orange Money</h2>
                <div id="customer-payments" class="portal-list"></div>
            </section>
        </div>
        <footer class="portal-footer">Créé par Nathan Zoua · NZ</footer>
    </main>

    <dialog id="payment-dialog" class="portal-dialog">
        <form id="payment-form" class="portal-form">
            <button class="portal-dialog-close" type="button" id="payment-close" aria-label="Fermer">×</button>
            <p class="eyebrow">ORANGE MONEY · XAF</p>
            <h2>Déclarer un paiement</h2>
            <p id="payment-instructions" class="portal-instructions"></p>
            <p id="payment-amount" class="portal-amount"></p>
            <input id="payment-order-id" type="hidden">
            <input id="payment-order-type" type="hidden">
            <label>Référence de la transaction<input id="payment-reference" required maxlength="100" autocomplete="off"></label>
            <label>Numéro ayant envoyé le paiement (facultatif)<input id="payment-phone" maxlength="30" autocomplete="tel"></label>
            <p class="portal-disclaimer">Après ton transfert Orange Money, indique sa référence. SmartBus ne débite pas ton compte; le gestionnaire vérifie puis confirme manuellement le paiement.</p>
            <button class="button button-primary" type="submit">Envoyer la référence</button>
        </form>
    </dialog>
</body>
</html>
