<?php
declare(strict_types=1);
?><!doctype html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <meta name="theme-color" content="#101b2b">
    <title>SmartBus — Partage GPS conducteur</title>
    <link rel="stylesheet" href="/assets/app.css">
    <link rel="stylesheet" href="/assets/mobile.css">
    <link rel="stylesheet" href="/assets/driver.css">
    <script defer src="/assets/driver.js"></script>
</head>
<body class="driver-page">
    <main class="driver-shell">
        <a class="brand driver-brand" href="/"><span class="brand-mark">S</span><span>smart<span class="brand-accent">bus</span></span></a>
        <section class="driver-panel">
            <p class="eyebrow">MODE CONDUCTEUR · PILOTE</p>
            <h1>Partager ma position</h1>
            <p class="driver-copy">Le partage démarre uniquement après ton action. Garde cette page ouverte pendant le trajet et appuie sur Arrêter à la fin.</p>

            <form id="driver-login" class="driver-form">
                <label>Identifiant<input name="username" autocomplete="username" required></label>
                <label>Mot de passe<input name="password" type="password" autocomplete="current-password" required></label>
                <button class="button button-primary" type="submit">Connexion conducteur</button>
            </form>

            <section id="driver-controls" class="driver-controls hidden">
                <label>Bus affecté<select id="driver-bus" required><option value="">Chargement des bus affectés…</option></select></label>
                <div class="gps-card"><span class="gps-dot" id="gps-dot"></span><div><strong id="gps-state" aria-live="polite">Partage désactivé</strong><small id="gps-detail">La position n'est pas transmise.</small></div></div>
                <div class="driver-actions">
                    <button class="button button-primary" id="start-sharing" type="button">Démarrer le partage GPS</button>
                    <button class="button button-quiet hidden" id="stop-sharing" type="button">Arrêter</button>
                </div>
                <button class="driver-logout" id="driver-logout" type="button">Se déconnecter</button>
            </section>
            <p class="driver-message" id="driver-message" role="status"></p>
            <p class="driver-security">Ton compte ne peut transmettre que la position du bus qui lui est affecté. Internet, HTTPS et l'autorisation de localisation sont nécessaires. En arrière-plan ou écran verrouillé, le navigateur peut suspendre le partage.</p>
        </section>
        <a class="driver-back" href="/">← Retour à SmartBus</a>
    </main>
</body>
</html>
