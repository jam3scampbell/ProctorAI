import tkinter as tk
from tkinter import messagebox


class ProcrastinationEvent:
    def show_popup(self, ai_message, pledge_message):
        root = tk.Tk()
        app = FocusPopup(root, ai_message, pledge_message)
        root.mainloop()

    def play_countdown(self, count, brief_message="You have 10 seconds to close it."):
        root = tk.Tk()
        root.title(brief_message)

        # Make the window stay on top
        root.attributes('-topmost', True)

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        window_width = 400
        window_height = 100

        position_top = int(screen_height / 2 - window_height / 2)
        position_right = int(screen_width / 2 - window_width / 2)

        root.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')

        label = tk.Label(root, font=('Helvetica', 48), fg='red')
        label.pack(expand=True)

        def countdown(start_count):
            label['text'] = start_count
            if start_count > 0:
                root.after(1000, countdown, start_count - 1)

        countdown(count)
        root.mainloop()


class FocusPopup:
    def __init__(self, master, ai_message, pledge_message):
        self.master = master
        self.master.title("Focus Reminder")
        self.master.attributes('-fullscreen', True)
        self.master.configure(bg='white')

        # AI personalized message at the top with wrapping
        self.ai_message_label = tk.Label(
            master,
            text=ai_message,
            font=("Helvetica", 24),
            bg='white',
            wraplength=self.master.winfo_screenwidth() - 100  # Wrap text to fit the screen width with padding
        )
        self.ai_message_label.pack(pady=50, side=tk.TOP)

        
        # Pledge message and entry at the bottom
        self.bottom_frame = tk.Frame(master, bg='white')
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=50)

        self.label = tk.Label(self.bottom_frame, text="Please type the following to continue working:", font=("Helvetica", 18), bg='white')
        self.label.pack(pady=10)

        self.challenge_text = pledge_message
        self.challenge_label = tk.Label(self.bottom_frame, text=self.challenge_text, font=("Helvetica", 16), bg='white')
        self.challenge_label.pack(pady=10)

        self.entry = tk.Entry(self.bottom_frame, font=("Helvetica", 16), width=50)
        self.entry.pack(pady=10)
        self.entry.bind('<Return>', self.check_input)

        self.result_label = tk.Label(self.bottom_frame, text="", font=("Helvetica", 16), bg='white')
        self.result_label.pack(pady=10)

    def check_input(self, event):
        user_input = self.entry.get()
        if user_input == self.challenge_text:
            self.master.destroy()  # Ends the mainloop
        else:
            self.result_label.config(text="Incorrect input. Please try again.", fg='red')
            self.entry.delete(0, tk.END)



if __name__ == "__main__":
    procrastination_event = ProcrastinationEvent()
    procrastination_event.show_popup("You are procrastinating. Please focus on your work.")
    procrastination_event.play_countdown(10)