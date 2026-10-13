import hashlib
import json
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPException
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.graphics import Color, Rectangle
from kivy.graphics.texture import Texture
from kivymd.app import MDApp
from kivymd.uix.navigationbar import (
    MDNavigationBar,
    MDNavigationItem,
    MDNavigationItemIcon,
    MDNavigationItemLabel,
)

from database import FirebaseError, obtenir_produits, obtenir_publications, image_locale

from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label as KivyLabel

UPDATE_MANIFEST_URL = "https://vente-24ed2.web.app/app-update.json"
MAX_APK_SIZE = 250 * 1024 * 1024

try:
    from android import activity
except ImportError:
    activity = None


class BaseNavigationItem(MDNavigationItem):
    icon = StringProperty()
    text = StringProperty()
    screen_name = StringProperty()


class AnimatedLogo(BoxLayout):
    scale = NumericProperty(1)


class GradientBackground(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        texture = Texture.create(size=(1, 256), colorfmt="rgba")
        pixels = bytearray()
        top_color = (14, 30, 59)
        bottom_color = (19, 91, 102)
        for y in range(256):
            ratio = y / 255
            color = tuple(
                round(bottom + (top - bottom) * ratio)
                for top, bottom in zip(top_color, bottom_color)
            )
            pixels.extend((*color, 255))
        texture.blit_buffer(bytes(pixels), colorfmt="rgba", bufferfmt="ubyte")
        texture.wrap = "clamp_to_edge"
        texture.mag_filter = "linear"
        texture.min_filter = "linear"
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._gradient = Rectangle(texture=texture, pos=self.pos, size=self.size)
        self.bind(pos=self._actualiser_degrade, size=self._actualiser_degrade)

    def _actualiser_degrade(self, *_):
        self._gradient.pos = self.pos
        self._gradient.size = self.size


KV = """
<AnimatedLogo>:
    canvas.before:
        PushMatrix
        Scale:
            x: self.scale
            y: self.scale
            origin: self.center
    canvas.after:
        PopMatrix

<BaseNavigationItem>:
    MDNavigationItemIcon:
        icon: root.icon

    MDNavigationItemLabel:
        text: root.text

MDScreen:
    MDBoxLayout:
        orientation: "vertical"
        size_hint: None, None
        size: root.size
        pos: root.pos

        MDTopAppBar:
            title: "VENTE"

        MDScreenManager:
            id: screen_manager

            MDScreen:
                name: "accueil"
                GradientBackground:
                    orientation: "vertical"
                    padding: ["30dp", "10dp", "30dp", "30dp"]
                    spacing: "12dp"
                    MDLabel:
                        text: "Bienvenue Chez SUPERLIFE TOGO!"
                        halign: "center"
                        font_size: "30sp"
                        bold: True
                        color: 1, 1, 1, 1
                        size_hint_y: None
                        height: "55dp"
                    AnimatedLogo:
                        id: home_logo
                        orientation: "vertical"
                        size_hint_y: None
                        height: "170dp"
                        spacing: "5dp"
                        MDIcon:
                            id: logo_icon
                            icon: "storefront"
                            font_size: "92sp"
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            opacity: 0 if app.logo_available else 1
                        Image:
                            id: logo_image
                            source: app.logo_image
                            opacity: 1 if app.logo_available else 0
                            fit_mode: "contain"
                            size_hint: 1, 1
                            size_hint_y: None
                            height: "120dp"
                        MDLabel:
                            text: "VENTE"
                            halign: "center"
                            font_size: "22sp"
                            bold: True
                            color: 1, 1, 1, 1
                            opacity: 0 if app.logo_available else 1
                    MDLabel:
                        text: "Découvrez nos produits et nos infos en exclusivités dans le domaine de l'entrepreneuriat."
                        halign: "center"
                        font_size: "18sp"
                        color: 1, 1, 1, 1
                        size_hint_y: None
                        height: "60dp"
                    MDBoxLayout:
                        orientation: "horizontal"
                        size_hint: None, None
                        width: "272dp"
                        height: "48dp"
                        spacing: "12dp"
                        pos_hint: {"center_x": 0.5}
                        MDButton:
                            id: produits_shortcut
                            style: "tonal"
                            size_hint_x: None
                            width: "130dp"
                            on_release: app.ouvrir_onglet("produits")
                            MDButtonText:
                                text: "PRODUITS"
                        MDButton:
                            id: infos_shortcut
                            style: "tonal"
                            size_hint_x: None
                            width: "130dp"
                            on_release: app.ouvrir_onglet("infos")
                            MDButtonText:
                                text: "NOS INFOS"

            MDScreen:
                name: "produits"
                ScrollView:
                    MDBoxLayout:
                        id: produits_container
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "20dp"
                        size_hint_y: None
                        height: self.minimum_height
                        MDLabel:
                            text: "NOS PRODUITS"
                            halign: "center"
                            font_size: "30sp"
                            bold: True
                            size_hint_y: None
                            height: "50dp"

            MDScreen:
                name: "infos"
                ScrollView:
                    id: publications_scroll
                    MDBoxLayout:
                        id: publications_container
                        orientation: "vertical"
                        padding: "15dp"
                        spacing: "20dp"
                        size_hint_y: None
                        height: self.minimum_height
                        MDLabel:
                            text: "INFOS & ACTUALITÉS"
                            halign: "center"
                            font_size: "30sp"
                            bold: True
                            size_hint_y: None
                            height: "50dp"

            MDScreen:
                name: "apropos"
                GradientBackground:
                    orientation: "vertical"
                    padding: "30dp"
                    spacing: "20dp"
                    MDLabel:
                        text: "À PROPOS"
                        halign: "center"
                        font_size: "30sp"
                        bold: True
                        color: 1, 1, 1, 1
                        size_hint_y: None
                        height: "55dp"
                    FloatLayout:
                        size_hint_y: None
                        height: "240dp"
                        MDIcon:
                            icon: "account-circle"
                            font_size: "150sp"
                            theme_text_color: "Custom"
                            text_color: 0.75, 0.8, 0.88, 1
                            opacity: 0 if app.owner_photo_available else 1
                            pos_hint: {"center_x": 0.5, "center_y": 0.5}
                        Image:
                            source: app.owner_photo
                            opacity: 1 if app.owner_photo_available else 0
                            fit_mode: "contain"
                            size_hint: None, None
                            size: "220dp", "220dp"
                            pos_hint: {"center_x": 0.5, "center_y": 0.5}
                    MDLabel:
                        text: "M. DEDJI Kossi Adeoto, Représentant SuperLife TOGO. Pour toutes informations sur notre entreprise, rendez-vous sur notre site officiel."
                        halign: "center"
                        font_size: "18sp"
                        color: 1, 1, 1, 1
                        size_hint_y: None
                        height: "90dp"
                    Widget:
                        size_hint_y: 1
                    Button:
                        text: "[u]superlife-togo.com[/u]"
                        markup: True
                        color: 0.78, 0.91, 1, 1
                        bold: True
                        font_size: "18sp"
                        background_normal: ""
                        background_color: 0, 0, 0, 0
                        size_hint_y: None
                        height: "48dp"
                        on_release: app.ouvrir_site()

        MDNavigationBar:
            id: navigation_bar
            on_switch_tabs: app.on_switch_tabs(*args)
            BaseNavigationItem:
                icon: "home"
                text: "Accueil"
                screen_name: "accueil"
                active: True
            BaseNavigationItem:
                icon: "shopping"
                text: "Produits"
                screen_name: "produits"
            BaseNavigationItem:
                icon: "newspaper"
                text: "Infos"
                screen_name: "infos"
            BaseNavigationItem:
                icon: "information"
                text: "À propos"
                screen_name: "apropos"
"""


def kv_escape(value):
    if value is None:
        return ""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


class VenteApp(MDApp):
    logo_image = StringProperty("")
    logo_available = BooleanProperty(False)
    owner_photo = StringProperty("")
    owner_photo_available = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._database_executor = ThreadPoolExecutor(max_workers=3)
        self._publication_widgets = {}
        self._update_popup = None

    def _verifier_mise_a_jour(self):
        if activity is None:
            return
        self._database_executor.submit(self._charger_mise_a_jour)

    def _charger_mise_a_jour(self):
        try:
            from jnius import JavaException, autoclass
        except ImportError as error:
            Logger.warning("VENTE: vérification de version indisponible: %s" % error)
            return

        try:
            request = Request(
                UPDATE_MANIFEST_URL,
                headers={"User-Agent": "VENTE-Android"},
            )
            with urlopen(request, timeout=15) as response:
                final_url = urlparse(response.geturl())
                if (
                    final_url.scheme != "https"
                    or final_url.hostname != urlparse(UPDATE_MANIFEST_URL).hostname
                ):
                    raise ValueError("Le manifeste a été redirigé vers un autre hôte.")
                manifest = json.loads(response.read(64 * 1024).decode("utf-8"))

            if not isinstance(manifest, dict):
                raise ValueError("Le manifeste de mise à jour est invalide.")
            version_code = manifest.get("version_code")
            version_name = manifest.get("version_name")
            apk_url = urljoin(UPDATE_MANIFEST_URL, manifest.get("apk_url", ""))
            apk_hash = manifest.get("sha256")
            parsed_apk_url = urlparse(apk_url)
            if (
                isinstance(version_code, bool)
                or not isinstance(version_code, int)
                or version_code < 1
                or version_code > 2_100_000_000
                or not isinstance(version_name, str)
                or not version_name.strip()
                or parsed_apk_url.scheme != "https"
                or parsed_apk_url.hostname
                != urlparse(UPDATE_MANIFEST_URL).hostname
                or not isinstance(apk_hash, str)
                or len(apk_hash) != 64
                or any(character not in "0123456789abcdefABCDEF" for character in apk_hash)
            ):
                raise ValueError("Le manifeste de mise à jour contient des données invalides.")

            activity_class = autoclass("org.kivy.android.PythonActivity")
            installed_code = int(
                autoclass("com.vente.app.ApkInstaller").getInstalledVersionCode(
                    activity_class.mActivity
                )
            )
            if version_code > installed_code:
                update = {
                    "version_code": version_code,
                    "version_name": version_name.strip(),
                    "apk_url": apk_url,
                    "sha256": apk_hash.lower(),
                }
                Clock.schedule_once(
                    lambda dt, update=update: self._proposer_mise_a_jour(update), 0
                )
        except (
            JavaException,
            AttributeError,
            RuntimeError,
            URLError,
            TimeoutError,
            OSError,
            ValueError,
            TypeError,
            HTTPException,
        ) as error:
            Logger.warning("VENTE: vérification des mises à jour impossible: %s" % error)

    def _creer_popup(self, title, message, buttons):
        layout = BoxLayout(
            orientation="vertical", padding="12dp", spacing="8dp"
        )
        message_label = KivyLabel(
            text=message,
            halign="center",
            valign="middle",
        )
        layout.add_widget(message_label)
        layout.bind(
            width=lambda instance, width: setattr(
                message_label, "text_size", (width - 24, None)
            )
        )
        button_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height="48dp", spacing="8dp"
        )
        if buttons:
            layout.add_widget(button_row)
        popup = Popup(
            title=title,
            content=layout,
            size_hint=(0.9, None),
            height="210dp" if buttons else "150dp",
            auto_dismiss=False,
        )
        for label, callback in buttons:
            button = Button(text=label)
            button.bind(on_release=lambda instance, cb=callback: cb(popup))
            button_row.add_widget(button)
        popup.open()
        return popup

    def _proposer_mise_a_jour(self, update):
        self._creer_popup(
            "Mise à jour disponible",
            "La version {} de VENTE est disponible. Voulez-vous la télécharger ?".format(
                update["version_name"]
            ),
            [
                ("Plus tard", lambda popup: popup.dismiss()),
                ("Télécharger", lambda popup: self._telecharger_mise_a_jour(popup, update)),
            ],
        )

    def _telecharger_mise_a_jour(self, popup, update):
        popup.dismiss()
        self._update_popup = self._creer_popup(
            "Téléchargement",
            "Téléchargement de la mise à jour en cours…",
            [],
        )
        future = self._database_executor.submit(self._telecharger_apk, update)

        def terminer(tache):
            try:
                apk_path = tache.result()
            except (
                URLError,
                TimeoutError,
                OSError,
                ValueError,
                TypeError,
                HTTPException,
            ) as error:
                Clock.schedule_once(
                    lambda dt, error=error: self._echec_telechargement(error), 0
                )
                return
            Clock.schedule_once(
                lambda dt, apk_path=apk_path: self._proposer_installation(apk_path), 0
            )

        future.add_done_callback(terminer)

    def _telecharger_apk(self, update):
        request = Request(update["apk_url"], headers={"User-Agent": "VENTE-Android"})
        update_dir = Path(self.user_data_dir) / "updates"
        update_dir.mkdir(parents=True, exist_ok=True)
        apk_path = update_dir / "vente-update.apk"
        temporary_path = update_dir / "vente-update.apk.part"
        digest = hashlib.sha256()
        downloaded = 0
        try:
            with urlopen(request, timeout=30) as response:
                final_url = urlparse(response.geturl())
                if (
                    final_url.scheme != "https"
                    or final_url.hostname != urlparse(UPDATE_MANIFEST_URL).hostname
                ):
                    raise ValueError("Le téléchargement a été redirigé vers un autre hôte.")
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_APK_SIZE:
                    raise ValueError("Le fichier APK dépasse la taille maximale autorisée.")
                with temporary_path.open("wb") as apk_file:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        downloaded += len(chunk)
                        if downloaded > MAX_APK_SIZE:
                            raise ValueError("Le fichier APK dépasse la taille maximale autorisée.")
                        digest.update(chunk)
                        apk_file.write(chunk)
            if digest.hexdigest() != update["sha256"]:
                raise ValueError("La vérification de sécurité de l’APK a échoué.")
            temporary_path.replace(apk_path)
            return str(apk_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    def _echec_telechargement(self, error):
        if self._update_popup is not None:
            self._update_popup.dismiss()
            self._update_popup = None
        self._afficher_erreur(
            ValueError("Impossible de télécharger la mise à jour : {}".format(error))
        )

    def _proposer_installation(self, apk_path):
        if self._update_popup is not None:
            self._update_popup.dismiss()
            self._update_popup = None

        def installer(popup):
            popup.dismiss()
            try:
                from jnius import JavaException, autoclass
            except ImportError as error:
                self._afficher_erreur(
                    ValueError("PyJNIus est indisponible : {}".format(error))
                )
                return

            try:
                activity_class = autoclass("org.kivy.android.PythonActivity")
                autoclass("com.vente.app.ApkInstaller").install(
                    activity_class.mActivity, apk_path
                )
            except (JavaException, ImportError, AttributeError, RuntimeError) as error:
                self._afficher_erreur(
                    ValueError("Impossible de lancer l’installateur Android : {}".format(error))
                )

        self._creer_popup(
            "Téléchargement terminé",
            "L’APK a été vérifié. Android vous demandera de confirmer son installation.",
            [("Installer", installer), ("Plus tard", lambda popup: popup.dismiss())],
        )

    def _reprendre_installation(self):
        if activity is None:
            return
        try:
            from jnius import JavaException, autoclass
        except ImportError as error:
            self._afficher_erreur(
                ValueError("PyJNIus est indisponible : {}".format(error))
            )
            return

        try:
            activity_class = autoclass("org.kivy.android.PythonActivity")
            status = autoclass("com.vente.app.ApkInstaller").resumeInstall(
                activity_class.mActivity
            )
        except (JavaException, ImportError, AttributeError, RuntimeError) as error:
            self._afficher_erreur(
                ValueError("Impossible de reprendre l’installation Android : {}".format(error))
            )
            return
        if status == 2:
            self._afficher_erreur(
                ValueError(
                    "Autorisez VENTE à installer des applications depuis cette source "
                    "dans les paramètres Android, puis revenez dans VENTE."
                )
            )

    def _executer_en_arriere_plan(self, operation, on_success=None):
        future = self._database_executor.submit(operation)

        def terminer(tache):
            try:
                resultat = tache.result()
            except Exception as error:
                Clock.schedule_once(
                    lambda dt, error=error: self._afficher_erreur(error), 0
                )
                return
            if on_success:
                Clock.schedule_once(lambda dt: on_success(resultat), 0)

        future.add_done_callback(terminer)

    def _afficher_erreur(self, error):
        Popup(
            title="Erreur",
            content=KivyLabel(text=str(error)),
            size_hint=(0.9, None),
            height="180dp",
        ).open()

    def _charger_avec_images(self, collection_loader):
        records = collection_loader()
        rows = []
        image_errors = []
        for row in records:
            try:
                local_image = image_locale(row[-1], self.user_data_dir)
            except FirebaseError as error:
                local_image = ""
                image_errors.append(str(error))
            rows.append((*row[:-1], local_image))
        return rows, image_errors

    def _afficher_erreurs_images(self, image_errors):
        if image_errors:
            self._afficher_erreur(
                FirebaseError(
                    "Certaines images n'ont pas pu être chargées :\n"
                    + "\n".join(image_errors[:3])
                )
            )

    def commander_whatsapp(self, produit, prix):
        numero = "22899057931"
        message = "Bonjour, je souhaite commander {} au prix de {}.".format(
            produit, prix
        )
        webbrowser.open("https://wa.me/{}?text={}".format(numero, quote(message)))

    def ouvrir_site(self):
        webbrowser.open("https://superlife-togo.com")

    def on_switch_tabs(self, bar, item, item_icon, item_text):
        self.root.ids.screen_manager.current = item.screen_name

    def ouvrir_onglet(self, screen_name):
        navigation_bar = self.root.ids.navigation_bar
        item = next(
            item
            for item in navigation_bar.children
            if item.screen_name == screen_name
        )
        navigation_bar.set_active_item(item)

    def afficher_produits(self):
        self._executer_en_arriere_plan(
            lambda: self._charger_avec_images(obtenir_produits),
            self._afficher_produits,
        )

    def _afficher_produits(self, result):
        produits, image_errors = result
        container = self.root.ids.produits_container
        container.clear_widgets()
        container.add_widget(
            Builder.load_string(
                """
MDLabel:
    text: "NOS PRODUITS"
    halign: "center"
    font_size: "30sp"
    bold: True
    size_hint_y: None
    height: "50dp"
"""
            )
        )

        for _, nom, prix, description, image in produits:
            carte = Builder.load_string(
                """
MDCard:
    orientation: "vertical"
    size_hint_y: None
    height: "400dp"
    padding: "10dp"
    spacing: "10dp"
    elevation: 3
    Image:
        source: "{}"
        size_hint_y: None
        height: "200dp"
    MDLabel:
        text: "{}"
        font_size: "22sp"
        bold: True
        halign: "center"
        size_hint_y: None
        height: "40dp"
    MDLabel:
        text: "{}"
        font_size: "20sp"
        halign: "center"
        size_hint_y: None
        height: "40dp"
    MDLabel:
        text: "{}"
        halign: "center"
        size_hint_y: None
        height: "50dp"
    MDButton:
        style: "filled"
        pos_hint: {{"center_x": 0.5}}
        size_hint_x: None
        width: "220dp"
        on_release: app.commander_whatsapp("{}", "{}")
        MDButtonIcon:
            icon: "whatsapp"
        MDButtonText:
            text: "Commander"
""".format(
                    kv_escape(image),
                    kv_escape(nom),
                    kv_escape(prix),
                    kv_escape(description),
                    kv_escape(nom),
                    kv_escape(prix),
                )
            )
            container.add_widget(carte)
        self._afficher_erreurs_images(image_errors)

    def afficher_publications(self, publication_id=None):
        self._executer_en_arriere_plan(
            lambda: self._charger_avec_images(obtenir_publications),
            lambda result: self._afficher_publications(result, publication_id),
        )

    def _afficher_publications(self, result, publication_id=None):
        publications, image_errors = result
        container = self.root.ids.publications_container
        container.clear_widgets()
        container.add_widget(
            Builder.load_string(
                """
MDLabel:
    text: "INFOS & ACTUALITÉS"
    halign: "center"
    font_size: "30sp"
    bold: True
    size_hint_y: None
    height: "50dp"
"""
            )
        )
        self._publication_widgets = {}

        for id_publication, titre, contenu, date, image in publications:
            carte = Builder.load_string(
                """
MDCard:
    orientation: "vertical"
    size_hint_y: None
    height: "400dp"
    padding: "10dp"
    spacing: "10dp"
    elevation: 3
    Image:
        source: "{}"
        size_hint_y: None
        height: "200dp"
    MDLabel:
        text: "{}"
        font_size: "22sp"
        bold: True
        halign: "center"
        size_hint_y: None
        height: "45dp"
    MDLabel:
        text: "{}"
        font_size: "15sp"
        halign: "center"
        size_hint_y: None
        height: "30dp"
    MDLabel:
        text: "{}"
        font_size: "16sp"
        halign: "center"
        size_hint_y: None
        height: "100dp"
""".format(
                    kv_escape(image),
                    kv_escape(titre),
                    kv_escape(date),
                    kv_escape(contenu),
                )
            )
            container.add_widget(carte)
            self._publication_widgets[str(id_publication)] = carte

        if publication_id is not None:
            target = self._publication_widgets.get(str(publication_id))
            self.root.ids.screen_manager.current = "infos"
            if target is None:
                self._afficher_erreur(
                    FirebaseError(
                        "La publication demandée par la notification n'existe plus."
                    )
                )
            else:
                Clock.schedule_once(
                    lambda dt: self.root.ids.publications_scroll.scroll_to(
                        target, padding=12
                    ),
                    0.2,
                )
        self._afficher_erreurs_images(image_errors)

    def _consommer_intention_notification(self, intent=None):
        if intent is None:
            try:
                from jnius import autoclass

                activity_class = autoclass("org.kivy.android.PythonActivity")
                intent = activity_class.mActivity.getIntent()
            except (ImportError, AttributeError, RuntimeError):
                return
        try:
            publication_id = intent.getStringExtra("annonce_id")
        except (AttributeError, RuntimeError):
            return
        if not publication_id:
            return
        try:
            intent.removeExtra("annonce_id")
        except (AttributeError, RuntimeError):
            pass
        self.afficher_publications(publication_id)

    def _on_new_intent(self, *args):
        for value in reversed(args):
            if hasattr(value, "getStringExtra"):
                self._consommer_intention_notification(value)
                return
        self._consommer_intention_notification()

    def on_start(self):
        animation = Animation(
            scale=1.12, duration=0.8, t="in_out_quad"
        ) + Animation(
            scale=1, duration=0.8, t="in_out_quad"
        )
        animation.repeat = True
        animation.start(self.root.ids.home_logo)
        blink = Animation(opacity=0.3, duration=0.55) + Animation(
            opacity=1, duration=0.55
        )
        blink.repeat = True
        blink.start(self.root.ids.produits_shortcut)
        blink.start(self.root.ids.infos_shortcut)
        if activity is not None:
            activity.bind(on_new_intent=self._on_new_intent)
        self._consommer_intention_notification()
        Clock.schedule_once(lambda dt: self._verifier_mise_a_jour(), 2)

    def on_resume(self):
        self._consommer_intention_notification()
        self._reprendre_installation()

    def build(self):
        images_dir = Path(__file__).resolve().parent / "images"
        logo = images_dir / "logo.png"
        self.logo_available = logo.is_file()
        if self.logo_available:
            self.logo_image = str(logo)
        owner_photo = images_dir / "proprietaire.jpg"
        self.owner_photo_available = owner_photo.is_file()
        if self.owner_photo_available:
            self.owner_photo = str(owner_photo)
        interface = Builder.load_string(KV)
        self.root = interface
        self.afficher_produits()
        self.afficher_publications()
        return interface


if __name__ == "__main__":
    VenteApp().run()
