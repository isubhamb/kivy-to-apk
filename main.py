import mysql.connector
from mysql.connector import Error
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.list import OneLineRightIconListItem, IconRightWidget
from kivy.clock import Clock
import threading
import socket

# Kivy GUI Layout
KV = '''
ScreenManager:
    SplashScreen:
    LoginScreen:
    DashboardScreen:

<SplashScreen>:
    name: 'splash'
    FloatLayout:  # Use FloatLayout to position widgets freely
        Image:
            source: 'image.png'  # Your custom loading image
            allow_stretch: True
            size_hint: 1, 1  # Make the image fill the entire screen

        MDSpinner:
            size_hint: None, None
            size: dp(46), dp(46)
            pos_hint: {'center_x': .5, 'center_y': .5}  # Center the spinner over the image
            active: True

<LoginScreen>:
    name: 'login'
    MDTextField:
        id: pin_input
        hint_text: "Enter PIN"
        helper_text: "Please enter your 4-digit PIN"
        helper_text_mode: "on_focus"
        password: True
        max_text_length: 4
        pos_hint: {"center_x": 0.5, "center_y": 0.6}
        size_hint_x: None
        width: 200

    MDRaisedButton:
        text: "Login"
        pos_hint: {"center_x": 0.5, "center_y": 0.5}
        md_bg_color: app.theme_cls.primary_color
        text_color: 1, 1, 1, 1
        on_release: app.validate_pin()

    MDLabel:
        id: error_label
        text: ""
        color: 1, 0, 0, 1  # Red color for error text
        halign: "center"
        pos_hint: {"center_x": 0.5, "center_y": 0.4}

<DashboardScreen>:
    name: 'dashboard'
    BoxLayout:
        orientation: 'vertical'
        padding: 10
        spacing: 10

        MDTextField:
            id: app_name
            hint_text: "App Name"
            size_hint_x: 0.8
            pos_hint: {"center_x": 0.5}

        MDTextField:
            id: credentials
            hint_text: "Credentials"
            size_hint_x: 0.8
            pos_hint: {"center_x": 0.5}

        MDRaisedButton:
            id: add_button
            text: "Add"
            pos_hint: {"center_x": 0.5}
            md_bg_color: app.theme_cls.primary_color
            text_color: 1, 1, 1, 1
            on_release: app.add_credential()

        ScrollView:
            MDList:
                id: credentials_list
'''

class SplashScreen(Screen):
    def on_enter(self):
        # This method is called when the splash screen is entered.
        # Schedule the transition to the login screen after 2 seconds.
        Clock.schedule_once(self.go_to_login, 2)

    def go_to_login(self, *args):
        # Change the screen to 'login'
        self.manager.current = 'login'

class LoginScreen(Screen):
    pass

class DashboardScreen(Screen):
    pass

class MyApp(MDApp):
    db_connection_active = False
    internet_connected = False  # Tracks if the internet is currently connected
    dashboard_connected = False  # Tracks internet connection specifically in the dashboard

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connection_thread = threading.Thread(target=self.monitor_internet_connection, daemon=True)

    def connect_to_db(self):
        try:
            # Attempt to connect to the MySQL database
            self.db_connection = mysql.connector.connect(
                host="",
                user="",
                password="",
                database="",
                port="",
            )
            # If the connection is successful, set the flag to True
            if self.db_connection.is_connected():
                self.db_connection_active = True
        except Error:
            self.show_connection_error("Unable to connect to the database. Check network or permissions.")
            self.db_connection_active = False

    def build(self):
        # Set theme to dark and primary color to blue
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        
        # Load the GUI
        screen_manager = Builder.load_string(KV)
        
        # Attempt to connect to the database
        self.connect_to_db()
        
        # Start the internet connection monitoring thread
        self.connection_thread.start()

        return screen_manager

    def validate_pin(self):
        if not self.db_connection_active:
            self.show_connection_error("Database connection is required for login.")
            return

        entered_pin = self.root.get_screen('login').ids.pin_input.text
        stored_pin = self.get_stored_pin()
        
        if entered_pin == stored_pin:
            self.root.current = 'dashboard'
            self.load_credentials()
        else:
            self.show_error_dialog()

    def get_stored_pin(self):
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT pin FROM secret LIMIT 1")
            result = cursor.fetchone()
            return result[0] if result else None
        except Error:
            self.show_connection_error("Failed to retrieve PIN. Check connection.")

    def show_error_dialog(self):
        if not hasattr(self, 'dialog'):
            self.dialog = MDDialog(
                text="Incorrect PIN! Please try again.",
                buttons=[
                    MDRaisedButton(
                        text="OK",
                        md_bg_color=self.theme_cls.primary_color,
                        text_color=(1, 1, 1, 1),
                        on_release=lambda x: self.dialog.dismiss()
                    )
                ],
            )
        self.dialog.open()

    def show_connection_error(self, message):
        login_screen = self.root.get_screen('login')
        login_screen.ids.error_label.text = message

    def monitor_internet_connection(self):
        while True:
            connected = self.check_internet_connection()
            if connected != self.internet_connected:
                self.internet_connected = connected
                Clock.schedule_once(self.on_connection_change, 0)
            threading.Event().wait(5)

    def check_internet_connection(self):
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True
        except OSError:
            return False

    def on_connection_change(self, *args):
        if self.internet_connected:
            self.show_connection_error("")
            self.connect_to_db()
            self.dashboard_connected = True
            self.enable_dashboard_inputs()
        else:
            self.show_connection_error("No internet connection. Please check your network.")
            self.db_connection_active = False
            self.dashboard_connected = False
            self.disable_dashboard_inputs()

    def disable_dashboard_inputs(self):
        dashboard_screen = self.root.get_screen('dashboard')
        dashboard_screen.ids.app_name.disabled = True
        dashboard_screen.ids.credentials.disabled = True
        dashboard_screen.ids.add_button.disabled = True  # Disable the Add button
        for item in dashboard_screen.ids.credentials_list.children:
            item.disabled = True

    def enable_dashboard_inputs(self):
        dashboard_screen = self.root.get_screen('dashboard')
        dashboard_screen.ids.app_name.disabled = False
        dashboard_screen.ids.credentials.disabled = False
        dashboard_screen.ids.add_button.disabled = False  # Enable the Add button
        for item in dashboard_screen.ids.credentials_list.children:
            item.disabled = False

    def add_credential(self):
        if not self.dashboard_connected:
            return

        app_name = self.root.get_screen('dashboard').ids.app_name.text
        credentials = self.root.get_screen('dashboard').ids.credentials.text

        if not app_name or not credentials:
            return

        try:
            cursor = self.db_connection.cursor()
            cursor.execute("INSERT INTO credentials (app_name, credentials) VALUES (%s, %s)", (app_name, credentials))
            self.db_connection.commit()
            self.load_credentials()
        except Error:
            self.show_connection_error("Failed to add credential. Check connection.")

    def load_credentials(self):
        self.root.get_screen('dashboard').ids.credentials_list.clear_widgets()
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT id, app_name FROM credentials")
            for cred_id, app_name in cursor.fetchall():
                item = OneLineRightIconListItem(text=app_name)
                delete_icon = IconRightWidget(icon="delete", on_release=lambda x, id=cred_id: self.delete_credential(id))
                item.add_widget(delete_icon)
                item.bind(on_release=lambda x, id=cred_id: self.show_credential_details(id))
                self.root.get_screen('dashboard').ids.credentials_list.add_widget(item)
        except Error:
            self.show_connection_error("Failed to load credentials. Check connection.")

    def delete_credential(self, cred_id):
        if not self.dashboard_connected:
            return

        try:
            cursor = self.db_connection.cursor()
            cursor.execute("DELETE FROM credentials WHERE id = %s", (cred_id,))
            self.db_connection.commit()
            self.load_credentials()
        except Error:
            self.show_connection_error("Failed to delete credential. Check connection.")

    def show_credential_details(self, cred_id):
        try:
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT app_name, credentials FROM credentials WHERE id = %s", (cred_id,))
            result = cursor.fetchone()
            if result:
                dialog = MDDialog(
                    title=result[0],
                    text=result[1],
                    buttons=[
                        MDRaisedButton(
                            text="OK",
                            md_bg_color=self.theme_cls.primary_color,
                            text_color=(1, 1, 1, 1),
                            on_release=lambda x: dialog.dismiss()
                        )
                    ]
                )
                dialog.open()
        except Error:
            self.show_connection_error("Failed to retrieve credential details. Check connection.")

if __name__ == '__main__':
    MyApp().run()
