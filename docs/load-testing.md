# Tests de charge

Aucun chiffre de concurrence ou de débit n'est actuellement garanti.

Avant de définir des objectifs, ajouter un scénario reproductible qui couvre authentification, lectures paginées de flotte, dernières positions GPS et création de réservations sans conflits artificiels. Exécuter les profils progressivement (100, 500, 1 000 utilisateurs), puis seulement augmenter selon les résultats.

Mesurer p50/p95/p99, débit, taux d'erreurs, CPU/RAM, connexions MySQL, temps des requêtes et saturation des workers. Archiver la version du code, la configuration et le rapport. Les essais ne doivent jamais utiliser de données de production.
