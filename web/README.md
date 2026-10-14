# VENTE — tableau de bord administrateur

Le tableau de bord utilise Firebase Authentication et Firestore du projet
`vente-24ed2`. Il n'initialise pas Firebase Storage et n'inclut aucun mot de
passe ni credential de compte de service.

## Préparation Firebase

1. Dans Firebase Console, activer le fournisseur **E-mail/Mot de passe** dans
   Authentication et vérifier que `ibromedoc@gmail.com` peut se connecter.
2. Conserver la configuration existante de l'application Web dans
   `web/firebase-config.js`. La clé API Firebase de configuration est publique ;
   elle ne doit pas être confondue avec un credential de compte de service.
3. Vérifier la revendication personnalisée `admin: true` du compte admin. Les
   règles Firestore font autorité ; masquer l'interface n'est pas une
   protection des données.

## Déployer

Avec Firebase CLI déjà authentifié :

```sh
firebase deploy --only hosting
```

Héberger le tableau de bord en HTTPS via Firebase Hosting. Ne pas l'ouvrir
directement depuis `file://` : les modules Firebase exigent un serveur Web.

## Publier une mise à jour Android

L'application vérifie `https://vente-24ed2.web.app/app-update.json` au démarrage.
Le manifeste versionné dans `web/app-update.json` doit contenir un `version_code`
entier supérieur à celui de l'application installée, un `version_name`, l'URL
HTTPS directe de l'APK jointe à une GitHub Release du dépôt public
`ibromedoc-sys/VENTE` et son empreinte SHA-256. L'application accepte le lien de
téléchargement de ce dépôt, puis les domaines de fichiers GitHub utilisés pour
la redirection du téléchargement.

Pour chaque nouvelle version :

1. Incrémenter `android.numeric_version` dans `buildozer.spec` et modifier
   `version` si nécessaire, puis générer l'APK.
2. Télécharger l'artefact `VENTE-APK-RELEASE` du workflow GitHub Actions et
   calculer l'empreinte de l'APK release dans PowerShell, par exemple :

   ```powershell
   $apk = Get-ChildItem .\bin\*-release.apk | Select-Object -First 1
   (Get-FileHash $apk.FullName -Algorithm SHA256).Hash
   ```

3. Créer sur GitHub une Release avec le tag `v<version>` et joindre l'APK sous
   le nom `vente-<version>.apk`. Le dépôt doit être public pour que l'application
   puisse télécharger l'APK sans identifiants.
4. Mettre à jour `web/app-update.json` avec le nouveau code et nom de version,
   l'URL de l'asset de la Release et l'empreinte SHA-256 obtenue (en minuscules).
5. Déployer uniquement le manifeste et le tableau de bord avec
   `firebase deploy --only hosting`. Ne pas placer l'APK dans `web` : Firebase
   Hosting du forfait Spark refuse les exécutables.

La version préparée ici est `0.2` (code `2`), avec le lien GitHub Release
`https://github.com/ibromedoc-sys/VENTE/releases/download/v0.2/vente-0.2.apk`.
Avant de déployer le manifeste, vérifier que son empreinte SHA-256 correspond
bien à l'APK compilée ; sinon, la remplacer par la valeur calculée. Une
empreinte qui ne correspond pas empêche volontairement l'installation.

Au prochain démarrage connecté, l'application proposera le téléchargement.
Elle vérifie l'empreinte avant de lancer l'installateur Android. Android peut
demander à l'utilisateur d'autoriser l'installation depuis VENTE, puis une
confirmation explicite de l'installation. Firebase Hosting ne sert que le
manifeste ; l'APK est distribuée par la GitHub Release.

Les lectures des collections `produits` et `publications` sont publiques pour
les appareils clients. Seuls les jetons portant `admin: true` peuvent écrire
dans Firestore. Le compte admin doit se déconnecter puis se reconnecter (ou
renouveler son jeton) après modification de ses claims.

## Signature des APK compilées par GitHub Actions

Le workflow `.github/workflows/build-apk.yml` construit une APK `release`
signée, puis l'envoie comme artefact `VENTE-APK-RELEASE`. Pour que chaque build
utilise la même identité de signature :

1. Créer une seule fois un keystore de publication dans un emplacement sûr,
   par exemple avec :

   ```powershell
   keytool -genkeypair -v -keystore vente-release.jks -alias vente -keyalg RSA -keysize 2048 -validity 10000
   ```

   Choisir et conserver les mots de passe sans les mettre dans le dépôt.
2. Encoder le fichier keystore en Base64 sous Windows PowerShell :
   `[Convert]::ToBase64String([IO.File]::ReadAllBytes(".\vente-release.jks"))`.
3. Dans GitHub, ouvrir **Settings → Secrets and variables → Actions → New
   repository secret**, puis créer les secrets `ANDROID_KEYSTORE_BASE64`
   (résultat Base64), `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS` (ici
   `vente`) et `ANDROID_KEY_PASSWORD`.
4. Sauvegarder le keystore et ses mots de passe dans un endroit sûr et chiffré.
   Ne jamais régénérer cette clé pour les futures mises à jour : si elle est
   perdue, Android ne pourra plus installer les APK suivantes par-dessus celles
   signées avec cette clé.

Les secrets ne sont utilisés que sur le runner GitHub ; le keystore est écrit
temporairement dans `RUNNER_TEMP`, hors du dépôt, et n'est pas inclus dans
l'artefact APK. Les secrets doivent être créés avant le prochain lancement du
workflow. L'APK `0.2` actuellement publiée a été compilée en debug, sans clé
persistante connue. La nouvelle clé release ne correspondra donc pas à sa
signature : pour installer la première APK release, il faudra désinstaller
l'ancienne application, puis conserver cette nouvelle clé pour tous les builds
futurs.

## Hébergement d'images

Le tableau de bord téléverse directement les images vers Cloudinary avec le
cloud `jvljzrue` et le preset non signé `vente_images`. Aucune clé secrète ni
Firebase Storage n'est utilisé. Firestore conserve l'URL HTTPS `secure_url`
renvoyée par Cloudinary dans le champ `image` des collections `produits` et
`publications`. Une URL HTTPS saisie manuellement reste possible pour préserver
le flux précédent. Lors d'une modification, ne pas choisir de fichier ni saisir
d'URL conserve la référence actuelle, y compris les références locales historiques.

Les fichiers sont limités à JPEG, PNG ou WebP et à 5 Mo pour rester compatibles
avec le client Android, qui lit les images HTTPS selon leur type MIME et les met
en cache localement. Les chemins historiques tels que `images/produit1.jpg` ne
sont pas réécrits et les fichiers locaux ne doivent pas être supprimés : ils
restent nécessaires aux références locales de l'APK.

Un preset non signé et son cloud name sont visibles dans le code du navigateur
et l'endpoint Cloudinary ne vérifie pas la connexion Firebase : toute personne
qui connaît ces paramètres peut tenter un téléversement. Restreindre le preset
dans Cloudinary aux formats image attendus et à la taille maximale autorisée,
désactiver l'écrasement si possible et surveiller les quotas. Ne jamais ajouter
de secret Cloudinary au client. Ne pas activer Firebase Storage, modifier la
facturation ni déployer `storage.rules`.

## Vérification

- Connexion avec l'administrateur : affichage des produits et publications.
- Création, modification et suppression de chaque type dans Firestore.
- Téléversement Cloudinary d'une image JPEG, PNG ou WebP et enregistrement de
  son URL HTTPS dans Firestore.
- Conservation de l'image existante si aucun nouveau fichier n'est sélectionné.
- Connexion d'un compte sans `admin: true` : aucune écriture autorisée.
- Affichage des URL d'images sur l'application Android et un second appareil.
- Ne pas déployer les règles Storage ni modifier le forfait Firebase pour
  cette solution.
