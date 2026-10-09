<?php
declare(strict_types=1);
?><!doctype html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="theme-color" content="#101b2b">
    <title>SmartBus — Fleet operations</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="/assets/app.css">
    <link rel="stylesheet" href="/assets/mobile.css">
    <script defer src="/assets/app.js"></script>
</head>
<body>
    <div class="app-shell">
        <aside class="sidebar">
            <a class="brand" href="#" aria-label="SmartBus accueil">
                <span class="brand-mark">S</span><span>smart<span class="brand-accent">bus</span></span>
            </a>
            <div class="workspace-label">OPERATIONS</div>
            <nav class="navigation" aria-label="Navigation principale">
                <a class="nav-item active" href="#overview"><span class="nav-icon">◫</span>Vue d'ensemble</a>
                <a class="nav-item" href="#fleet"><span class="nav-icon">▣</span>Flotte</a>
                <a class="nav-item" href="#tracking"><span class="nav-icon">⌖</span>Suivi GPS</a>
                <a class="nav-item" href="#bookings"><span class="nav-icon">▤</span>Réservations</a>
                <a class="nav-item" href="/services.php"><span class="nav-icon">◉</span>Achats & paiements</a>
                <a class="nav-item" href="/office.php"><span class="nav-icon">⚙</span>Gestion agence</a>
            </nav>
            <div class="sidebar-bottom">
                <div class="online-indicator"><span></span><span id="sidebar-api-status">Vérification API</span></div>
                <div class="user-card">
                    <div class="avatar">SB</div>
                    <div><strong id="user-name">Visiteur</strong><small id="user-role">Espace public</small></div>
                </div>
            </div>
        </aside>

        <main class="main-content" id="overview">
            <header class="topbar">
                <div class="breadcrumb">SmartBus <span>/</span> <strong>Vue d'ensemble</strong></div>
                <div class="topbar-actions">
                    <span class="live-pill" id="api-status"><i></i>Vérification API</span>
                    <button class="button button-quiet" id="auth-open" type="button">Connexion</button>
                    <button class="button button-primary" id="register-open" type="button">Créer un compte <span>↗</span></button>
                    <button class="button button-quiet hidden" id="logout-button" type="button">Déconnexion</button>
                </div>
            </header>

            <section class="welcome">
                <div>
                    <p class="eyebrow">CENTRE DE CONTRÔLE</p>
                    <h1>La mobilité, <span>sous contrôle.</span></h1>
                    <p class="welcome-copy">Une vue claire de votre flotte, de ses positions et de ses réservations.</p>
                </div>
                <div class="welcome-date"><span class="pulse"></span>Plateforme prête</div>
            </section>

            <section class="stats-grid" aria-label="Statistiques de flotte">
                <article class="stat-card">
                    <div class="stat-top"><span>Bus enregistrés</span><span class="stat-icon blue">▣</span></div>
                    <strong id="stat-total">—</strong><small>Véhicules dans la flotte</small>
                </article>
                <article class="stat-card">
                    <div class="stat-top"><span>Disponibles</span><span class="stat-icon green">✓</span></div>
                    <strong id="stat-available">—</strong><small>Prêts à être réservés</small>
                </article>
                <article class="stat-card">
                    <div class="stat-top"><span>En service</span><span class="stat-icon amber">⌖</span></div>
                    <strong id="stat-service">—</strong><small>Actuellement sur la route</small>
                </article>
                <article class="stat-card">
                    <div class="stat-top"><span>Réservations</span><span class="stat-icon violet">▤</span></div>
                    <strong id="stat-bookings">—</strong><small id="booking-caption">Connectez-vous pour voir les vôtres</small>
                </article>
            </section>

            <section class="content-grid">
                <article class="panel map-panel" id="tracking">
                    <div class="panel-heading">
                        <div><p class="eyebrow">LOCALISATION</p><h2>Positions récentes</h2></div>
                        <span class="live-label"><i></i>GPS</span>
                    </div>
                    <div class="map-stage" id="map-stage">
                        <div class="map-grid"></div>
                        <div class="map-empty" id="map-empty">
                            <span class="map-target">⌖</span>
                            <strong>Aucune position GPS reçue</strong>
                            <p>Les positions apparaîtront ici lorsqu'un tracker publiera des données.</p>
                        </div>
                        <div class="map-pins" id="map-pins"></div>
                        <div class="map-legend"><span><i class="legend-dot green-dot"></i>En ligne</span><span><i class="legend-dot gray-dot"></i>Sans signal</span></div>
                        <span class="map-coordinate">VUE RELATIVE · POSITIONS GPS (SANS FOND CARTOGRAPHIQUE)</span>
                    </div>
                </article>

                <article class="panel fleet-panel" id="fleet">
                    <div class="panel-heading">
                        <div><p class="eyebrow">VÉHICULES</p><h2>Votre flotte</h2></div>
                        <span class="count-badge" id="fleet-count">0</span>
                    </div>
                    <div class="fleet-list" id="fleet-list">
                        <div class="skeleton-row"></div><div class="skeleton-row"></div><div class="skeleton-row"></div>
                    </div>
                    <div class="empty-state hidden" id="fleet-empty">
                        <div class="empty-icon">▣</div><strong>La flotte est vide</strong>
                        <p>Ajoutez un véhicule depuis l'administration Django ou l'API.</p>
                    </div>
                </article>
            </section>

            <section class="panel bookings-panel" id="bookings">
                <div class="panel-heading">
                    <div><p class="eyebrow">ACTIVITÉ</p><h2>Réserver un bus</h2></div>
                    <span class="secure-note">Réservation sécurisée</span>
                </div>
                <form id="booking-form" class="booking-form">
                    <label>Bus<select name="bus" id="booking-bus" required><option value="">Choisir un bus disponible</option></select></label>
                    <label>Départ<input name="start_date" type="date" required></label>
                    <label>Retour<input name="end_date" type="date" required></label>
                    <label>Destination<input name="destination" maxlength="180" placeholder="Ex. Centre-ville" required></label>
                    <label>Passagers<input name="passengers" type="number" min="1" value="1" required></label>
                    <button class="button button-primary booking-submit" type="submit">Demander une réservation <span>→</span></button>
                </form>
                <p class="form-message" id="booking-message" role="status"></p>
                <div class="booking-list" id="booking-list"></div>
            </section>

            <footer class="page-footer"><span>SMARTBUS <span class="footer-dot">•</span> FLEET OPERATIONS</span><span>Créé par Nathan Zoua · NZ</span></footer>
        </main>
    </div>

    <dialog class="auth-dialog" id="auth-dialog">
        <form method="dialog" class="dialog-close-row"><button class="icon-button" aria-label="Fermer">×</button></form>
        <p class="eyebrow" id="auth-eyebrow">ACCÈS SÉCURISÉ</p>
        <h2 id="auth-title">Bienvenue</h2>
        <p class="dialog-copy" id="auth-description">Connectez-vous pour gérer vos réservations.</p>
        <form id="auth-form" class="auth-form">
            <label>Nom d'utilisateur<input name="username" autocomplete="username" required></label>
            <label id="email-field" class="hidden">Adresse e-mail<input name="email" type="email" autocomplete="email"></label>
            <label>Mot de passe<input name="password" type="password" autocomplete="current-password" minlength="10" required></label>
            <label id="confirm-field" class="hidden">Confirmer le mot de passe<input name="password_confirm" type="password" minlength="10"></label>
            <button class="button button-primary" id="auth-submit" type="submit">Se connecter</button>
        </form>
        <button id="auth-mode-toggle" class="text-button" type="button">Créer un compte client</button>
        <p class="form-message" id="auth-message" role="status"></p>
    </dialog>
    <div class="toast" id="toast" role="status"></div>
</body>
</html>
