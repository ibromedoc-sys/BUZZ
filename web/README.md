# BUZZ — tableau de bord administrateur

Le tableau de bord utilise Firebase Authentication et Firestore du projet
`buzz-6e997`. Il n'initialise pas Firebase Storage et n'inclut aucun mot de
passe ni credential de compte de service.

## Préparation Firebase

1. Dans Firebase Console, activer le fournisseur **E-mail/Mot de passe** dans
   Authentication et vérifier que `ibromedoc@gmail.com` peut se connecter.
2. La configuration Firebase est définie dans `web/firebase-config.js` pour le
   projet BUZZ. La clé API Firebase de configuration est publique ; elle ne doit
   pas être confondue avec un credential de compte de service.
3. Vérifier la revendication personnalisée `admin: true` du compte admin. Les
   règles Firestore font autorité ; masquer l'interface n'est pas une
   protection des données.

## Déployer

Avec Firebase CLI déjà authentifié :

```sh
firebase deploy --only hosting,firestore:rules
```

Héberger le tableau de bord en HTTPS via Firebase Hosting et publier les règles
Firestore mises à jour. Ne pas l'ouvrir directement depuis `file://` : les
modules Firebase exigent un serveur Web.

## Distribuer l'application et les mises à jour via Google Play

Les mises à jour de BUZZ seront distribuées par Google Play ; l'application ne
vérifie plus un manifeste distant et ne télécharge ni n'installe d'APK depuis
GitHub. Le fichier `web/app-update.json` et l'ancien mécanisme d'installation
directe ne sont plus utilisés. Firebase Hosting reste dédié au tableau de bord.

L'identifiant Android actuel est `com.buzz.app` (`package.domain` +
`package.name` dans `buildozer.spec`) : il doit rester identique pour publier
des mises à jour de la même application Play. Le format de sortie release est
configuré en Android App Bundle (`aab`) ; le workflow GitHub Actions actuel
construit encore une APK debug de test, pas un bundle prêt à téléverser dans la
Play Console.

Avant une publication Play, il faudra :

1. Créer l'application dans la Play Console et compléter les informations
   demandées, puis activer Play App Signing.
2. Incrémenter `android.numeric_version` à chaque publication (la version
   préparée est actuellement le code `2`) et modifier `version` pour le nom
   affiché.
3. Compiler un bundle release signé avec la clé d'envoi configurée pour Play,
   puis téléverser le `.aab` dans une piste de test interne avant la production.
   Garder une sauvegarde privée de la clé d'envoi ; ne pas la committer.
4. Installer la version de test depuis Play. Ensuite, Play gère la distribution
   des mises à jour selon les réglages de l'utilisateur (mises à jour
   automatiques, ou mise à jour manuelle depuis le Play Store).

L'APK debug distribuée auparavant hors Play peut avoir une signature différente
de celle installée par Play. Si Android refuse la première installation Play
par-dessus, il faudra désinstaller l'ancienne APK puis installer l'application
depuis la piste de test Play ; les données locales peuvent être effacées.

Les lectures des collections `produits`, `publications` et `contenu` sont
publiques pour les appareils clients. Seuls les jetons portant `admin: true`
peuvent écrire dans Firestore. Le tableau de bord conserve les contenus fixes
dans `contenu/accueil` (textes et quatre logos) et `contenu/apropos` (titre des
actualités, textes de la page « À propos » et photo). Les valeurs initiales
reproduisent celles de l'application ; les images locales existantes sont
conservées tant qu'elles ne sont pas remplacées. L'application Android lit ces
documents au démarrage et garde son contenu local si aucun document n'a encore
été créé. Cette lecture à distance nécessite d'abord de publier une nouvelle
version Android contenant cette fonctionnalité ; ensuite, modifier ces champs
ne nécessite pas une nouvelle publication Android. Le compte admin doit se
déconnecter puis se reconnecter (ou renouveler son jeton) après modification de
ses claims. Le document `contenu/apropos` contient aussi `apropos_lien_url`,
destination HTTPS du lien `apropos_lien_texte`; l'application l'ouvre depuis la
page « À propos ». Sa valeur par défaut est `https://superlife-togo.com`.

Chaque document de `produits` peut définir `telephone_commande`, le numéro
WhatsApp international à utiliser pour le bouton « Commander » de ce produit.
Le tableau de bord permet de le saisir et de le modifier produit par produit.
Les anciens produits sans ce champ continuent d’utiliser le numéro historique
`22899057931` jusqu’à leur modification.

## Hébergement d'images

Le tableau de bord téléverse directement les images vers Cloudinary avec le
cloud `jvljzrue` et le preset non signé `vente_images` (configuration Cloudinary
existante, indépendante du projet Firebase BUZZ). Aucune clé secrète ni
Firebase Storage n'est utilisé. Firestore conserve l'URL HTTPS `secure_url`
renvoyée par Cloudinary dans le champ `image` des collections `produits` et
`publications` et dans les champs d'image de `contenu/accueil` et
`contenu/apropos`. Une URL HTTPS saisie manuellement reste possible pour
préserver le flux précédent. Lors d'une modification, ne pas choisir de fichier
ni saisir d'URL conserve la référence actuelle, y compris les références locales
historiques.

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

- Connexion avec l'administrateur : affichage des produits, publications et
  des textes actuels de l'accueil et de la page « À propos ».
- Modification des textes et des images de l'accueil/infos ; vérification de
  leur affichage dans l'application Android après redémarrage.
- Création, modification et suppression de chaque type dans Firestore.
- Modification du numéro de commande de produits différents et vérification
  que chaque bouton « Commander » ouvre le bon numéro WhatsApp.
- Téléversement Cloudinary d'une image JPEG, PNG ou WebP et enregistrement de
  son URL HTTPS dans Firestore.
- Conservation de l'image existante si aucun nouveau fichier n'est sélectionné.
- Connexion d'un compte sans `admin: true` : aucune écriture autorisée.
- Affichage des URL d'images sur l'application Android et un second appareil.
- Publication Android via une piste de test interne Google Play.
- Ne pas déployer les règles Storage ni modifier le forfait Firebase pour
  cette solution.
