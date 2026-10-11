# VENTE — tableau de bord administrateur

Le tableau de bord utilise Firebase Authentication, Firestore et Storage du
projet `vente-24ed2`. Aucun mot de passe ni credential de compte de service
n'est inclus dans le site.

## Préparation Firebase

1. Dans Firebase Console, activer le fournisseur **E-mail/Mot de passe** dans
   Authentication et vérifier que `ibromedoc@gmail.com` peut se connecter.
2. Enregistrer l'application Web du projet Firebase et copier les valeurs
   `apiKey`, `authDomain`, `projectId`, `storageBucket` et
   `messagingSenderId` dans `web/firebase-config.js`. Le SDK de ce tableau de
   bord n'utilise pas l'`appId` Android. La clé API de configuration Firebase
   est une clé client publique, pas une clé privée de compte de service.
3. Vérifier la revendication personnalisée `admin: true` du compte admin. Les
   règles Firestore et Storage font autorité ; masquer l'interface n'est pas
   une protection des données.
4. Vérifier la configuration/activation de Firebase Storage et du bucket
   `vente-24ed2.firebasestorage.app`.

## Déployer

Avec Firebase CLI déjà authentifié :

```sh
firebase deploy --only firestore:rules,storage,hosting
```

Héberger le tableau de bord en HTTPS via Firebase Hosting. Ne pas l'ouvrir
directement depuis `file://` : les modules Firebase exigent un serveur Web.

Les lectures des collections et des images sont publiques pour les appareils
clients. Seuls les jetons portant `admin: true` peuvent écrire dans Firestore
ou téléverser/supprimer des images. Le compte admin doit se déconnecter puis
se reconnecter (ou renouveler son jeton) après modification de ses claims.

Les anciennes images référencées par un chemin local tel que `images/produit1.jpg`
restent inchangées et disponibles dans l'APK existant. Pour les rendre
accessibles depuis le Web et d'autres appareils, modifier l'élément dans le
tableau de bord, sélectionner son fichier source, puis enregistrer : l'image
sera téléversée dans Storage et la référence Firestore remplacée par son URL
HTTPS. Ne pas supprimer les fichiers locaux avant d'avoir vérifié tous les
éléments migrés sur l'application client.

## Vérification

- Connexion avec l'administrateur : affichage des produits et publications.
- Création, modification, suppression de chaque type et téléversement d'une
  image JPEG/PNG/WebP (5 Mo maximum).
- Connexion d'un compte sans `admin: true` : aucune écriture autorisée.
- Affichage des URL d'images sur l'application Android et un second appareil.
- Déploiement séparé des règles Storage et Firestore avant l'utilisation.
