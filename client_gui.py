"""Interface gráfica do cliente. A comunicação é delegada a ChatClient."""

import datetime
import os
from tkinter import *
from tkinter import scrolledtext, messagebox, filedialog, simpledialog


class ChatClientGUI:
    """Janela e interações visuais do cliente de chat."""

    def __init__(self):
        self.window = None
        self.chat_text = None
        self.message_entry = None
        self.users_listbox = None
        self.status_label = None
        self.send_button = None
        self.file_button = None
        self.private_button = None
        self.refresh_button = None
        self.create_group_button = None
        self.invite_group_button = None
        self.send_group_message_button = None
        self.group_history_button = None
        self.controller = None
        self.running = True
        self.online_users = []
        self.create_gui()

    def set_controller(self, controller):
        self.controller = controller

    def create_gui(self):
        """Cria toda a interface gráfica"""
        self.window = Tk()
        self.window.title("💬 Chat Client")
        self.window.geometry("900x700")
        self.window.configure(bg="#2c3e50")
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Título principal
        title_frame = Frame(self.window, bg="#2c3e50")
        title_frame.pack(pady=10, fill="x")
        
        title = Label(title_frame, text="💬 CLIENTE DE CHAT", 
                     font=("Arial", 18, "bold"), 
                     bg="#2c3e50", fg="#ecf0f1")
        title.pack()
        
        # Status de conexão
        self.status_label = Label(title_frame, text="🔴 Desconectado", 
                                 font=("Arial", 12), 
                                 bg="#2c3e50", fg="#e74c3c")
        self.status_label.pack(pady=5)
        
        # Frame principal (dividido em duas colunas)
        main_frame = Frame(self.window, bg="#2c3e50")
        main_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # Coluna esquerda - Chat
        chat_frame = Frame(main_frame, bg="#34495e", relief="raised", bd=2)
        chat_frame.pack(side=LEFT, fill="both", expand=True, padx=(0, 10))
        
        # Área de chat
        chat_label = Label(chat_frame, text="💬 CHAT", 
                          font=("Arial", 12, "bold"), 
                          bg="#34495e", fg="#ecf0f1")
        chat_label.pack(pady=10)
        
        self.chat_text = scrolledtext.ScrolledText(
            chat_frame, 
            height=20, 
            width=50,
            font=("Consolas", 10),
            bg="#1e1e1e", 
            fg="#ecf0f1",
            insertbackground="#ecf0f1",
            selectbackground="#404040",
            wrap=WORD,
            state=DISABLED
        )
        self.chat_text.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Frame para entrada de mensagem
        input_frame = Frame(chat_frame, bg="#34495e")
        input_frame.pack(pady=10, padx=10, fill="x")
        
        self.message_entry = Entry(input_frame, 
                                  font=("Arial", 11),
                                  bg="#ecf0f1", 
                                  fg="#2c3e50",
                                  relief="flat")
        self.message_entry.pack(side=LEFT, fill="x", expand=True, padx=(0, 5))
        self.message_entry.bind("<Return>", self.send_message_event)
        self.message_entry.bind("<Control-Return>", self.send_private_message_event)
        
        # Botões de envio
        buttons_frame = Frame(input_frame, bg="#34495e")
        buttons_frame.pack(side=RIGHT)
        
        self.send_button = Button(buttons_frame, text="📤", 
                                 command=self.send_message,
                                 font=("Arial", 10, "bold"),
                                 bg="#27ae60", fg="white",
                                 relief="flat", width=4,
                                 state=DISABLED)
        self.send_button.pack(side=LEFT, padx=2)
        
        self.file_button = Button(buttons_frame, text="📎", 
                                 command=self.send_file,
                                 font=("Arial", 10, "bold"),
                                 bg="#3498db", fg="white",
                                 relief="flat", width=4,
                                 state=DISABLED)
        self.file_button.pack(side=LEFT, padx=2)
        
        self.private_button = Button(buttons_frame, text="🔒", 
                                    command=self.send_private_message,
                                    font=("Arial", 10, "bold"),
                                    bg="#9b59b6", fg="white",
                                    relief="flat", width=4,
                                    state=DISABLED)
        self.private_button.pack(side=LEFT, padx=2)
        
        # Coluna direita - Usuários online
        users_frame = Frame(main_frame, bg="#34495e", relief="raised", bd=2)
        users_frame.pack(side=RIGHT, fill="y", padx=(10, 0))
        
        users_label = Label(users_frame, text="👥 USUÁRIOS ONLINE", 
                           font=("Arial", 12, "bold"), 
                           bg="#34495e", fg="#ecf0f1")
        users_label.pack(pady=10)
        
        # Lista de usuários
        listbox_frame = Frame(users_frame, bg="#34495e")
        listbox_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.users_listbox = Listbox(listbox_frame,
                                   font=("Arial", 10),
                                   bg="#1e1e1e",
                                   fg="#ecf0f1",
                                   selectbackground="#3498db",
                                   relief="flat",
                                   width=25,
                                   height=15)
        self.users_listbox.pack(fill="both", expand=True)
        self.users_listbox.bind("<Double-Button-1>", self.on_user_double_click)
        
        # Botão para atualizar lista
        self.refresh_button = Button(users_frame, text="🔄 Atualizar", 
                                   command=self.refresh_users,
                                   font=("Arial", 10, "bold"),
                                   bg="#f79c0b", fg="white",
                                   relief="flat",
                                   state=DISABLED)
        self.refresh_button.pack(pady=10)

        # Botão para criar grupo
        self.create_group_button = Button(users_frame, text="👥 Criar grupo",
                                    command=self.create_group,
                                    font=("Arial", 10, "bold"),
                                    bg="#d66e91",
                                    fg="white",
                                    relief="flat",
                                    state=DISABLED
                                    )
        self.create_group_button.pack(pady=5)

         # Botão para convites
        self.invite_group_button = Button(users_frame, text="✉️ Convidar para grupo",
                                    command=self.invite_to_group,
                                    font=("Arial", 10, "bold"),
                                    bg="#185b64",
                                    fg="white",
                                    relief="flat",
                                    state=DISABLED
                                    )
        self.invite_group_button.pack(pady=5)

        self.send_group_message_button = Button(users_frame, text="💬 Mensagem para grupo",
                                    command=self.send_group_message,
                                    font=("Arial", 10, "bold"),
                                    bg="#680717",
                                    fg="white",
                                    relief="flat",
                                    state=DISABLED
                    )
        self.send_group_message_button.pack(pady=5)

        self.group_history_button = Button(users_frame, text="📜 Ver histórico",
                                    command=self.view_group_history,
                                    font=("Arial", 10, "bold"),
                                    bg="#305770",
                                    fg="white",
                                    relief="flat",
                                    state=DISABLED
)
        self.group_history_button.pack(pady=5)
    
        # Informações na parte inferior
        info_frame = Frame(self.window, bg="#2c3e50")
        info_frame.pack(pady=10, fill="x")
        
        info_text = Label(info_frame, 
                         text="💡 Dicas: Enter = msg global | Ctrl+Enter = msg privada | Duplo-click = msg privada para usuário",
                         font=("Arial", 9),
                         bg="#2c3e50", fg="#95a5a6")
        info_text.pack()
        

    def log_message(self, message, color="#ecf0f1"):
        """Adiciona mensagem ao chat com timestamp e cor"""
        if not self.running:
            return
            
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        def _update():
            try:
                self.chat_text.config(state=NORMAL)
                self.chat_text.insert(END, formatted_message)
                self.chat_text.tag_add("color", "end-2l", "end-1l")
                self.chat_text.tag_config("color", foreground=color)
                self.chat_text.see(END)
                self.chat_text.config(state=DISABLED)
            except:
                pass
        
        self.window.after(0, _update)
        
    def update_status(self, status, color="#e74c3c"):
        """Atualiza o status de conexão"""
        def _update():
            try:
                self.status_label.config(text=status, fg=color)
            except:
                pass
        
        self.window.after(0, _update)
        
    def enable_controls(self, enabled=True):
        """Habilita/desabilita controles da interface"""
        state = NORMAL if enabled else DISABLED
        
        def _update():
            try:
                self.send_button.config(state=state)
                self.file_button.config(state=state)
                self.private_button.config(state=state)
                self.refresh_button.config(state=state)
                self.message_entry.config(state=state)
                self.create_group_button.config(state=state)
                self.invite_group_button.config(state=state)
                self.send_group_message_button.config(state=state)
                self.group_history_button.config(state=state)
            except:
                pass
        
        self.window.after(0, _update)
        
    def update_users_list(self, users):
        """Atualiza a lista de usuários online"""
        self.online_users = users
        
        def _update():
            try:
                self.users_listbox.delete(0, END)
                for user in users:
                    name = user.get('name', 'Desconhecido')
                    self.users_listbox.insert(END, f"👤 {name}")
            except:
                pass
        
        self.window.after(0, _update)
        
    def get_selected_user(self):
        """Retorna o usuário selecionado na lista (sem o emoji)"""
        try:
            selection = self.users_listbox.curselection()
            if selection:
                user_text = self.users_listbox.get(selection[0])
                return user_text.replace("👤 ", "")
        except:
            pass
        return None
        

    def _is_connected(self):
        return self.controller is not None and self.controller.name_registered

    def on_user_double_click(self, event):
        user = self.get_selected_user()
        if user:
            self.send_private_message(target_user=user)

    def send_message_event(self, event):
        self.send_message()
        return "break"

    def send_private_message_event(self, event):
        self.send_private_message()
        return "break"

    def send_message(self):
        if not self._is_connected():
            messagebox.showwarning("Aviso", "Configure seu nome primeiro!", parent=self.window)
            return
        message = self.message_entry.get().strip()
        if not message:
            return
        if self.controller.send_text(message, "4all"):
            self.message_entry.delete(0, END)
            self.log_message(f"[Você → todos]: {message}", "#27ae60")

    def send_private_message(self, target_user=None):
        if not self._is_connected():
            messagebox.showwarning("Aviso", "Configure seu nome primeiro!", parent=self.window)
            return
        if target_user is None:
            target_user = self.get_selected_user()
        if not target_user:
            target_user = simpledialog.askstring("Mensagem Privada", "Digite o nome do destinatário:", parent=self.window)
        if not target_user:
            return
        message = simpledialog.askstring("Mensagem Privada", f"Mensagem para {target_user}:", parent=self.window)
        if message and self.controller.send_text(message, target_user):
            self.log_message(f"[Você → {target_user}]: {message}", "#9b59b6")

    def send_group_message(self):
        if not self._is_connected():
            messagebox.showwarning("Aviso", "Configure seu nome primeiro!", parent=self.window)
            return
        group_name = simpledialog.askstring("Mensagem para grupo", "Digite o nome do grupo:", parent=self.window)
        if not group_name or not group_name.strip():
            return
        group_name = group_name.strip()
        message = simpledialog.askstring("Mensagem para grupo", f"Mensagem para o grupo {group_name}:", parent=self.window)
        if message and self.controller.send_text(message, f"group:{group_name}"):
            self.log_message(f"[Você → Grupo {group_name}]: {message}", "#b40e45")

    def view_group_history(self):
        if not self._is_connected():
            messagebox.showwarning("Aviso", "Configure seu nome primeiro!", parent=self.window)
            return
        group_name = simpledialog.askstring("Histórico do grupo", "Digite o nome do grupo:", parent=self.window)
        if group_name and group_name.strip():
            self.controller.request_group_history(group_name.strip())

    def send_file(self):
        if not self._is_connected():
            messagebox.showwarning("Aviso", "Configure seu nome primeiro!", parent=self.window)
            return
        filepath = filedialog.askopenfilename(
            title="Selecione o arquivo para enviar",
            filetypes=[
                ("Todos os arquivos", "*.*"),
                ("Documentos de texto", "*.txt *.doc *.docx *.pdf"),
                ("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("Arquivos de código", "*.py *.js *.html *.css *.json"),
            ],
        )
        if not filepath or not os.path.isfile(filepath):
            return
        size = os.path.getsize(filepath)
        if size > 10 * 1024 * 1024 and not messagebox.askyesno(
            "Arquivo Grande",
            "Arquivo muito grande (" + f"{size / 1024 / 1024:.1f}MB)." + chr(10) +
            "Máximo recomendado: 10MB" + chr(10) + "Continuar mesmo assim?",
            parent=self.window,
        ):
            return
        choice = messagebox.askyesnocancel(
            "Destino do Arquivo", "Enviar para todos? (Não = mensagem privada)", parent=self.window
        )
        if choice is None:
            return
        destination = "4all" if choice else self.get_selected_user()
        if destination is None:
            destination = simpledialog.askstring("Arquivo Privado", "Digite o nome do destinatário:", parent=self.window)
        if destination and self.controller.send_file(filepath, destination):
            label = "todos" if destination == "4all" else destination
            self.log_message(f"[Você → {label}]: 📎 {os.path.basename(filepath)} ({size / 1024:.1f}KB)", "#3498db")

    def create_group(self):
        if not self._is_connected():
            messagebox.showwarning("Aviso", "Configure seu nome primeiro!", parent=self.window)
            return
        group_name = simpledialog.askstring("Criar grupo", "Digite o nome do grupo:", parent=self.window)
        if group_name and group_name.strip():
            self.controller.create_group(group_name.strip())

    def invite_to_group(self):
        if not self._is_connected():
            messagebox.showwarning("Aviso", "Configure seu nome primeiro!", parent=self.window)
            return

        group_name = simpledialog.askstring(
            "Convidar para grupo",
            "Digite o nome do grupo:",
            parent=self.window
        )

        if not group_name or not group_name.strip():
            return

        target_names = simpledialog.askstring(
            "Convidar para grupo",
            "Digite os nomes dos usuários separados por vírgula (máximo 5):",
            parent=self.window
        )

        if not target_names or not target_names.strip():
            return

        target_names = [
            name.strip()
            for name in target_names.split(",")
            if name.strip()
        ]

        if len(target_names) > 5:
            messagebox.showwarning(
                "Limite de convites",
                "Você pode convidar no máximo 5 pessoas por vez.",
                parent=self.window
            )
            return

        self.controller.invite_to_group(group_name.strip(), target_names)

    def ask_group_invite(self, group_name, invitation_text):
        self.log_message(invitation_text, "#b40e45")
        accepted = messagebox.askyesno(
            "Convite para grupo",
            f"{invitation_text}" + chr(10) + chr(10) + "Deseja aceitar o convite?",
            parent=self.window,
        )
        self.controller.respond_group_invite(group_name, accepted)

    def refresh_users(self):
        if self._is_connected():
            self.controller.refresh_users()

    def process_file_offer(self, sender, filename, b64data, file_size):
        accepted = messagebox.askyesnocancel(
            "Arquivo Recebido",
            f"📎 Arquivo recebido de {sender}" + chr(10) + f"📄 Nome: {filename}" + chr(10) +
            f"📊 Tamanho: {file_size / 1024:.1f}KB" + chr(10) + chr(10) + "Deseja baixar o arquivo?",
            parent=self.window,
        )
        if accepted:
            saved_path = self.controller.save_received_file(filename, b64data)
            if saved_path:
                size = os.path.getsize(saved_path)
                self.log_message(f"✅ Arquivo baixado: {os.path.basename(saved_path)} ({size / 1024:.1f}KB)", "#27ae60")
                messagebox.showinfo("Sucesso", "Arquivo salvo em:" + chr(10) + saved_path, parent=self.window)
        else:
            self.log_message(f"📎 Arquivo de {sender} ignorado: {filename}", "#95a5a6")

    def request_name(self):
        if self.controller is None or not self.controller.running or self.controller.name_registered:
            return
        name = simpledialog.askstring("Bem-vindo", "Digite seu nome para entrar no chat:", parent=self.window)
        if not name:
            if messagebox.askyesno("Sair", "Deseja sair do chat?", parent=self.window):
                self.on_closing()
            else:
                self.window.after(250, self.request_name)
            return
        self.controller.register_name(name)

    def request_new_name(self):
        if self.controller is None or not self.controller.running:
            return
        name = simpledialog.askstring(
            "Nome Duplicado", "Este nome já está em uso." + chr(10) + "Digite um novo nome:", parent=self.window
        )
        if name:
            self.controller.register_name(name)
        else:
            self.window.after(250, self.request_new_name)

    def ask_server_ip(self):
        return simpledialog.askstring(
            "Servidor",
            "Servidor não encontrado automaticamente." + chr(10) + "Digite o IP do servidor:",
            parent=self.window,
        )

    def show_error(self, title, text):
        messagebox.showerror(title, text, parent=self.window)

    def show_warning(self, title, text):
        messagebox.showwarning(title, text, parent=self.window)

    def on_closing(self):
        if not self.running:
            return
        self.running = False
        if self.controller is not None:
            self.controller.close_connection()
        self.window.quit()
        self.window.destroy()

    def run(self):
        self.window.mainloop()
