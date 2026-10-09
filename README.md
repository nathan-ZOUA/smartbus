# SmartBus

MVP de gestion de flotte, réservation, ventes et suivi GPS web : API Django REST, base MySQL et interface PHP responsive.
Le projet est conçu pour être lancé et testé localement. Il n'est pas encore un produit complet de production.
Créé par **Nathan Zoua (NZ)**.

## Fonctionnalités disponibles

- inscription client, connexion, déconnexion et profil API ;
- rôles de compte et contrôle d'accès aux modifications de flotte ;
- gestion des bus et conducteurs via l'API et l'administration Django ;
- consultation paginée/recherchable de la flotte ;
- réception et historique des positions GPS, avec endpoint des dernières positions ;
- page conducteur mobile pour partager la géolocalisation après autorisation explicite ;
- demande de réservation, contrôle du chevauchement des dates, calcul serveur du prix et annulation des réservations en attente ;
- demandes d'achat de bus en vente avec validation commerciale ;
- déclarations de paiement Orange Money en XAF avec vérification humaine et historique ;
- ordres de maintenance avec approbation, suivi des coûts, kilométrage et disponibilité du bus ;
- PDF récapitulatifs de location ou de vente après paiement confirmé (brouillons non signés) ;
- tableau de bord agrégé et health check MySQL ;
- interface PHP avec aperçu de flotte, positions, authentification et formulaire de réservation ;
- commande explicite de données de démonstration, toutes identifiées `is_demo`.

Les alertes e-mail, Channels/WebSockets, Celery et l'intégration réelle des appareils GPS ne sont pas encore implémentés. Aucun chiffre de charge simultanée n'est revendiqué. Orange Money n'est pas prélevé automatiquement : chaque référence doit être vérifiée par un gestionnaire. Les contrats générés sont des brouillons à faire vérifier juridiquement au Cameroun; ils ne sont pas signés électroniquement.

Le suivi GPS sur téléphone se fait actuellement avec la page web conducteur `/driver.php` (HTTPS requis, page à laisser ouverte). Le prototype Flutter n'est pas compilé et n'est pas nécessaire pour ce pilote; il est documenté dans [mobile/smartbus_driver/README.md](mobile/smartbus_driver/README.md). Le prototype Android Kotlin antérieur est conservé dans [android/driver-app/README.md](android/driver-app/README.md).

## Prérequis

- Python 3.12+ (poste développé/testé en Python 3.14)
- MySQL 8 ou MariaDB démarré
- PHP 8+ pour servir l'interface
- Node.js (facultatif; utilisé pour vérifier la syntaxe JavaScript)

## Installation Windows PowerShell

À exécuter depuis le dossier racine `SmartBus` :

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
Copy-Item .env.example .env
```

Configure `.env` avec des secrets générés et un compte MySQL dédié, puis crée la base avec le jeu de caractères `utf8mb4`. L'utilisateur applicatif ne doit pas être administrateur MySQL.

Pour activer le formulaire Orange Money, configure aussi `ORANGE_MONEY_RECEIVER_NAME` et `ORANGE_MONEY_RECEIVER_NUMBER` avec le numéro de destination contrôlé par l'agence. Le numéro est rendu visible aux clients sur la page de paiement. Ne partage pas les secrets d'accès personnels et ne place pas de code PIN Orange Money dans l'application.

Pour personnaliser les projets de contrat, configure `SMARTBUS_LEGAL_NAME`, `SMARTBUS_LEGAL_ADDRESS`, `SMARTBUS_LEGAL_PHONE` et `SMARTBUS_LEGAL_REGISTRATION`. Les champs manquants restent explicitement à compléter dans le PDF.

Dans MySQL/phpMyAdmin, crée la base et un compte dédié (remplace le mot de passe d'exemple par celui de `.env`) :

```sql
CREATE DATABASE smartbus CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'smartbus_app'@'localhost' IDENTIFIED BY 'replace-with-the-value-from-env';
GRANT ALL PRIVILEGES ON smartbus.* TO 'smartbus_app'@'localhost';
FLUSH PRIVILEGES;
```

Pour générer une clé secrète Django :

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Initialise la base et crée un administrateur Django :

```powershell
python backend\manage.py migrate
python backend\manage.py createsuperuser
```

Lance Django :

```powershell
python backend\manage.py runserver
```

Dans un deuxième terminal, démarre l'interface PHP :

```powershell
& 'C:\wamp64\bin\php\php8.4.15\php.exe' -S 127.0.0.1:8080 -t frontend\public frontend\router.php
```

Le routeur PHP de développement relaie `/api/` vers Django pour que le navigateur reste sur la même origine. En production, configure le reverse proxy de l'hébergeur pour exposer frontend et API sous la même origine; le serveur PHP intégré ne doit pas être utilisé en production.

Pages utiles :

- interface : `http://127.0.0.1:8080`
- partage GPS conducteur : `http://127.0.0.1:8080/driver.php` (la géolocalisation exige HTTPS ou localhost)
- API : `http://127.0.0.1:8000/api/`
- administration : `http://127.0.0.1:8000/admin/`
- disponibilité : `http://127.0.0.1:8000/api/health/`

## Données de démonstration facultatives

Cette commande ajoute deux véhicules et une position fictive, explicitement marqués `Demo Data` :

```powershell
python backend\manage.py seed_demo
```

Ne lance pas cette commande sur une base de production. Elle n'est pas exécutée automatiquement.

## Essayer le GPS avec un téléphone

1. Connecte-toi à l'administration Django avec un compte gestionnaire et crée une fiche `Driver` ainsi qu'un `Bus` affecté à cette fiche.
2. Crée le compte utilisateur du conducteur et son `UserProfile`; choisis le rôle `DRIVER` et lie la fiche Driver créée.
3. Ouvre `/driver.php`, connecte-toi avec ce compte, puis appuie sur **Démarrer le partage GPS** et autorise la localisation.
4. Vérifie avec un compte gestionnaire les dernières positions sur `/api/tracking/positions/latest/`.

Sur le téléphone, ouvre `/driver.php` avec Chrome (Android) ou Safari (iPhone), autorise la localisation précise et garde la page ouverte au premier plan pendant le trajet. Le navigateur envoie la position au maximum toutes les 10 secondes, uniquement après action explicite du conducteur. Arrêter ou fermer la page stoppe le partage; verrouiller l'écran ou passer dans une autre application peut aussi le suspendre. Le navigateur doit être sur HTTPS (ou `localhost` sur le même appareil); l'URL locale en HTTP ne permet pas de tester la géolocalisation depuis un vrai téléphone. Pour cela, déploie d'abord un environnement de staging HTTPS et utilise son adresse sur le téléphone. Le serveur PHP intégré ne doit jamais être exposé sur Internet.

Pour passer de 1 à 10 téléphones, crée un compte conducteur distinct, une fiche Driver et une affectation de bus par téléphone. N'utilise pas un identifiant partagé. La page conducteur du site fonctionne sur téléphone sous HTTPS et envoie la dernière position GPS pendant que la page reste ouverte. Si elle passe en arrière-plan ou si l'écran est verrouillé, le navigateur peut suspendre le partage : cette version ne garantit donc pas un suivi continu dans ces conditions. Une application mobile native pourra être préparée séparément pour ce besoin.

## Tests et vérifications

```powershell
python backend\manage.py check
python backend\manage.py makemigrations --check --dry-run
python backend\manage.py test apps.authentication apps.fleet apps.tracking apps.bookings apps.users apps.core --settings=config.test_settings
node --check frontend\public\assets\app.js
node --check frontend\public\assets\driver.js
node --test frontend\tests\driver.test.js
```

Les tests automatiques utilisent une base SQLite temporaire isolée pour ne pas détruire ou altérer la base MySQL de développement. Les migrations MySQL doivent aussi être exécutées et vérifiées sur un environnement dédié avant chaque déploiement.

## Structure

```text
backend/
  apps/
    authentication/  # inscription, tokens expirables et rôles
    bookings/        # demandes et disponibilité des bus
    core/            # dashboard, API root et health check
    fleet/           # bus et conducteurs
    tracking/        # historique GPS et dernières positions
    users/            # profils et rôles
  config/             # settings, URL, ASGI/WSGI, test settings
frontend/public/      # point d'entrée PHP et CSS/JavaScript
docs/                 # architecture, API, base, sécurité, déploiement
```

## Déploiement

Voir [docs/deployment.md](docs/deployment.md). Il faudra notamment un hébergement PHP, un service Django ASGI/WSGI, MySQL géré, HTTPS, des variables d'environnement distinctes et des sauvegardes. L'environnement local actuel n'est pas un déploiement de production.
Voir aussi [android/driver-app/README.md](android/driver-app/README.md) pour compiler et installer l'application conducteur sur les téléphones.
Voir [mobile/smartbus_driver/README.md](mobile/smartbus_driver/README.md) pour le client Android/iOS et sa compilation.

### Aperçu statique gratuit sur Vercel

Le dépôt contient une cible Vercel statique qui transforme les pages PHP de présentation en fichiers HTML et affiche uniquement du contenu fictif. Elle ne publie ni le backend Django, ni MySQL, ni les fichiers `.env`; connexion, réservations, paiements et GPS y sont désactivés. N'y saisis aucune donnée réelle.

1. Importe le dépôt dans Vercel et choisis le dossier `SmartBus` comme racine du projet.
2. Garde la configuration du projet : commande `node scripts/build-vercel-preview.mjs`, dossier de sortie `dist`, sans variables d'environnement à ajouter.
3. Lance le déploiement. L'adresse gratuite `*.vercel.app` suffit pour partager cet aperçu.

Pour vérifier le rendu avant l'import :

```powershell
node scripts/build-vercel-preview.mjs
node --test frontend/tests/vercel-preview.test.mjs
```

Cette cible n'est pas un déploiement fonctionnel ni un staging : pour activer les comptes, les paiements, les réservations ou le suivi GPS, il faudra héberger aussi le backend Django et une base MySQL persistante.

## Sécurité et limites

- `.env` est ignoré par Git; ne publie jamais ses valeurs.
- Le token API a une durée de vie configurable (12 heures par défaut).
- Chaque profil conducteur doit être lié à une fiche conducteur et à son bus dans l'administration. Il ne peut envoyer que les positions de son bus.
- Le téléphone envoie au maximum une position toutes les 10 secondes; le serveur limite aussi les rapports GPS à 30 par minute et par utilisateur.
- Les écritures de flotte sont réservées aux rôles d'administration correspondants.
- Les réservations sont limitées à l'utilisateur connecté, avec validation serveur.
- Active HTTPS et les réglages de cookies sécurisés en production.
- Un test de charge réel est requis avant toute déclaration de capacité.
