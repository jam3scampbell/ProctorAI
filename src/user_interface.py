import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QHBoxLayout, QLineEdit
from PyQt5.QtWidgets import QDialog, QFormLayout, QCheckBox, QSpinBox, QComboBox, QShortcut
from PyQt5.QtGui import QIcon, QFont, QPixmap, QBrush, QPalette
from PyQt5.QtCore import QTime, QTimer, Qt, QProcess
from PyQt5.QtGui import QColor, QTextCursor, QTextCharFormat, QKeySequence
from api_models import *
import json
import os
from utils import find_virtualenv
from dotenv import find_dotenv, load_dotenv

dotenv_file = find_dotenv()
load_dotenv(dotenv_file)

VENV_PATH = os.getenv("PATH_TO_LOCAL_EVN", None)

if not VENV_PATH:
    VENV_PATH = os.path.join(find_virtualenv(".."), "Scripts", "python.exe")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")

        self.layout = QFormLayout(self)

        # model_name flag
        self.model_name_box = QComboBox()
        self.model_name_box.addItems(["claude-3-5-sonnet-20240620","gpt-4o","gemini-1.5-flash","llava:34b","llava"])
        self.layout.addRow("Model", self.model_name_box)

        # tts flag
        self.tts_checkbox = QCheckBox("Enable text-to-speech")
        self.layout.addRow("TTS", self.tts_checkbox)

        # voice flag
        self.voice_combobox = QComboBox()
        self.voice_combobox.addItems(["Adam","Arnold","Emily","Harry","Josh","Patrick"])
        self.layout.addRow("Voice", self.voice_combobox)

        # cli_mode flag
        self.cli_mode_checkbox = QCheckBox("Enable CLI mode")
        self.layout.addRow("CLI Mode", self.cli_mode_checkbox)

        # delay_time flag
        self.delay_time_spinbox = QSpinBox()
        self.delay_time_spinbox.setRange(0, 100000)
        self.layout.addRow("Delay Time", self.delay_time_spinbox)

        # initial_delay flag
        self.initial_delay_spinbox = QSpinBox()
        self.initial_delay_spinbox.setRange(0,100000)
        self.layout.addRow("Initial Delay", self.initial_delay_spinbox)

        # countdown_time flag
        self.countdown_time_spinbox = QSpinBox()
        self.countdown_time_spinbox.setRange(0, 100)
        self.layout.addRow("Countdown Time", self.countdown_time_spinbox)

        # user_name flag
        self.user_name_lineedit = QLineEdit()
        self.user_name_lineedit.setText("Procrastinator")
        self.layout.addRow("User Name", self.user_name_lineedit)

        # print_CoT flag
        self.print_CoT_checkbox = QCheckBox("Show model's chain of thought")
        self.layout.addRow("Print CoT", self.print_CoT_checkbox)

        # two_tier flag
        self.two_tier_checkbox = QCheckBox("Use smaller routing model")
        self.layout.addRow("Two Tier", self.two_tier_checkbox)
        
        # router model
        self.router_model_box = QComboBox()
        self.router_model_box.addItems(["claude-3-5-sonnet-20240620","gpt-4o","gemini-1.5-flash","llava:34b","llava"])
        self.layout.addRow("Router Model", self.router_model_box)

        # OK and Cancel buttons
        self.buttons_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.buttons_layout.addWidget(self.ok_button)
        self.buttons_layout.addWidget(self.cancel_button)

        self.layout.addRow(self.buttons_layout)

    def get_settings(self):
        return {
            "model": self.model_name_box.currentText(),
            "tts": self.tts_checkbox.isChecked(),
            "voice": self.voice_combobox.currentText(),
            "cli_mode": self.cli_mode_checkbox.isChecked(),
            "delay_time": self.delay_time_spinbox.value(),
            "initial_delay": self.initial_delay_spinbox.value(),
            "countdown_time": self.countdown_time_spinbox.value(),
            "user_name": self.user_name_lineedit.text(),
            "print_CoT": self.print_CoT_checkbox.isChecked(),
            "two_tier": self.two_tier_checkbox.isChecked(),
            "router_model": self.router_model_box.currentText()
        }


class ProcrastinationApp(QWidget):
    def __init__(self):
        super().__init__()
        self.cur_dir = os.path.dirname(__file__)
        self.initUI()
        self.start_time = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.process = None
        self.settings = load_settings()
        self.settings_dialog = SettingsDialog(self)
        self.apply_settings()

    def initUI(self):
        self.setWindowTitle('ProctorAI👁️')
        self.setGeometry(100, 100, 800, 600)

        self.layout = QVBoxLayout()
        
        # Stylish prompt label
        pretitle = 'Welcome to ProctorAI👁️'
        title = 'What are you looking to get done today?'
        subtitle_1 = 'What behaviors do you want me to allow?'
        subtitle_2 = 'What behaviors do you want me to call you out on?'
        subtitle_3 = "You've got this"
        subtitle_4 = "And if you dare to procrastinate, I will make you pay the price ;)"
        self.prompt_label = QLabel(self)
        # self.prompt_label.setText(
        self.full_text = f"""
            <span style="font-family: Courier New; font-size: 16px; color: #ffffff; font-weight: bold">
                {pretitle}
            </span>
            <br>
            <span style="font-family: Arial; font-size: 28px; color: #ffffff; font-weight: 900;">
                {title}
            </span>
            <br>
            <br>
            <br>
            <br>
            <br>
            <span style="font-family: Courier New; font-size: 16px; color: #ffffff; font-weight: bold">
                {subtitle_1}
            </span>
            <br>
            <span style="font-family: Courier New; font-size: 16px; color: #ffffff; font-weight: bold">
                {subtitle_2}
            </span>
            <br>
            <span style="font-family: Courier New; font-size: 16px; color: #ffffff; font-weight: bold">
                {subtitle_3}
            </span>
            <br>
            <span style="font-family: Courier New; font-size: 16px; color: #ffffff; font-weight: bold">
                {subtitle_4}
            </span>
        """
        self.current_text = ""
        self.text_index = 0
        self.parts = self.split_text_into_parts(self.full_text)

        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self.update_text)


        self.prompt_input = QTextEdit(self)
        self.prompt_input.setFont(QFont('Courier New', 16))
        self.prompt_input.setLineWrapMode(QTextEdit.WidgetWidth)
        self.prompt_input.setPlaceholderText("Type your task description here...")
        self.prompt_input.setFixedHeight(100)
        self.prompt_input.setStyleSheet("""
            QTextEdit {
                border: 1.5px solid #39FF14;
                border-radius: 20px;
                background-color: black;
                color: white;
            }
        """)
        
        self.start_button = QPushButton('Start (⌘⏎)', self)
        self.start_button.clicked.connect(self.start_task)
        self.start_button.setStyleSheet("""
            QPushButton {
                border: 2px solid #8f8f91;
                border-radius: 25px;
                background-color: #3a3a3c;
                color: white;
                font-size: 18px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #575759;
            }
            QPushButton:pressed {
                background-color: #2e2e30;
            }
        """)
                                        

        # Create a shortcut for Command+Enter
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut.activated.connect(self.start_button.click)
        
        self.settings_button = QPushButton('Settings (⌘S)', self)
        self.settings_button.clicked.connect(self.open_settings)
        # setting geometry of button
        self.settings_button.setGeometry(200, 150, 100, 100)
 

        self.settings_button.setStyleSheet("""
            QPushButton {
                border: 5px solid #4CAF50;
                border-radius: 50px; /* Half of the button's height/width */
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #388E3C;
            }
        """)

        settings_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        settings_shortcut.activated.connect(self.settings_button.click)
        
        prompt_layout = QVBoxLayout()
        button_layout = QHBoxLayout()
        
        prompt_layout.addWidget(self.prompt_label)
        prompt_layout.addWidget(self.prompt_input)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.settings_button)
        
        self.layout.addLayout(prompt_layout)
        self.layout.addLayout(button_layout)
        
        # Running screen elements (hidden initially)
        self.running_label = QLabel('Task in progress: ', self)
        self.running_label.setFont(QFont('Arial', 16, QFont.Bold, italic=True))
        self.running_label.setStyleSheet("color: white;")
        self.running_label.setWordWrap(True)
        self.timer_label = QLabel('Time Elapsed: 00:00:00', self)
        self.timer_label.setFont(QFont('Arial', 16, QFont.Bold, italic=True))
        self.timer_label.setStyleSheet("color: white;")
        self.output_display = QTextEdit(self)
        self.output_display.setReadOnly(True)
        self.output_display.setFont(QFont('Arial', 16, QFont.Bold, italic=True))
        # self.output_display.setStyleSheet("background-color: black; color: white;")
        self.output_display.setStyleSheet("""
            QTextEdit {
                border: 1.5px solid #39FF14;
                border-radius: 20px;
                background-color: black;
                color: white;
            }
        """)
        
        self.stop_button = QPushButton('Stop', self)
        self.stop_button.clicked.connect(self.stop_task)
        
        self.chat_button = QPushButton('Change Task', self)
        self.chat_button.clicked.connect(self.show_chat)
        
        self.back_button = QPushButton('←', self)
        self.back_button.clicked.connect(self.show_stdout)
        
        # Chat elements (hidden initially)
        self.chat_area = QTextEdit(self)
        self.chat_area.setReadOnly(True)
        self.chat_area.setFont(QFont('Courier New', 16))
        self.chat_area.setStyleSheet("""
            QTextEdit {
                background-color: white;
                color: black;
                border: none;
            }
        """)
        
        self.input_area = QLineEdit(self)
        self.input_area.setFont(QFont('Courier New', 16))
        self.input_area.setStyleSheet("""
            QLineEdit {
                background-color: white;
                color: black;
                border: 1px solid #ccc;
                border-radius: 10px;
                padding: 5px;
            }
        """)
        self.input_area.returnPressed.connect(self.send_message)
        
        self.send_button = QPushButton('Send', self)
        self.send_button.clicked.connect(self.send_message)
        
        chat_input_layout = QHBoxLayout()
        chat_input_layout.addWidget(self.input_area)
        chat_input_layout.addWidget(self.send_button)
        
        self.chat_layout = QVBoxLayout()
        self.chat_layout.addWidget(self.back_button)
        self.chat_layout.addWidget(self.chat_area)
        self.chat_layout.addLayout(chat_input_layout)
        
        self.chat_widget = QWidget()
        self.chat_widget.setLayout(self.chat_layout)
        
        self.layout.addWidget(self.running_label)
        self.layout.addWidget(self.timer_label)
        self.layout.addWidget(self.output_display)
        self.layout.addWidget(self.stop_button)
        self.layout.addWidget(self.chat_button)
        self.layout.addWidget(self.chat_widget)
        
        self.running_label.hide()
        self.timer_label.hide()
        self.output_display.hide()
        self.stop_button.hide()
        self.chat_button.hide()
        self.chat_widget.hide()
        
        self.setLayout(self.layout)
        self.show()
        self.typing_timer.start(50)

        
    def start_task(self, task_description=None):
        if not task_description:
            task_description = self.prompt_input.toPlainText()
        if task_description:
            if self.process:
                self.process.terminate()
                self.process.waitForFinished()

            self.running_label.setText(f"Task in progress: {task_description}")

            self.process = QProcess(self)
            arguments = ["-u", os.path.dirname(__file__)+"/main.py"]

            if self.settings["tts"]:
                arguments.append("--tts")
            if self.settings["cli_mode"]:
                arguments.append("--cli_mode")
            if self.settings["print_CoT"]:
                arguments.append("--print_CoT")
            if self.settings["two_tier"]:
                arguments.append("--two_tier")
            arguments.extend([
                "--model", self.settings["model"],
                "--voice", self.settings["voice"],
                "--delay_time", str(self.settings["delay_time"]),
                "--initial_delay", str(self.settings["initial_delay"]),
                "--countdown_time", str(self.settings["countdown_time"]),
                "--user_name", self.settings["user_name"],
                "--router_model", self.settings["router_model"]
            ])

            # HERE PATH TO YOUR VENV PYTHON
            self.process.setProgram(VENV_PATH)
            self.process.setArguments(arguments)
            self.process.setProcessChannelMode(QProcess.MergedChannels)
            self.process.readyReadStandardOutput.connect(self.handle_stdout)
            self.process.start()
            self.process.write(task_description.encode() + b'\n')
            self.process.closeWriteChannel()

            if self.start_time is None:
                self.start_time = QTime.currentTime()
                self.timer.start(1000)  # Update every second

            # Switch to running screen if initial start
            if not self.running_label.isVisible():
                self.prompt_label.hide()
                self.prompt_input.hide()
                self.start_button.hide()
                self.settings_button.hide()
                self.running_label.show()
                self.timer_label.show()
                self.output_display.show()
                self.stop_button.show()
                self.chat_button.show()

        

    def handle_stdout(self):
        output = self.process.readAllStandardOutput().data().decode()
        elapsed_time = QTime(0, 0).addSecs(self.start_time.secsTo(QTime.currentTime())).toString('hh:mm:ss')
        timestamped_output = f"{elapsed_time} - {output}"

        cursor = self.output_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Apply conditional coloring
        format = QTextCharFormat()
        
        if "procrastinating" in output.lower() and api_name_to_colloquial[self.settings["router_model"]] in output:
            format.setForeground(QColor("orange"))
        elif "procrastinating" in output.lower() and api_name_to_colloquial[self.settings["model"]] in output:
            format.setForeground(QColor("red"))
        else:
            format.setForeground(QColor("green"))
        
        cursor.insertText(timestamped_output, format)
        self.output_display.setTextCursor(cursor)
    
        
    def update_timer(self):
        if self.start_time:
            elapsed_time = QTime(0, 0).secsTo(QTime.currentTime()) - QTime(0, 0).secsTo(self.start_time)
            self.timer_label.setText('Time Elapsed: ' + QTime(0, 0).addSecs(elapsed_time).toString('hh:mm:ss'))
        
    def stop_task(self):
        self.timer.stop()
        if self.process:
            self.process.terminate()
            self.process.waitForFinished()
        print("Stopping task")
        self.close()

    def resizeEvent(self, event):
        background_image = QPixmap(os.path.dirname(self.cur_dir)+'/assets/space_2.jpg')  # Replace with your image file
        scaled_background = background_image.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        
        palette = QPalette()
        palette.setBrush(QPalette.Background, QBrush(scaled_background))
        self.setPalette(palette)

    def open_settings(self):
        if self.settings_dialog.exec_():
            self.settings = self.settings_dialog.get_settings()
            save_settings(self.settings)
            print("Settings updated:", self.settings)

    def show_chat(self):
        self.running_label.hide()
        self.timer_label.hide()
        self.output_display.hide()
        self.stop_button.hide()
        self.chat_button.hide()
        self.chat_widget.show()
        
        self.chat_area.append("ProctorAI: What do you plan to get done today?")
        
    def show_stdout(self):
        self.chat_widget.hide()
        self.running_label.show()
        self.timer_label.show()
        self.output_display.show()
        self.stop_button.show()
        self.chat_button.show()
        
    def send_message(self):
        user_message = self.input_area.text()
        if user_message:
            self.chat_area.append(f"You: {user_message}")
            self.input_area.clear()
            model = create_model(self.settings["model"])
            system_prompt = "You are a charismatic productivity assistant chatbot. You give short encouraging responses."
            user_prompt = f"The User just updated their task specification. It is pasted below. Please give a brief response telling them that their task has been updated and a little bit of personalized ecouragement. But no matter what, don't sound cliche.\n\n{user_message}"            
            ai_message = model.call_model(user_prompt, system_prompt=system_prompt)
            self.chat_area.append("ProctorAI: "+ai_message)
            # Restart the backend with the user's message as stdin
            self.start_task(user_message)

    def apply_settings(self):
        self.settings_dialog.model_name_box.setCurrentText(self.settings["model"])
        self.settings_dialog.tts_checkbox.setChecked(self.settings["tts"])
        self.settings_dialog.voice_combobox.setCurrentText(self.settings["voice"])
        self.settings_dialog.cli_mode_checkbox.setChecked(self.settings["cli_mode"])
        self.settings_dialog.delay_time_spinbox.setValue(self.settings["delay_time"])
        self.settings_dialog.initial_delay_spinbox.setValue(self.settings["initial_delay"])
        self.settings_dialog.countdown_time_spinbox.setValue(self.settings["countdown_time"])
        self.settings_dialog.user_name_lineedit.setText(self.settings["user_name"])
        self.settings_dialog.print_CoT_checkbox.setChecked(self.settings["print_CoT"])
        self.settings_dialog.two_tier_checkbox.setChecked(self.settings["two_tier"])
        self.settings_dialog.router_model_box.setCurrentText(self.settings["router_model"])

    def split_text_into_parts(self, text):
        # For quick dynamic typing of the text on the screen without waiting for tags
        parts = []
        temp = ""
        in_tag = False

        for char in text:
            if char == '<':
                if temp:
                    parts.append(('text', temp.strip()))
                    temp = ""
                in_tag = True
                temp += char
            elif char == '>':
                temp += char
                parts.append(('tag', temp))
                temp = ""
                in_tag = False
            else:
                temp += char

        if temp:
            parts.append(('text', temp.strip()))

        return parts
    
    def update_text(self):
        if self.text_index < len(self.parts):
            part_type, part_content = self.parts[self.text_index]
            
            if part_type == 'tag':
                self.current_text += part_content
                self.text_index += 1
            else:  
                if part_content:
                    self.current_text += part_content[0]
                    self.parts[self.text_index] = ('text', part_content[1:])
                else:
                    self.text_index += 1
            
            self.prompt_label.setText(self.current_text)
        else:
            self.typing_timer.stop()



def load_settings():
    settings_file = os.path.dirname(os.path.dirname(__file__)) + "/settings.json"
    if os.path.exists(settings_file):
        with open(settings_file, "r") as file:
            return json.load(file)
    else:
        return {
            "model": "claude-3-5-sonnet-20240620",
            "tts": False,
            "voice": "Patrick",
            "cli_mode": False,
            "delay_time": 0,
            "initial_delay": 0,
            "countdown_time": 15,
            "user_name": "Procrastinator",
            "print_CoT": False,
            "two_tier": False,
            "router_model": "llava"
        }

def save_settings(settings):
    settings_file = os.path.dirname(os.path.dirname(__file__)) + "/settings.json"
    with open(settings_file, "w") as file:
        json.dump(settings, file)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(os.path.dirname(os.path.dirname(__file__))+'/assets/icon_rounded.png'))
    app.setApplicationName('ProctorAI👁️')
    ex = ProcrastinationApp()
    sys.exit(app.exec_())
