import kivy, sys, threading, json, time, os, re, platform, subprocess, sys
kivy.require('1.10.1')
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.properties import ObjectProperty
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.core.window import Window
from data_collection import Scraper
os.chdir(os.path.realpath(sys.path[0]))
#from gui_main_test import Coordinator

class LoginPage(Screen):
    def __init__(self, **kwargs): 
        super(LoginPage, self).__init__(**kwargs)
        Window.bind(on_keyboard=self._on_keyboard)
    def verify_credentials(self):
        """
        Verify if the correct login credentials have been provided.
        Args:
            None
        """
        #note that it is bad practice to hardcode username/password, this is used for rough idea only
        if self.ids["username"].text == "username" and self.ids["password"].text == "password":
            self.ids["successlogin_message"].opacity = 1
            Clock.schedule_once(self.hidemessage, 1.5)
            self.manager.transition.direction = "left"
            self.manager.current = "user_page"
        else:
            self.ids["errorlogin_message"].opacity = 1
            Clock.schedule_once(self.hidemessage, 1.5)
        self.ids["username"].text = ""
        self.ids["password"].text = ""

    def _on_keyboard(self, instance, key, scancode, codepoint, modifiers):
        """
        Function to take in enter input from keyboard.
        """
        if scancode == 40:
            self.verify_credentials()

    def hidemessage(self, placeholder):
        """
        Toggles message on and off.
        Args:
            placeholder: -
        """
        self.ids["successlogin_message"].opacity = 0
        self.ids["errorlogin_message"].opacity = 0
    
    def quit(self):
        """
        Exits upon clicking the quit button.
        Args:
            None
        """
        sys.exit()

class UserPage(Screen):
    def logout(self):
        """
        Logout back to main login page.
        Args:
            None
        """
        self.manager.transition.direction = "right"
        self.manager.current = "login_page"

    def settings(self):
        """
        Go to settings page.
        Args:
            None
        """
        self.manager.transition.direction = "left"
        self.manager.current = "settings_page"

    def reports(self):
        """
        Go to reports page.
        Args:
            None
        """
        self.manager.transition.direction = "left"
        self.manager.current = "reports_page"

    def start_test(self):
        """
        Start running test from main script.
        Args:
            None
        """
        self.manager.transition.direction = "left"
        self.manager.current = "progress_page"
        self.ids["start_button"].text = "View progress"

class ProgressPage(Screen): 
    def __init__(self, **kwargs): 
        super(ProgressPage, self).__init__(**kwargs)
        self.i = 0
        self.state = 0
    def state(self):
        print(self.state)
        if self.state == 0:
            self.track_progress()
        else:
            pass
    def track_progress(self):
        """
        Open up the reports directory to show reports.
        Args:
            None
        """
        if self.i == 0:
            self.pb = self.ids["pb"]
            self.scraper = Scraper()
            self.begin = threading.Thread(target=self.scraper.begin)
            self.begin.daemon = True
            self.begin.start()
            self.updatelabel = threading.Thread(target=self.progresslabel)
            self.updatelabel.daemon = True
            self.updatelabel.start()
            self.i += 1

    def progresslabel(self):
        while True:
            self.pb.task = self.scraper.task
            self.pb.value = self.scraper.value
            self.pb.max = self.scraper.max

    def check(self):
        """
        Check if thread is still running for the active test.
        Args:
            None
        """
        Clock.schedule_interval(self.update, 0.5)

    def update(self, placeholder):
        """
        Update the start button depending on status of thread/test.
        Args:
            placeholder: -
        """
        if self.test.is_alive() == False:
            self.ids["start_button"].disabled = False

    def back(self):
        """
        Back to main menu.
        Args:
            None
        """
        self.manager.transition.direction = "right"
        self.manager.current = "user_page"

class SettingsPage(Screen):
    def read_in_config(self):
        """
        Read in pre-set configuration from file.
        Args:
            None
        """
        with open("./config/gui_main_test_config.json") as configurationfile:
            self.configuration = json.load(configurationfile)
        for configuration_type in self.configuration.keys():
            if self.configuration[configuration_type] == "E":
                self.ids[configuration_type + "_togglebutton"].state = "down"
                self.ids[configuration_type + "_togglebutton"].text = "Enabled"
            elif self.configuration[configuration_type] == "D":
                self.ids[configuration_type + "_togglebutton"].state = "normal"
                self.ids[configuration_type + "_togglebutton"].text = "Disabled"
            else:
                self.ids[configuration_type + "_togglebutton"].state = "normal"
                self.ids[configuration_type + "_togglebutton"].text = "ERROR"
        configurationfile.close()

    def update_button(self, togglebutton):
        """
        Change text on button when enabled/disabled.
        Args:
            None
        """
        if self.ids[togglebutton].state == "down":
            self.ids[togglebutton].text = "Enabled"
        else:
            self.ids[togglebutton].text = "Disabled"

    def save_changes(self):
        """
        Write button state into configuration file to save changes.
        Args:
            None
        """
        newconfigurationfile = open("./config/gui_main_test_config.json", "w", encoding="utf-8")
        newconfiguration = {}
        for configuration_type in self.configuration.keys():
            newconfiguration[configuration_type] = self.ids[configuration_type + "_togglebutton"].text[0]
        json.dump(newconfiguration, newconfigurationfile)
        self.ids["save_message"].opacity = 1
        Clock.schedule_once(self.hidemessage, 1.5)


    def hidemessage(self, placeholder):
        """
        Toggles message on and off.
        Args:
            placeholder: -
        """
        self.ids["save_message"].opacity = 0

    def back(self):
        """
        Back to main menu.
        Args:
            None
        """
        self.manager.transition.direction = "right"
        self.manager.current = "user_page"

class ScreenManagement(ScreenManager):
    pass

kv_file = Builder.load_file('spotify_scraper.kv')

class Spotify_ScraperApp(App):
    def builder(self):
        return kv_file

if __name__ == '__main__':
    Spotify_ScraperApp().run()