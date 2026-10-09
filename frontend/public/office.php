<?php
declare(strict_types=1);
?><!doctype html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <meta name="theme-color" content="#101b2b">
    <title>SmartBus — Gestion agence</title>
    <link rel="stylesheet" href="/assets/app.css">
    <link rel="stylesheet" href="/assets/mobile.css">
    <link rel="stylesheet" href="/assets/portal.css">
    <script defer src="/assets/office.js"></script>
</head>
<body class="portal-page" data-page="office">
    <main class="portal-shell">
        <header class="portal-header">
            <a class="brand" href="/"><span class="brand-mark">S</span><span>smart<span class="brand-accent">bus</span></span></a>
            <nav aria-label="Navigation de l'agence"><a href="/">Accueil</a><a href="/services.php">Espace client</a><a href="/driver.php">Partage GPS</a></nav>
        </header>
        <section class="portal-intro">
            <p class="eyebrow">ESPACE AGENCE</p>
            <h1>Gestion des opérations</h1>
            <p>Demandes de vente, vérification des paiements et ordres de maintenance.</p>
        </section>
        <section id="office-login" class="portal-panel">
            <h2>Connexion agence</h2>
            <p>Connecte-toi avec un compte de gestionnaire autorisé.</p>
            <form id="office-login-form" class="portal-form">
                <label>Identifiant<input name="username" autocomplete="username" required></label>
                <label>Mot de passe<input name="password" type="password" autocomplete="current-password" required></label>
                <button class="button button-primary" type="submit">Se connecter</button>
            </form>
        </section>
        <p id="office-message" class="portal-message" role="status"></p>
        <div id="office-content" class="portal-list portal-list-wide hidden">
            <section id="sales-section" class="portal-panel hidden">
                <h2>Demandes de vente</h2>
                <div id="office-sales" class="portal-list"></div>
            </section>
            <section id="payments-section" class="portal-panel hidden">
                <h2>Références Orange Money à vérifier</h2>
                <div id="office-payments" class="portal-list"></div>
            </section>
            <section id="maintenance-section" class="portal-panel hidden">
                <h2>Nouvel ordre de maintenance</h2>
                <form id="maintenance-form" class="portal-form">
                    <label>Bus<select name="bus" id="maintenance-bus" required></select></label>
                    <label>Description des travaux<textarea name="description" rows="3" maxlength="5000" required></textarea></label>
                    <label>Priorité<select name="priority"><option value="NORMAL">Normale</option><option value="LOW">Faible</option><option value="HIGH">Haute</option><option value="URGENT">Urgente</option></select></label>
                    <label>Kilométrage actuel (facultatif)<input name="odometer_km" type="number" min="0" step="1"></label>
                    <label>Coût estimé en XAF (facultatif)<input name="estimated_cost" type="number" min="0" step="1"></label>
                    <button class="button button-primary" type="submit">Créer l'ordre</button>
                </form>
                <h3>Ordres et historique</h3>
                <div id="office-maintenance" class="portal-list"></div>
            </section>
        </div>
        <footer class="portal-footer">Créé par Nathan Zoua · NZ</footer>
    </main>
</body>
</html>
