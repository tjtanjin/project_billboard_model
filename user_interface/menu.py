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
stop_thread = "1"

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
    def get_state(self):
        """
        Check state of extraction to determine button to show.
        Args:
            None
        """
        with open("./settings/config.json", "r") as file:
            settings = json.load(file)
        if settings["state"] == "0":
            self.ids["start_button"].text = "Start"
        else:
            self.ids["start_button"].text = "View progress"
        print(threading.active_count())

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
    def track_progress(self):
        """
        Open up the reports directory to show reports.
        Args:
            None
        """
        with open("./settings/config.json", "r") as file:
            settings = json.load(file)
        if settings["state"] == "0":
            settings["state"] = "1"
            with open("./settings/config.json", "w+") as updatedfile:
                json.dump(settings, updatedfile)
            self.pb = self.ids["pb"]
            self.pb_label = self.ids["pb_label"]
            self.scraper = Scraper()
            self.begin = threading.Thread(target=self.scraper.begin)
            self.begin.daemon = True
            self.begin.start()
            self.updatelabel = threading.Thread(target=self.progresslabel)
            self.updatelabel.daemon = True
            self.updatelabel.start()

    def progresslabel(self):
        """
        Updates the progress bar continuously.
        Args:
            None
        """
        global stop_thread
        stop_thread = "1"
        while stop_thread == "1":
            time.sleep(0.01)
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

    def stop_scrape(self):
        """
        Aborts the task and update the state upon stop button pressed.
        Args:
            None
        """
        global stop_thread
        stop_thread = "0"
        with open("./settings/config.json", "r") as file:
            settings = json.load(file)
            settings["state"] = "0"
        with open("./settings/config.json", "w+") as updatedfile:
            settings = json.dump(settings, updatedfile)
        self.begin.join()
        self.pb_label.text = "Task aborted."
        self.manager.transition.direction = "right"
        self.manager.current = "user_page"

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
        pass

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