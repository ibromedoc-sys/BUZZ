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
HTTPS de l'APK et son empreinte SHA-256. Le lien APK doit rester sur le domaine
Firebase Hosting `vente-24ed2.web.app`.

Pour chaque nouvelle version :

1. Incrémenter `android.numeric_version` dans `buildozer.spec` et modifier
   `version` si nécessaire, puis générer l'APK.
2. Copier l'APK dans `web/downloads/vente-<version>.apk`.
3. Calculer son empreinte dans PowerShell (en adaptant le nom de fichier), par
   exemple `(Get-FileHash .\web\downloads\vente-0.2.apk -Algorithm SHA256).Hash`.
4. Mettre à jour `web/app-update.json` avec le nouveau code et nom de version,
   `"/downloads/vente-<version>.apk"` et l'empreinte obtenue en minuscules.
5. Déployer Firebase Hosting avec `firebase deploy --only hosting`.

Au prochain démarrage connecté, l'application proposera le téléchargement.
Elle vérifie l'empreinte avant de lancer l'installateur Android. Android peut
demander à l'utilisateur d'autoriser l'installation depuis VENTE, puis une
confirmation explicite de l'installation. Les APK sous `web/downloads/` sont
ignorées par Git (`*.apk`) mais sont publiées par Firebase Hosting lors du
déploiement local.

Les lectures des collections `produits` et `publications` sont publiques pour
les appareils clients. Seuls les jetons portant `admin: true` peuvent écrire
dans Firestore. Le compte admin doit se déconnecter puis se reconnecter (ou
renouveler son jeton) après modification de ses claims.

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
