# Base de données

Le moteur configuré est MySQL/MariaDB avec `utf8mb4` et mode strict.

## Modèles MVP

- `auth_user` : comptes Django.
- `UserProfile` : rôle du compte.
- `Driver` : conducteur et permis.
- `Bus` : immatriculation unique, capacité, tarif, statut et conducteur affecté.
- `GPSPosition` : coordonnées, vitesse, cap et date d'enregistrement.
- `Booking` : client, véhicule, période, passagers, tarif calculé et statut.

Les réservations actives utilisent des périodes semi-ouvertes `[départ, retour)` : un retour le même jour qu'un nouveau départ ne constitue donc pas un chevauchement. Le bus est verrouillé pendant la création de réservation; un index couvre le véhicule et les dates.

## Modifications de schéma

Créer les migrations avec `python backend\\manage.py makemigrations`, les inspecter, puis les appliquer avec `python backend\\manage.py migrate`. Ne réinitialise jamais la base de production pour appliquer un changement de schéma.

Faire des sauvegardes MySQL avant une migration de production et tester la restauration.
