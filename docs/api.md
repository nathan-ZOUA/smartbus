# API MVP

Les requêtes JSON d'écriture doivent s'authentifier avec `Authorization: Token <token>`. Les tokens durent 12 heures par défaut (`SMARTBUS_TOKEN_TTL_HOURS`).

| Méthode | Route | Accès | Usage |
|---|---|---|---|
| GET | `/api/` | public | statut API |
| GET | `/api/health/` | public | vérification MySQL |
| POST | `/api/auth/register/` | public, limité en débit | créer un compte client |
| POST | `/api/auth/login/` | public, limité en débit | ouvrir une session token |
| POST | `/api/auth/logout/` | authentifié | révoquer le token |
| GET | `/api/auth/me/` | authentifié | profil |
| GET/POST | `/api/fleet/buses/` | lecture publique; écriture gestionnaire | flotte |
| GET/POST | `/api/fleet/drivers/` | administrateur/gestionnaire de flotte | conducteurs |
| GET | `/api/tracking/positions/` | admin, gestionnaire de flotte | historique GPS paginé |
| GET | `/api/tracking/positions/latest/` | admin, gestionnaire de flotte | dernière position de chaque bus |
| GET | `/api/tracking/positions/my-buses/` | conducteur affecté | lister uniquement ses bus |
| POST | `/api/tracking/positions/report/` | conducteur affecté ou gestionnaire | publier une position GPS (limite 30/minute) |
| GET/POST | `/api/bookings/` | authentifié | lister/créer ses réservations |
| POST | `/api/bookings/{id}/cancel/` | propriétaire ou gestionnaire | annuler une réservation en attente |
| GET/POST | `/api/sales/orders/` | authentifié | lister ses demandes ou demander l'achat d'un bus `FOR_SALE` |
| POST | `/api/sales/orders/{id}/approve/` | gestionnaire commercial | approuver une demande d'achat |
| POST | `/api/sales/orders/{id}/cancel/` | client propriétaire ou gestionnaire | annuler une demande avant paiement |
| GET | `/api/payments/instructions/` | public | vérifier la configuration du numéro Orange Money destinataire |
| GET/POST | `/api/payments/attempts/` | authentifié | lister ses déclarations ou déclarer une référence de transaction |
| POST | `/api/payments/attempts/{id}/verify/` | gestionnaire | confirmer une transaction après vérification Orange Money |
| POST | `/api/payments/attempts/{id}/reject/` | gestionnaire | refuser une référence avec motif |
| GET/POST | `/api/maintenance/orders/` | responsable de maintenance/gestionnaire | gérer les ordres et l'historique de maintenance |
| POST | `/api/maintenance/orders/{id}/approve/` | responsable de maintenance/gestionnaire | approuver un ordre |
| POST | `/api/maintenance/orders/{id}/start/` | responsable de maintenance/gestionnaire | démarrer les travaux et rendre le bus indisponible |
| POST | `/api/maintenance/orders/{id}/complete/` | responsable de maintenance/gestionnaire | terminer les travaux, saisir le coût et restaurer l'état antérieur |
| GET | `/api/contracts/bookings/{id}/pdf/` | propriétaire ou gestionnaire | télécharger un projet de contrat de location après paiement confirmé |
| GET | `/api/contracts/sales/{id}/pdf/` | propriétaire ou gestionnaire | télécharger un projet de contrat de vente après paiement confirmé |
| GET | `/api/dashboard/` | authentifié | agrégats de flotte/réservations |

La pagination par défaut renvoie 25 éléments avec `count`, `next`, `previous` et `results`; le paramètre `page_size` peut demander jusqu'à 100 éléments par page. La documentation OpenAPI/Swagger n'est pas encore ajoutée.

Les déclarations de paiement Orange Money ne réalisent aucun encaissement automatique : le client saisit sa référence et un gestionnaire doit vérifier la transaction dans le compte Orange Money avant de la confirmer dans SmartBus. Configure `ORANGE_MONEY_RECEIVER_NAME` et `ORANGE_MONEY_RECEIVER_NUMBER` dans l'environnement Django avant d'activer le formulaire de paiement. Les montants XAF sont des entiers. Les PDF de contrat sont des brouillons récapitulatifs non signés et doivent être complétés puis vérifiés par un juriste au Cameroun.
