
import socket
import threading
import queue
import customtkinter as ctk

HOST = "2.tcp.eu.ngrok.io"
PORT = 29636

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class LogiTalk(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("LogiTalk")
        self.geometry("550x480")
        self.minsize(400, 450)
        self.configure(fg_color="#181818")

        self.username = ""
        self.sock = None
        self.connected = False
        self.connecting = False
        self.running = True

        self.events = queue.Queue()
        self.send_lock = threading.Lock()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.show_login()
        self.after(100, self.process_events)

    # Екран введення ніка
    def show_login(self):
        self.login_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        self.login_frame.pack(fill="both", expand=True)

        content = ctk.CTkFrame(
            self.login_frame,
            fg_color="transparent"
        )
        content.place(
            relx=0.5,
            rely=0.45,
            anchor="center"
        )

        ctk.CTkLabel(
            content,
            text="LogiTalk",
            font=("Arial", 36, "bold")
        ).pack(pady=(0, 10))

        ctk.CTkLabel(
            content,
            text="Введіть нік, щоб приєднатися",
            font=("Arial", 14),
            text_color="#999999"
        ).pack(pady=(0, 25))

        self.name_entry = ctk.CTkEntry(
            content,
            width=280,
            height=45,
            placeholder_text="Ваш нікнейм",
            corner_radius=8
        )
        self.name_entry.pack(pady=5)

        self.name_entry.bind(
            "<Return>",
            lambda event: self.join_chat()
        )

        ctk.CTkButton(
            content,
            text="Приєднатися",
            width=280,
            height=45,
            corner_radius=8,
            command=self.join_chat
        ).pack(pady=15)

        self.login_error = ctk.CTkLabel(
            content,
            text="",
            text_color="#ff7777"
        )
        self.login_error.pack()

        self.name_entry.focus_set()

    # Вхід у чат
    def join_chat(self):
        name = self.name_entry.get().strip()

        name = name.replace("@", "")
        name = name.replace("\n", "")
        name = name.replace("\r", "")

        if not name:
            self.login_error.configure(
                text="Спочатку введіть нік!"
            )
            return

        self.username = name[:25]

        self.login_frame.destroy()
        self.show_chat()
        self.connect_to_server()

    # Інтерфейс чату
    def show_chat(self):
        self.chat_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        self.chat_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=15
        )

        # Заголовок
        header = ctk.CTkFrame(
            self.chat_frame,
            fg_color="transparent"
        )
        header.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            header,
            text="LogiTalk",
            font=("Arial", 25, "bold")
        ).pack(side="left")

        self.status_label = ctk.CTkLabel(
            header,
            text="Підключення...",
            font=("Arial", 12),
            text_color="#aaaaaa"
        )
        self.status_label.pack(side="right")

        # Повідомлення
        self.chat_field = ctk.CTkTextbox(
            self.chat_frame,
            font=("Arial", 14),
            fg_color="#242424",
            corner_radius=10,
            state="disabled",
            wrap="word"
        )
        self.chat_field.pack(
            fill="both",
            expand=True,
            pady=(0, 10)
        )

        # Поле введення
        bottom = ctk.CTkFrame(
            self.chat_frame,
            fg_color="transparent"
        )
        bottom.pack(fill="x")

        self.message_entry = ctk.CTkEntry(
            bottom,
            placeholder_text="Напишіть повідомлення...",
            height=42,
            corner_radius=8
        )
        self.message_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 8)
        )

        self.send_button = ctk.CTkButton(
            bottom,
            text="➤",
            width=48,
            height=42,
            corner_radius=8,
            state="disabled",
            command=self.send_message
        )
        self.send_button.pack(side="right")

        self.message_entry.bind(
            "<Return>",
            lambda event: self.send_message()
        )

        self.add_message(
            f"Ви увійшли як {self.username}"
        )

    # Виведення повідомлень
    def add_message(self, text):
        self.chat_field.configure(state="normal")
        self.chat_field.insert("end", text + "\n")
        self.chat_field.see("end")
        self.chat_field.configure(state="disabled")

    # Підключення до сервера
    def connect_to_server(self):
        if self.connected or self.connecting:
            return

        self.connecting = True

        self.status_label.configure(
            text="Підключення...",
            text_color="#aaaaaa"
        )

        threading.Thread(
            target=self.connection_worker,
            daemon=True
        ).start()

    def connection_worker(self):
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        sock.settimeout(8)

        try:
            sock.connect((HOST, PORT))
            sock.settimeout(None)

            if not self.running:
                return

            self.sock = sock

            hello = (
                f"TEXT@{self.username}@"
                f"[SYSTEM] {self.username} приєднався до чату!\n"
            )
            sock.sendall(hello.encode("utf-8"))

            self.events.put(("connected", None))
            self.receive_messages(sock)

        except Exception as error:
            if self.running:
                self.events.put(("error", str(error)))

        finally:
            try:
                sock.close()
            except OSError:
                pass

            if self.running:
                self.events.put(("disconnected", None))

    # Отримання повідомлень
    def receive_messages(self, sock):
        buffer = b""

        while self.running:
            data = sock.recv(4096)

            if not data:
                break

            buffer += data

            if len(buffer) > 65536:
                break

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)

                text = line.decode(
                    "utf-8",
                    errors="replace"
                )

                parts = text.split("@", 2)

                if len(parts) == 3 and parts[0] == "TEXT":
                    self.events.put((
                        "message",
                        f"{parts[1]}: {parts[2]}"
                    ))

    # Обробка подій
    def process_events(self):
        try:
            while True:
                event, value = self.events.get_nowait()

                if event == "connected":
                    self.connected = True
                    self.connecting = False

                    self.status_label.configure(
                        text="● Онлайн",
                        text_color="#55cc88"
                    )

                    self.send_button.configure(
                        state="normal"
                    )

                    self.add_message(
                        "Підключено до сервера"
                    )

                elif event == "message":
                    self.add_message(value)

                elif event == "error":
                    self.add_message(
                        f"Помилка: {value}"
                    )

                elif event == "disconnected":
                    self.connected = False
                    self.connecting = False
                    self.sock = None

                    self.status_label.configure(
                        text="● Офлайн",
                        text_color="#ff6666"
                    )

                    self.send_button.configure(
                        state="disabled"
                    )

        except queue.Empty:
            pass

        if self.running:
            self.after(100, self.process_events)

    # Надсилання повідомлення
    def send_message(self):
        message = self.message_entry.get().strip()

        if not message or not self.connected:
            return

        message = message.replace("\n", " ")

        data = f"TEXT@{self.username}@{message}\n"

        self.message_entry.delete(0, "end")

        self.add_message(f"Я: {message}")

        threading.Thread(
            target=self.send_data,
            args=(data,),
            daemon=True
        ).start()

    def send_data(self, data):
        try:
            with self.send_lock:
                if self.sock:
                    self.sock.sendall(
                        data.encode("utf-8")
                    )

        except OSError as error:
            self.events.put((
                "error",
                str(error)
            ))

    # Закриття програми
    def on_close(self):
        self.running = False

        if self.sock:
            try:
                self.sock.shutdown(
                    socket.SHUT_RDWR
                )
            except OSError:
                pass

            self.sock.close()

        self.destroy()


if __name__ == "__main__":
    app = LogiTalk()
    app.mainloop()
