# Déploiement — préparation, pas encore exécuté

Le code actuel est un MVP local. Aucun hébergement, domaine ou certificat TLS n'a été provisionné. Ne pointe pas un domaine public vers le serveur Django de développement.

## Aperçu statique Vercel (démo seulement)

Le projet configure une cible statique Vercel (`vercel.json`) qui compile les pages PHP existantes en HTML sous `dist/`. Elle embarque uniquement CSS, HTML et un script de présentation avec exemples fictifs; les sources `.env`, le backend, MySQL et les scripts JavaScript de l'application connectée ne font pas partie de la sortie. Connexion, réservations, paiements et GPS y sont désactivés. Ne pas collecter de données personnelles ou de paiements avec cet aperçu.

Importer le dossier `SmartBus` dans Vercel sans modifier la commande de build (`node scripts/build-vercel-preview.mjs`) ni le dossier de sortie (`dist`). Aucun domaine payant ni variable d'environnement ne sont requis pour l'adresse `*.vercel.app`. Cet aperçu n'est pas un staging backend ni une mise en production; le reste du guide concerne un futur déploiement complet.

Le navigateur conducteur utilise la géolocalisation web, disponible uniquement dans un contexte sécurisé : HTTPS en staging/production (ou `localhost` sur le même appareil pendant le développement). Une URL LAN en HTTP n'est pas suffisante pour un test GPS sur téléphone.

La page GPS conducteur doit être servie sur la même origine HTTPS que l'API pour accéder à la géolocalisation sur téléphone. N'expose pas le serveur Django de développement à Internet. Chaque chauffeur utilise un compte individuel de rôle `DRIVER` lié à sa fiche conducteur et à un bus autorisé.

Les paiements Orange Money du pilote sont déclaratifs : le client saisit une référence après avoir envoyé le montant à `ORANGE_MONEY_RECEIVER_NUMBER`, puis un gestionnaire vérifie le compte Orange Money et confirme ou refuse la déclaration dans SmartBus. Il faut configurer `ORANGE_MONEY_RECEIVER_NAME` et `ORANGE_MONEY_RECEIVER_NUMBER`; ne configure jamais de code PIN personnel dans le serveur. Cette version ne communique pas avec une API marchande Orange Money et ne prélève pas les fonds automatiquement. Les contrats PDF restent des brouillons non signés et doivent être révisés juridiquement avant utilisation commerciale.

## Avant la mise en ligne

1. Créer MySQL managé et un utilisateur à privilèges limités; activer sauvegardes et chiffrement.
2. Installer les dépendances Python; lancer `python backend/manage.py migrate` lors de la release, puis `python backend/manage.py collectstatic --noinput`.
3. Lancer Django avec Gunicorn (`config.wsgi:application`) derrière le reverse proxy; le serveur `runserver` et `php -S` sont réservés au développement.
4. Héberger PHP 8 via PHP-FPM/Apache derrière le même domaine; proxyfier `/api/`, `/admin/` et `/static/` vers les services correspondants.
5. Injecter secrets et paramètres depuis le gestionnaire de secrets de l'hébergeur.
6. Régler `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS` sur le domaine exact et générer une nouvelle clé secrète.
7. Activer HTTPS au proxy et régler `DJANGO_SECURE_SSL_REDIRECT=True`, `DJANGO_SECURE_COOKIES=True`. Le proxy doit écraser tout en-tête client `X-Forwarded-Proto` avant de l'envoyer à Django. Configurer HSTS avec `DJANGO_HSTS_SECONDS` uniquement après validation complète de TLS.
8. Configurer, si l'agence le souhaite, `ORANGE_MONEY_RECEIVER_NAME`, `ORANGE_MONEY_RECEIVER_NUMBER` et les informations juridiques. Les valeurs de l'exemple sont vides; ne configure aucun code PIN.
9. Créer l'administrateur, vérifier health check, logs, sauvegarde et procédure de restauration.
10. Tester les parcours d'inscription, authentification, réservations, vente, déclarations et vérification manuelle des paiements, maintenance et téléchargement PDF dans le staging.

Les modules métier disponibles couvrent les demandes de vente, les déclarations de paiements Orange Money à vérifier manuellement, les ordres de maintenance et les PDF récapitulatifs non signés. Cette version ne fait ni encaissement Orange Money automatique, ni signature électronique, ni notifications e-mail/SMS, ni suivi GPS garanti écran verrouillé. Les contrats restent des brouillons et demandent une revue juridique locale.

Avant la production, il faut encore préparer la documentation OpenAPI, le monitoring, une stratégie de sauvegarde/restauration vérifiée, le serveur PHP/Django de production et des tests de charge adaptés au nombre réel de véhicules et d'utilisateurs. Redis, Celery et Channels/WebSockets ne sont pas inclus dans ce déploiement pilote.

## Base locale du développeur

La base MySQL créée sur le poste de développement ne doit pas être exposée sur Internet ni réutilisée comme base de production.
