# SmartBus Conducteur (prototype Android Kotlin)

Le développement mobile recommandé est maintenant l'application Flutter commune à Android et iPhone dans `mobile/smartbus_driver`. Ce projet Kotlin est conservé comme prototype antérieur.

Application native Kotlin pour partager la position du téléphone pendant le service :

- le chauffeur se connecte avec son compte SmartBus de rôle `DRIVER` ;
- l'application ne propose que le ou les bus affectés à son profil ;
- le chauffeur démarre et arrête explicitement le partage ;
- un service Android au premier plan garde une notification persistante pendant le suivi ;
- le GPS est échantillonné par Android et au plus un rapport est envoyé toutes les 10 secondes ;
- le token d'accès est chiffré avec AES-GCM et une clé Android Keystore ;
- les requêtes sont limitées à HTTPS, sauf l'émulateur Android en mode debug.

Le suivi commence uniquement quand l'application est visible et que le chauffeur appuie sur Démarrer. Pas de démarrage automatique, de suivi caché, ni de demande de permission d'arrière-plan permanente. L'application continue normalement pendant le verrouillage grâce au service au premier plan, mais certains fabricants appliquent leurs propres restrictions batterie.

## Configuration et compilation Windows

Installer Android Studio avec Android SDK Platform 35, Android Build Tools et JDK 17. Installer également Gradle 8.9 ou utiliser une installation Gradle compatible fournie par l'environnement Android Studio.

Ouvrir ce dossier comme projet Android Gradle :

```text
SmartBus\android\driver-app
```

Définir l'adresse HTTPS d'une instance de staging SmartBus, qui doit exposer l'API sous `/api/`. Ne saisis pas cette valeur dans le code source :

```powershell
$env:SMARTBUS_API_BASE_URL = 'https://staging.example.org/api/'
gradle :app:assembleDebug
```

Ou passer la propriété Gradle :

```powershell
gradle :app:assembleDebug '-PsmartbusApiBaseUrl=https://staging.example.org/api/'
```

L'APK debug se trouve sous `app\build\outputs\apk\debug\app-debug.apk`. Pour distribuer une APK, configurer une signature de release protégée (clé hors Git) et produire un build release séparé.

## Préparer un compte téléphone

Dans Django Admin :

1. créer une fiche `Driver` ;
2. affecter cette fiche à un bus ;
3. créer le compte utilisateur du chauffeur ;
4. créer son `UserProfile` avec le rôle `DRIVER` et la fiche `Driver` liée.

Installer l'application sur le téléphone, l'ouvrir, se connecter, autoriser la localisation et les notifications, choisir le bus puis appuyer sur **Démarrer le partage GPS**. L'autorisation de notification est requise pour que le suivi soit visible. Une notification SmartBus reste affichée et comprend une action **Arrêter**.

Le token expire selon `SMARTBUS_TOKEN_TTL_HOURS` (12 heures par défaut). Lorsque l'API retourne une erreur d'authentification/permission, le service arrête le suivi et le chauffeur doit rouvrir l'application et se reconnecter.

## Limites du pilote

- l'appareil doit pouvoir joindre l'API par Internet ; utiliser un vrai domaine HTTPS, pas `127.0.0.1` ni l'adresse HTTP de développement ;
- les points GPS ne sont pas mis en file locale quand le réseau est coupé; l'app reprend l'envoi aux prochains points GPS quand la connexion revient ;
- Android peut ralentir les mises à jour et les fabricants peuvent arrêter les applications optimisées pour économiser la batterie ;
- tester la durée de vie de batterie et la précision sur chaque modèle de téléphone avant de l'utiliser avec les 10 chauffeurs ;
- le service est à arrêter en fin de service et les chauffeurs doivent être informés de la collecte.

## Développement émulateur

En mode debug uniquement, un émulateur Android peut utiliser l'API locale via `http://10.0.2.2:8000/api/` et le manifeste debug autorise HTTP pour les tests. Ce chemin HTTP est délibérément refusé sur téléphone physique et dans les builds release. Pour tester sur un vrai téléphone, utilise impérativement une URL HTTPS accessible.
