# Sécurité

- Les secrets sont lus depuis l'environnement ou `.env`; le fichier réel est ignoré par Git.
- Crée des identifiants MySQL distincts pour développement, staging et production.
- Les mots de passe sont gérés par les hashers Django et les validateurs de mot de passe.
- Les endpoints d'inscription et de connexion sont limités en débit.
- Les tokens API expirent après 12 heures par défaut et peuvent être révoqués par déconnexion.
- Les rôles limitent les écritures de flotte; les réservations sont filtrées par propriétaire.
- Les positions GPS et informations nominatives des conducteurs ne sont pas publiques.
- Un compte au rôle `DRIVER` ne peut rapporter des positions que pour le bus affecté à sa fiche conducteur; les rapports sont limités à 30 par minute.
- Le navigateur de partage GPS ne transmet la position qu'après action explicite et permission du système; fermer la page arrête le suivi.
- L'application Android native démarre le suivi après action explicite, exige une notification de service visible et stocke le token chiffré avec Android Keystore.
- La géolocalisation navigateur requiert HTTPS en dehors de localhost. Ne collecte pas ces données sans informer les conducteurs et obtenir les accords requis.
- Les expressions de requête passent par l'ORM Django; les entrées sont validées par les serializers.
- Configure HTTPS, HSTS, cookies sécurisés, domaines autorisés exacts et `DEBUG=False` au déploiement.
- Ne stocke pas de données de carte bancaire. Aucun fournisseur de paiement n'est intégré.
- Les tests actuels ne constituent pas un audit de sécurité ni une certification.

Après une exposition accidentelle d'un secret, remplace-le immédiatement dans le service et invalide les tokens/session concernés.
