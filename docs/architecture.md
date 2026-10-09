# Architecture SmartBus

## Vue MVP

Le navigateur reçoit le shell via PHP et appelle l'API Django REST sous `/api`. Le reverse proxy de déploiement devra présenter PHP et Django sous la même origine pour simplifier cookies, tokens et politique CORS.

Django expose les ressources métier. MySQL est la source de vérité transactionnelle. Les clés étrangères et index servent la flotte, les conducteurs, les positions GPS et les réservations.

## Applications

- `users`: profils, téléphone et rôles.
- `authentication`: inscription, connexion, déconnexion et authentification par token à durée limitée.
- `fleet`: bus, conducteurs et permissions de modification.
- `tracking`: positions GPS historisées.
- `bookings`: réservations atomiques, vérification d'intervalles et tarifs.
- `core`: informations API, santé DB et agrégats du dashboard.

## Évolution ultérieure

Channels + Redis pourront distribuer les positions par WebSocket; Celery + Redis pourra traiter rappels, notifications et rapports. Ces composants ne sont pas activés dans le MVP et ne doivent pas être annoncés comme opérationnels.
