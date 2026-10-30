#client.py

import socket
import threading
import base64
import os
import json
import sys
import platform
import time
from tkinter import *
from tkinter import scrolledtext, messagebox, filedialog, simpledialog
from tkinter import ttk
import datetime

def discover_server(timeout=5):
    """
    Descobre automaticamente o servidor de chat na rede local
    - Envia broadcast UDP na porta 5051 com mensagem "CHAT_DISCOVER"
    - Aguarda resposta "CHAT_SERVER" do servidor
    - Retorna o IP do servidor encontrado ou None
    """
    print("🔍 Procurando servidor na rede local...")
    
    # Criar socket UDP para broadcast
    discover_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    discover_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    discover_socket.settimeout(timeout)
    
    try:
        # Enviar mensagem de descoberta
        discover_socket.sendto(b"CHAT_DISCOVER", ('<broadcast>', 5051))
        
        # Aguardar resposta do servidor
        data, addr = discover_socket.recvfrom(1024)
        if data == b"CHAT_SERVER":
            server_ip = addr[0]
            print(f"✅ Servidor encontrado: {server_ip}")
            return server_ip
    except socket.timeout:
        print("❌ Nenhum servidor encontrado automaticamente.")
    except Exception as e:
        print(f"❌ Erro na descoberta: {e}")
    finally:
        discover_socket.close()
    
    return None

class ChatClientGUI:
    """
    Classe principal da interface gráfica do cliente de chat
    """
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
        
        # Controles de estado
        self.running = True
        self.name_registered = False
        self.waiting_for_name = False
        self.current_user = ""
        self.online_users = []
        
        # Dados de arquivo pendente
        self.waiting_for_file_decision = False
        self.pending_file_data = None
        
        # Socket do cliente
        self.client = None
        
        # Inicializar GUI
        self.create_gui()
        
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
        
    def on_user_double_click(self, event):
        """Evento de duplo-click em usuário para mensagem privada"""
        user = self.get_selected_user()
        if user:
            self.send_private_message(target_user=user)
            
    def send_message_event(self, event):
        """Evento de Enter para enviar mensagem"""
        self.send_message()
        
    def send_private_message_event(self, event):
        """Evento de Ctrl+Enter para mensagem privada"""
        self.send_private_message()
        
    def send_message(self):
        """Envia mensagem global"""
        if not self.name_registered:
            messagebox.showwarning("Aviso", "Configure seu nome primeiro!")
            return
            
        message = self.message_entry.get().strip()
        if not message:
            return
            
        try:
            message_formatted = {"type": "msg", "control": "4all", "message": message}
            self.client.send(json.dumps(message_formatted).encode('utf-8'))
            self.message_entry.delete(0, END)
            self.log_message(f"[Você → todos]: {message}", "#27ae60")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao enviar mensagem: {e}")
            
    def send_private_message(self, target_user=None):
        """Envia mensagem privada"""
        if not self.name_registered:
            messagebox.showwarning("Aviso", "Configure seu nome primeiro!")
            return
            
        # Determinar destinatário
        if target_user is None:
            target_user = self.get_selected_user()
            
        if target_user is None:
            # Solicitar nome do usuário
            target_user = simpledialog.askstring("Mensagem Privada", 
                                               "Digite o nome do destinatário:")
            if not target_user:
                return
                
        # Solicitar mensagem
        message = simpledialog.askstring("Mensagem Privada", 
                                       f"Mensagem para {target_user}:")
        if not message:
            return
            
        try:
            message_formatted = {"type": "msg", "control": target_user, "message": message}
            self.client.send(json.dumps(message_formatted).encode('utf-8'))
            self.log_message(f"[Você → {target_user}]: {message}", "#9b59b6")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao enviar mensagem privada: {e}")

    def send_group_message(self):
        """Envia mensagem para um grupo."""
        
        if not self.name_registered:
            messagebox.showwarning(
                "Aviso",
                "Configure seu nome primeiro!"
            )
            return

        group_name = simpledialog.askstring(
            "Mensagem para grupo",
            "Digite o nome do grupo:",
            parent=self.window
        )

        if not group_name or not group_name.strip():
            return

        group_name = group_name.strip()

        message = simpledialog.askstring(
            "Mensagem para grupo",
            f"Mensagem para o grupo {group_name}:",
            parent=self.window
        )

        if not message or not message.strip():
            return

        try:
            message_formatted = {
                "type": "msg",
                "control": f"group:{group_name}",
                "message": message
            }

            self.client.send(
                json.dumps(message_formatted).encode("utf-8")
            )

            self.log_message(
                f"[Você → Grupo {group_name}]: {message}",
                "#b40e45"
            )

        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Erro ao enviar mensagem para o grupo: {e}"
            )

    def view_group_history(self):
        """Solicita o histórico de mensagens de um grupo."""

        if not self.name_registered:
            messagebox.showwarning(
                "Aviso",
                "Configure seu nome primeiro!"
            )
            return

        group_name = simpledialog.askstring(
            "Histórico do grupo",
            "Digite o nome do grupo:",
            parent=self.window
        )

        if not group_name or not group_name.strip():
            return

        group_name = group_name.strip()

        try:
            message_formatted = {
                "type": "group_history",
                "control": group_name,
                "message": ""
            }

            self.client.send(
                json.dumps(message_formatted).encode("utf-8")
            )

        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Erro ao solicitar histórico: {e}"
            )
            
    def send_file(self):
        """Envia arquivo"""
        if not self.name_registered:
            messagebox.showwarning("Aviso", "Configure seu nome primeiro!")
            return
            
        # Selecionar arquivo
        filepath = filedialog.askopenfilename(
            title="Selecione o arquivo para enviar",
            filetypes=[
                ("Todos os arquivos", "*.*"),
                ("Documentos de texto", "*.txt *.doc *.docx *.pdf"),
                ("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("Arquivos de código", "*.py *.js *.html *.css *.json")
            ]
        )
        
        if not filepath or not os.path.isfile(filepath):
            return
            
        # Verificar tamanho
        size = os.path.getsize(filepath)
        if size > 10 * 1024 * 1024:  # 10MB
            if not messagebox.askyesno("Arquivo Grande", 
                                     f"Arquivo muito grande ({size/1024/1024:.1f}MB).\n"
                                     "Máximo recomendado: 10MB\n"
                                     "Continuar mesmo assim?"):
                return
                
        # Perguntar se é global ou privado
        choice = messagebox.askyesnocancel("Destino do Arquivo", 
                                         "Enviar para todos? (Não = mensagem privada)")
        if choice is None:  # Cancelado
            return
            
        filename = os.path.basename(filepath)
        
        try:
            # Codificar arquivo
            with open(filepath, "rb") as file:
                data = base64.b64encode(file.read()).decode('utf-8')
                
            if choice:  # Global
                message_formatted = {"type": "file", "control": "4all", 
                                   "message": data, "filename": filename}
                self.log_message(f"[Você → todos]: 📎 {filename} ({size/1024:.1f}KB)", "#3498db")
            else:  # Privado
                target_user = self.get_selected_user()
                if target_user is None:
                    target_user = simpledialog.askstring("Arquivo Privado", 
                                                       "Digite o nome do destinatário:")
                    if not target_user:
                        return
                        
                message_formatted = {"type": "file", "control": target_user, 
                                   "message": data, "filename": filename}
                self.log_message(f"[Você → {target_user}]: 📎 {filename} ({size/1024:.1f}KB)", "#3498db")
                
            self.client.send(json.dumps(message_formatted).encode('utf-8'))
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao enviar arquivo: {e}")

    def create_group(self):
        """Solicita a criação de um grupo."""
        if not self.name_registered:
            messagebox.showwarning(
                "Aviso",
                "Configure seu nome primeiro!"
            )
            return

        group_name = simpledialog.askstring(
            "Criar grupo",
            "Digite o nome do grupo:",
            parent=self.window
        )

        if not group_name or not group_name.strip():
            return

        group_name = group_name.strip()

        try:
            message_formatted = {
                "type": "create_group",
                "control": "dontcare",
                "message": group_name
            }

            self.client.send(
                json.dumps(message_formatted).encode("utf-8")
            )

        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Erro ao criar grupo: {e}"
            )

    def invite_to_group(self):
        """Envia um convite para um grupo."""
        if not self.name_registered:
            messagebox.showwarning(
                "Aviso",
                "Configure seu nome primeiro!"
            )
            return

        group_name = simpledialog.askstring(
            "Convidar para grupo",
            "Digite o nome do grupo:",
            parent=self.window
        )

        if not group_name or not group_name.strip():
            return

        group_name = group_name.strip()

        target_name = simpledialog.askstring(
            "Convidar para grupo",
            "Digite o nome do usuário que deseja convidar:",
            parent=self.window
        )

        if not target_name or not target_name.strip():
            return

        target_name = target_name.strip()

        try:
            message_formatted = {
                "type": "invite_group",
                "control": target_name,
                "message": group_name
            }

            self.client.send(
                json.dumps(message_formatted).encode("utf-8")
            )

        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Erro ao enviar convite: {e}"
            )

    def ask_group_invite(self, group_name, invitation_text):
        """Pergunta se quer aceitar o convite."""
        self.log_message(invitation_text, "#b40e45")

        accepted = messagebox.askyesno(
            "Convite para grupo",
            f"{invitation_text}\n\nDeseja aceitar o convite?",
            parent=self.window
        )

        try:
            message_formatted = {
                "type": "respond_group_invite",
                "control": group_name,
                "message": "accept" if accepted else "reject"
            }

            self.client.send(
                json.dumps(message_formatted).encode("utf-8")
            )

        except Exception as e:
            messagebox.showerror(
                "Erro",
                f"Erro ao responder ao convite: {e}",
                parent=self.window
            )

    def refresh_users(self):
        """Solicita lista atualizada de usuários"""
        if not self.name_registered:
            return
            
        try:
            message_formatted = {"type": "online_usr", "control": "dontcare", "message": "dontcare"}
            self.client.send(json.dumps(message_formatted).encode('utf-8'))
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao buscar usuários: {e}")
            
    def process_file_offer(self, sender, filename, b64data, file_size):
        """Processa oferta de arquivo recebido"""
        result = messagebox.askyesnocancel("Arquivo Recebido", 
                                         f"📎 Arquivo recebido de {sender}\n"
                                         f"📄 Nome: {filename}\n"
                                         f"📊 Tamanho: {file_size/1024:.1f}KB\n\n"
                                         f"Deseja baixar o arquivo?")
        
        if result:  # Sim - baixar
            try:
                # Criar diretório downloads se não existir
                if not os.path.exists("downloads"):
                    os.makedirs("downloads")
                    
                # Evitar sobrescrever arquivos
                base_name = os.path.splitext(filename)[0]
                extension = os.path.splitext(filename)[1]
                counter = 1
                new_filename = filename
                
                while os.path.exists(os.path.join("downloads", new_filename)):
                    new_filename = f"{base_name}_{counter}{extension}"
                    counter += 1
                    
                filepath = os.path.join("downloads", new_filename)
                
                # Salvar arquivo
                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(b64data))
                    
                actual_size = os.path.getsize(filepath)
                self.log_message(f"✅ Arquivo baixado: {new_filename} ({actual_size/1024:.1f}KB)", "#27ae60")
                messagebox.showinfo("Sucesso", f"Arquivo salvo em:\n{filepath}")
                
            except Exception as e:
                self.log_message(f"❌ Erro ao baixar arquivo: {e}", "#e74c3c")
                messagebox.showerror("Erro", f"Erro ao baixar arquivo: {e}")
        else:
            self.log_message(f"📎 Arquivo de {sender} ignorado: {filename}", "#95a5a6")
            
    def handle_messages(self):
        """Thread para receber mensagens do servidor"""
        while self.running:
            try:
                msg = self.client.recv(2048 * 10).decode('utf-8')
                if not msg:
                    break
                    
                key, value = msg.split("=", 1)
                
                if key == "msg":
                    # Processar mensagens de texto

                    if value.startswith("[ConviteGrupo]"):
                        try:
                            group_name = value.split(
                                " para o grupo '", 1
                            )[1].rsplit("'.", 1)[0]

                            self.window.after(
                                0,
                                lambda gn=group_name, v=value:
                                    self.ask_group_invite(gn, v)
                            )
                        except (IndexError, ValueError):
                            self.log_message(
                                "❌ Convite recebido em formato inválido",
                                "#e74c3c"
                            )

                    elif "[Servidor]:" in value:
                        if "já está sendo usado" in value:
                            self.waiting_for_name = True
                            self.name_registered = False
                            self.log_message(value, "#e74c3c")
                            self.window.after(0, self.request_new_name)
                        elif "Bem-vindo ao chat" in value:
                            self.name_registered = True
                            self.waiting_for_name = False
                            self.log_message(value, "#27ae60")
                            self.update_status("🟢 Conectado", "#27ae60")
                            self.enable_controls(True)
                            self.refresh_users()
                        else:
                            self.log_message(value, "#f39c12")
                    else:
                        self.log_message(value, "#ecf0f1")
                        
                elif key == "online_users":
                    # Processar lista de usuários
                    try:
                        users = json.loads(value)
                        self.update_users_list(users)
                        self.log_message(f"👥 {len(users)} outros usuários online", "#3498db")
                    except json.JSONDecodeError as e:
                        self.log_message(f"❌ Erro ao processar lista de usuários: {e}", "#e74c3c")
                        
                elif key == "file":
                    # Processar arquivo recebido
                    parts = value.split("||", 2)
                    if len(parts) == 3:
                        sender, filename, b64data = parts
                        file_size = (len(b64data) * 3) // 4
                        self.log_message(f"📎 Arquivo recebido de {sender}: {filename}", "#3498db")
                        
                        # Processar arquivo na thread principal
                        self.window.after(0, lambda: self.process_file_offer(sender, filename, b64data, file_size))
                    else:
                        self.log_message("❌ Arquivo recebido em formato inválido", "#e74c3c")
                        
            except Exception as e:
                if self.running:
                    self.log_message(f"❌ Erro ao receber mensagem: {e}", "#e74c3c")
                break
                
    def request_name(self):
        """Solicita nome do usuário"""
        while not self.name_registered and self.running:
            if self.waiting_for_name:
                name = simpledialog.askstring("Nome Duplicado", 
                                            "Este nome já está em uso.\nDigite um novo nome:")
            else:
                name = simpledialog.askstring("Bem-vindo", 
                                            "Digite seu nome para entrar no chat:",
                                            parent=self.window)
                
            if not name:
                if messagebox.askyesno("Sair", "Deseja sair do chat?"):
                    self.on_closing()
                    return
                continue
                
            try:
                message_formatted = {"type": "name", "control": "dontcare", "message": name}
                self.client.send(json.dumps(message_formatted).encode('utf-8'))
                self.current_user = name
                time.sleep(1)  # Aguardar resposta
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao enviar nome: {e}")
                break
                
    def request_new_name(self):
        """Solicita novo nome quando o atual está duplicado"""
        if self.waiting_for_name:
            name = simpledialog.askstring("Nome Duplicado", 
                                        "Este nome já está em uso.\nDigite um novo nome:",
                                        parent=self.window)
            if name:
                try:
                    message_formatted = {"type": "name", "control": "dontcare", "message": name}
                    self.client.send(json.dumps(message_formatted).encode('utf-8'))
                    self.current_user = name
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao enviar nome: {e}")
                    
    def connect_to_server(self):
        """Conecta ao servidor"""
        try:
            # Descobrir servidor automaticamente
            SERVER_IP = discover_server()
            
            if not SERVER_IP:
                # Se não encontrou automaticamente, solicitar IP manual
                SERVER_IP = simpledialog.askstring("Servidor", 
                                                 "Servidor não encontrado automaticamente.\n"
                                                 "Digite o IP do servidor:",
                                                 parent=self.window)
                if not SERVER_IP:
                    return False
                    
            PORT = 5050
            
            # Conectar ao servidor
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((SERVER_IP, PORT))
            
            self.log_message(f"🔗 Conectado ao servidor {SERVER_IP}:{PORT}", "#27ae60")
            self.update_status("🟡 Conectado - Configurando nome...", "#f39c12")
            
            # Iniciar thread para receber mensagens
            msg_thread = threading.Thread(target=self.handle_messages, daemon=True)
            msg_thread.start()
            
            # Solicitar nome do usuário
            self.window.after(1000, self.request_name)
            
            return True
            
        except Exception as e:
            self.log_message(f"❌ Erro ao conectar: {e}", "#e74c3c")
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao servidor:\n{e}")
            return False
            
    def on_closing(self):
        """Manipula o fechamento da janela"""
        self.running = False
        
        try:
            if self.client:
                self.client.close()
        except:
            pass
            
        self.window.quit()
        self.window.destroy()
        
    def run(self):
        """Executa o cliente de chat"""
        # Tentar conectar ao servidor
        if self.connect_to_server():
            # Executar interface gráfica
            self.window.mainloop()
        else:
            self.window.destroy()

def main():
    """Função principal"""
    try:
        client = ChatClientGUI()
        client.run()
    except KeyboardInterrupt:
        print("\n👋 Cliente desconectado.")
    except Exception as e:
        print(f"❌ Erro no cliente: {e}")

if __name__ == "__main__":
    main()
