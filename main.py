import webbrowser
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivymd.app import MDApp
from kivymd.uix.navigationbar import (
    MDNavigationBar,
    MDNavigationItem,
    MDNavigationItemIcon,
    MDNavigationItemLabel,
)

from database import FirebaseError, obtenir_produits, obtenir_publications, image_locale

from kivy.uix.popup import Popup
from kivy.uix.label import Label as KivyLabel

try:
    from android import activity
except ImportError:
    activity = None


class BaseNavigationItem(MDNavigationItem):
    icon = StringProperty()
    text = StringProperty()
    screen_name = StringProperty()


KV = """
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
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "30dp"
                    spacing: "20dp"
                    MDLabel:
                        text: "Bienvenue !"
                        halign: "center"
                        font_size: "30sp"
                        bold: True
                    MDLabel:
                        text: "Découvrez nos produits et nos informations."
                        halign: "center"
                        font_size: "18sp"

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
                MDBoxLayout:
                    orientation: "vertical"
                    padding: "30dp"
                    spacing: "20dp"
                    MDLabel:
                        text: "À PROPOS"
                        halign: "center"
                        font_size: "30sp"
                        bold: True
                    MDLabel:
                        text: "Informations sur notre entreprise."
                        halign: "center"
                        font_size: "18sp"

        MDNavigationBar:
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._database_executor = ThreadPoolExecutor(max_workers=3)
        self._publication_widgets = {}

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
        numero = "22890000000"
        message = "Bonjour, je souhaite commander {} au prix de {}.".format(
            produit, prix
        )
        webbrowser.open("https://wa.me/{}?text={}".format(numero, quote(message)))

    def on_switch_tabs(self, bar, item, item_icon, item_text):
        self.root.ids.screen_manager.current = item.screen_name

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
        if activity is not None:
            activity.bind(on_new_intent=self._on_new_intent)
        self._consommer_intention_notification()

    def on_resume(self):
        self._consommer_intention_notification()

    def build(self):
        interface = Builder.load_string(KV)
        self.root = interface
        self.afficher_produits()
        self.afficher_publications()
        return interface


if __name__ == "__main__":
    VenteApp().run()
