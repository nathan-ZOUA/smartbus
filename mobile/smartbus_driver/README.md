# Prototype SmartBus Flutter — Android et iPhone

Ces sources Flutter sont un prototype séparé. Aucun binaire Android/iPhone n'a été compilé ou testé; ne l'utilise pas pour le pilote actuel. Pour le suivi sur téléphone aujourd'hui, ouvre la page web `/driver.php` depuis le domaine HTTPS SmartBus et garde cette page ouverte pendant le trajet. Un navigateur peut suspendre la géolocalisation en arrière-plan ou lorsque l'écran est verrouillé.

Le prototype Flutter contient :

- connexion avec un compte SmartBus `DRIVER` ;
- liste limitée aux bus affectés à la fiche conducteur ;
- démarrage et arrêt explicites du partage ;
- collecte en arrière-plan avec notification de service visible sur Android ;
- mises à jour de localisation en arrière-plan avec indicateur visible sur iPhone ;
- envoi au serveur au maximum toutes les 10 secondes ;
- token conservé dans le stockage sécurisé Android/iOS ;
- API HTTPS obligatoire sur un téléphone réel.

L'application ne démarre pas le suivi toute seule et n'est pas un outil de surveillance caché. Le conducteur voit quand le partage est actif et peut l'arrêter. Informer les conducteurs et définir la période de collecte avant de l'utiliser.

## Environnement nécessaire

- Flutter stable et Dart compatibles avec `pubspec.yaml` ;
- Android : Android Studio, SDK et JDK 17+ ;
- iPhone : **un Mac avec Xcode**, outils en ligne de commande Xcode, compte Apple Developer pour distribuer via TestFlight/App Store ;
- API SmartBus déployée sur une adresse HTTPS joignable par les téléphones.

L'environnement Windows de développement SmartBus ne contient pas Flutter, Android SDK, Xcode ou JDK; il ne peut donc pas produire ni signer les binaires de téléphone. iOS ne peut pas être compilé ou signé sur Windows.

## Générer les projets natifs

Les sources Flutter de l'application sont dans `lib/main.dart`. Dans PowerShell, crée d'abord le squelette Android/iOS avec Flutter depuis ce répertoire :

```powershell
Set-Location 'C:\Users\zoua\Documents\DEV\projets\SmartBus\mobile\smartbus_driver'
flutter create --platforms=android,ios --org com.smartbus --project-name smartbus_driver .
```

Cette commande ajoute les squelettes natifs au dossier source. Si Flutter remplace `pubspec.yaml` ou `lib/main.dart`, restaure ces deux fichiers depuis Git avant de continuer. Puis lance `flutter pub get`. Ouvre ensuite le projet avec Android Studio pour Android, ou copie le dossier sur un Mac et ouvre `ios\Runner.xcworkspace` avec Xcode pour iOS.

## Configurer le service et l'adresse API

Ne mets pas l'adresse du serveur dans le code. Passe-la au moment du build :

```powershell
flutter run --dart-define=SMARTBUS_API_BASE_URL=https://staging.ton-domaine.tld/api/
flutter build apk --dart-define=SMARTBUS_API_BASE_URL=https://staging.ton-domaine.tld/api/
```

Pour iPhone, sur le Mac :

```bash
flutter build ios --release --dart-define=SMARTBUS_API_BASE_URL=https://staging.ton-domaine.tld/api/
```

L'URL doit désigner directement l'API Django sous `/api/`, présenter un certificat TLS valide, et être joignable depuis le réseau mobile. `localhost`, `127.0.0.1` et le serveur PHP/Django de développement ne sont pas des URL utilisables depuis un téléphone physique.

## Configuration iOS requise

Dans `ios/Runner/Info.plist`, ajouter des explications claires pour l'usage foreground et Always, et activer le mode background location dans `UIBackgroundModes` :

```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>SmartBus partage votre position GPS avec votre agence quand vous démarrez le suivi pendant votre service.</string>
<key>NSLocationAlwaysAndWhenInUseUsageDescription</key>
<string>SmartBus continue le partage GPS pendant votre service lorsque l’application est en arrière-plan ou que l’écran est verrouillé.</string>
<key>UIBackgroundModes</key>
<array>
    <string>location</string>
</array>
```

Sur iPhone, accorder d'abord l'autorisation demandée par iOS, puis ouvrir **Réglages > SmartBus > Position** et choisir **Toujours** si cette option est disponible; activer la localisation précise pour des positions plus fiables. iOS décide de la fréquence des points et peut suspendre ou réduire les mises à jour (mode économie d'énergie, signal GPS, arrêt forcé de l'app). Aucune application ne peut promettre un suivi absolu permanent lorsque l'utilisateur ou le système arrête le processus.

## Configuration Android requise

Après génération avec `flutter create`, vérifier dans `android/app/src/main/AndroidManifest.xml` que ces permissions sont présentes (les ajouter si elles manquent) :

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_LOCATION" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

Le service de localisation fourni par `geolocator` utilise une notification persistante pendant le suivi. Autoriser les notifications, laisser l'activité GPS active en arrière-plan et éviter de forcer l'arrêt de l'application.

## Préparer et essayer un compte conducteur

Dans Django Admin :

1. créer une fiche conducteur ;
2. affecter un bus à cette fiche ;
3. créer un utilisateur avec un mot de passe robuste ;
4. créer le `UserProfile` lié à l'utilisateur, avec le rôle `DRIVER` et cette fiche conducteur.

Sur le téléphone :

1. installer ou lancer l'application de staging ;
2. se connecter avec ce compte, choisir le bus affecté ;
3. autoriser la localisation et les notifications ;
4. appuyer sur **Démarrer le partage GPS** et laisser l'application visible quelques minutes pour vérifier le premier envoi ;
5. verrouiller l'écran, vérifier la notification Android / l'indicateur iOS et contrôler les nouvelles positions depuis le compte gestionnaire ;
6. arrêter le partage, vérifier qu'aucun nouveau point n'arrive, puis se déconnecter.

Tester d'abord sur un seul téléphone et un seul bus. Ensuite essayer les cas réseau coupé/rétabli, GPS désactivé, permission retirée, token expiré, arrêt forcé, batterie faible et changement de réseau avant d'étendre à 10 appareils.

## Limites du pilote

- les positions ne sont pas encore mises en file hors-ligne; elles sont renvoyées quand un nouveau point est reçu après le retour du réseau ;
- la cadence de 10 secondes est une cible maximale, pas une garantie du système mobile ;
- l'utilisation continue du GPS consomme batterie et données ;
- tester le comportement écran verrouillé sur les modèles réels Android/iPhone ;
- le service doit être arrêté à la fin du service.

## Créateur

L'application est attribuée à **Nathan Zoua**, signature courte **NZ**.
