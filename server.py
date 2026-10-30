#server.py

import socket
import threading
import time
import json
from tkinter import *
from tkinter import scrolledtext
import datetime

SERVER_IP = "0.0.0.0" # Aceita conexoes de qualquer IP
PORT = 5050 # Porta principal do chat
DISC_PORT = 5051 # Porta para descoberta automatica
ADDR = (SERVER_IP, PORT)
FORMAT = 'utf-8'          # Codificação de caracteres

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

class serverGUI:
    """
    Classe para gerenciar a interface grafica do servidor
    - Exibe mensagens de status e conexoes ativas
    - Permite interacao com o servidor via GUI
    """
    def __init__(self):
        self.window = window_create()

    # Frame para informações do servidor
        info_frame = Frame(self.window, bg="#34495e", relief="raised", bd=2)
        info_frame.pack(pady=10, padx=20, fill="x")

    # Informações do servidor
        server_info = Label(info_frame, text=f"📡 Servidor ativo em: {SERVER_IP}:{PORT}", 
                           font=("Arial", 12, "bold"), 
                           bg="#34495e", fg="#1abc9c")
        server_info.pack(pady=8)
        
        discovery_info = Label(info_frame, text=f"🔍 Sistema de descoberta automática ativo na porta {DISC_PORT}", 
                              font=("Arial", 10), 
                              bg="#34495e", fg="#95a5a6")
        discovery_info.pack(pady=2)

    # Frame para estatísticas
        stats_frame = Frame(self.window, bg="#2c3e50")
        stats_frame.pack(pady=10, fill="x")
        
        self.connections_label = Label(stats_frame, text="👥 Conexões ativas: 0", 
                                        font=("Arial", 12, "bold"), 
                                        bg="#2c3e50", fg="#e74c3c")
        self.connections_label.pack(side=LEFT, padx=20)
        
        self.messages_label = Label(stats_frame, text="💬 Mensagens: 0", 
                                    font=("Arial", 12, "bold"), 
                                    bg="#2c3e50", fg="#3498db")
        self.messages_label.pack(side=LEFT, padx=20)
    
    # Área de log com scroll
        log_frame = Frame(self.window, bg="#2c3e50")
        log_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        log_label = Label(log_frame, text="📋 LOG DO SERVIDOR:", 
                         font=("Arial", 12, "bold"), 
                         bg="#2c3e50", fg="#f39c12")
        log_label.pack(anchor="w", pady=(0, 5))
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=25, 
            width=100,
            font=("Consolas", 10),
            bg="#1e1e1e", 
            fg="#00ff00",
            insertbackground="#00ff00",
            selectbackground="#404040"
        )
        self.log_text.pack(fill="both", expand=True)

        clear_btn = Button(self.window, text="🗑️ Limpar Log", 
                            command=self.clear_log,
                            font=("Arial", 10, "bold"),
                            bg="#e74c3c", fg="white",
                            relief="flat", padx=20)
        clear_btn.pack(pady=10)

    # Variáveis de controle
        self.message_count = 0
        self.running = True
        
    # Log inicial
        self.log("[SERVIDOR] Iniciando servidor de chat...")
        self.log(f"[SERVIDOR] Sistema de descoberta ativo na porta 5051")
        self.log(f"[SERVIDOR] Servidor principal ouvindo em {SERVER_IP}:{PORT}")
        self.log("[SERVIDOR] Aguardando conexões...")

    def log(self, message):
        """Adiciona uma mensagem ao log com timestamp"""
        if not self.running:
            return
            
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # Atualizar na thread principal do Tkinter
        self.window.after(0, self._update_log, formatted_message)
        
        # Também imprimir no console
        print(f"[{timestamp}] {message}")

    def _update_log(self, message):
        """Atualiza o log na interface (deve ser chamado na thread principal)"""
        try:
            self.log_text.insert(END, message)
            self.log_text.see(END)
        except:
            pass
    def update_stats(self, connections_count, messages_count=None):
        """Atualiza as estatísticas na interface"""
        if not self.running:
            return
            
        if messages_count is not None:
            self.message_count = messages_count
        
        def _update():
            try:
                self.connections_label.config(text=f"👥 Conexões ativas: {connections_count}")
                self.messages_label.config(text=f"💬 Mensagens: {self.message_count}")
            except:
                pass
        
        self.window.after(0, _update)
    def increment_message_count(self):
        """Incrementa o contador de mensagens"""
        self.message_count += 1
        self.update_stats(len(connections))
    
    def clear_log(self):
        """Limpa o log da interface"""
        self.log_text.delete(1.0, END)
        self.log("[SERVIDOR] Log limpo pelo usuário")
    
    def on_closing(self):
        """Manipula o fechamento da janela"""
        self.running = False
        self.log("[SERVIDOR] Encerrando servidor...")
        try:
            server.close()
        except:
            pass
        self.window.destroy()

# FORMATO DAS MENSAGENS:
# 
# Cliente -> Servidor (JSON):
# {
#   "type": "name|msg|file|online_usr",
#   "control": "destinatario|4all|dontcare", 
#   "message": "conteudo",
#   "filename": "nome_arquivo" (apenas para files)
# }
#
# Servidor -> Cliente (string):
# "msg=conteudo_da_mensagem"
# "file=remetente||nome_arquivo||dados_base64"
# "online_users=json_array_usuarios"

def handle_discovery():
    """
    Gerencia a descoberta automatica do servidor na rede local
    - Cria socket UDP na porta 5051
    - Escuta por mensagens "CHAT_DISCOVER" 
    - Responde com "CHAT_SERVER" para identificar o servidor
    """
    discover_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    discover_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    discover_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    discover_socket.bind(('', 5051))
    
    def discovery_loop():
        while True:
            try:
                data, addr = discover_socket.recvfrom(1024)
                if data == b"CHAT_DISCOVER":
                    gui.log(f"[Descoberta] Requisição de {addr[0]}")
                    discover_socket.sendto(b"CHAT_SERVER", addr)
            except Exception as e:
                if gui.running:
                    gui.log(f"[Erro Descoberta] {e}")
                break
    
    # Inicia thread separada para descoberta em background
    discovery_thread = threading.Thread(target=discovery_loop, daemon=True)
    discovery_thread.start()

# Estruturas de dados globais
connections = []     # Lista de usuarios conectados: [{"conn": socket, "addr": tuple, "name": str}]
global_messages = []  # Historico de mensagens publicas
private_messages = [] # Historico de mensagens privadas

# Estruturas dos grupos
groups = {}
MAX_GROUPS_MESSAGES = 100

def create_group(group_name, creator_name):
    """
    Cria um grupo e registra o criador como o primeiro membro
    """
    if group_name in groups:
        return False, "Já existe um grupo com esse nome."

    groups[group_name] = {
        "creator": creator_name,
        "members": [creator_name],
        "pending_invites": [],
        "messages": []
    }
    return True, f"Grupo '{group_name}' criado com sucesso."

def search_name_in_connections(name):
    """
    Busca um usuario conectado pelo nome
    Retorna o dicionario da conexao ou None se nao encontrado
    """
    for conn in connections:
        if conn["name"] == name:
            return conn
    return None

def name_already_exists(name):
    """
    Verifica se o nome ja esta sendo usado por outro usuario
    Usado para evitar nomes duplicados no chat
    """
    for conn in connections:
        if conn["name"] == name:
            return True
    return False

def view_global_history(client_connection):
    """
    Envia todo o historico de mensagens globais para um cliente que acabou de se conectar
    - Percorre a lista global_messages
    - Envia cada mensagem formatada para o cliente
    - Inclui delay entre mensagens para evitar spam
    """
    conn = client_connection["conn"]
    for msg in global_messages:
        try:
            if msg["type"] == "msg":
                message = f"[{msg['sender']} -> todos]: {msg['content']}"
                conn.send(f"msg={message}".encode(FORMAT))
            elif msg["type"] == "file":
                filename = msg.get("filename", "arquivo_recebido")
                data = msg["content"]
                sender = msg["sender"]
                # Formato: remetente||nome_arquivo||dados_base64
                conn.send(f"file={sender}||{filename}||{data}".encode(FORMAT))
            time.sleep(0.2) # Delay para nao sobrecarregar o cliente
        except Exception as e:
            gui.log(f"Erro ao enviar histórico para {client_connection['name']}: {e}")

def send_online_users_list(client_connection):
    """
    Envia a lista de usuarios online para o cliente solicitante
    - Coleta informacoes de todos os usuarios conectados (exceto o proprio)
    - Formata como JSON e envia via "online_users=dados"
    """
    conn = client_connection["conn"]
    try:
        online_users = []
        # Para não incluir o próprio usuário na contagem:
        for connection in connections:
            if connection["name"] != client_connection["name"]:  # Excluir o próprio usuário
                user_info = {
                    "name": connection["name"],
                    "addr": f"{connection['addr'][0]}:{connection['addr'][1]}"
                }
                online_users.append(user_info)
        
        # Envia a lista como JSON
        users_data = json.dumps(online_users)
        conn.send(f"online_users={users_data}".encode(FORMAT))
        gui.log(f"[Lista de Usuários] Enviada para {client_connection['name']} - {len(online_users)} outros usuários online")
        
    except Exception as e:
        gui.log(f"Erro ao enviar lista de usuários para {client_connection['name']}: {e}")

def send_message_to_user(sending_conn, client_connection, is_private):
    """
    Envia a ultima mensagem de um usuario para outro usuario especifico
    - sending_conn: quem enviou a mensagem
    - client_connection: quem vai receber
    - is_private: True para mensagem privada, False para global
    """
    conn = client_connection["conn"]
    dest_name = client_connection["name"]
    from_name = sending_conn["name"] if sending_conn != 0 else "Servidor"

    messages_source = private_messages if is_private else global_messages
    
    if is_private:
        # Para mensagens privadas, filtrar apenas mensagens para este usuario
        messages_for_client = [
            msg for msg in messages_source
            if (msg["sender"] == from_name and msg["destination"] == dest_name)
        ]
    else:
        # Para mensagens globais, pegar todas
        messages_for_client = messages_source

    if messages_for_client:
        last_msg = messages_for_client[-1]
        try:
            if last_msg["type"] == "msg":
                if is_private:
                    message = f"[{last_msg['sender']} -> {last_msg['destination']}]: {last_msg['content']}"
                else:
                    message = f"[{last_msg['sender']} -> todos]: {last_msg['content']}"
                conn.send(f"msg={message}".encode(FORMAT))
            elif last_msg["type"] == "file":
                filename = last_msg.get("filename", "arquivo_recebido")
                data = last_msg["content"]
                sender = last_msg["sender"]
                # Formato: remetente||nome_arquivo||dados_base64
                conn.send(f"file={sender}||{filename}||{data}".encode(FORMAT))
        except Exception as e:
            gui.log(f"Erro ao enviar mensagem para {dest_name}: {e}")

def send_message_to_all(user_conn):
    """
    Envia a ultima mensagem global para todos os usuarios conectados
    Exclui o remetente da lista de destinatarios
    """
    for conn in connections:
        if conn["conn"] != user_conn["conn"]:
            send_message_to_user(user_conn, conn, is_private=False)

def handle_clients(conn, addr):
    """
    Funcao principal para gerenciar cada cliente conectado
    Roda em thread separada para cada conexao
    Processa todos os tipos de mensagem JSON recebidas:
    - "name": definir nome do usuario
    - "online_usr": solicitar lista de usuarios
    - "msg": enviar mensagem de texto
    - "file": enviar arquivo
    """
    gui.log(f"[Conexão] Novo usuário conectado: {addr}")
    global connections
    gui.update_stats(len(connections))

    user_conn = None # Sera definido quando o usuario enviar seu nome

    while True:
        try:
            data = conn.recv(2048 * 10) # Buffer grande para arquivos
            if not data:
                break

            message = json.loads(data.decode(FORMAT))

            if message["type"] == "name":
                name = message["message"]
                
                # Verificar se o nome ja existe
                if name_already_exists(name):
                    error_msg = f"❌ Nome '{name}' já está sendo usado! Escolha outro nome."
                    conn.send(f"msg=[Servidor]: {error_msg}".encode(FORMAT))
                    # Solicitar novo nome
                    conn.send(f"msg=[Servidor]: Digite um novo nome:".encode(FORMAT))
                    gui.log(f"[NOME REJEITADO] '{name}' já existe - solicitando novo nome para {addr[0]}")
                    continue
                
                # Criar registro do usuario
                user_conn = {"conn": conn, "addr": addr, "name": name}
                connections.append(user_conn)
                gui.log(f"[USUÁRIO CONECTADO] {name} conectado de {addr}")
                gui.update_stats(len(connections))
                
                # Enviar mensagem de boas-vindas
                welcome_msg = f"✅ Bem-vindo ao chat, {name}!"
                conn.send(f"msg=[Servidor]: {welcome_msg}".encode(FORMAT))
                
                # Enviar historico de mensagens globais
                view_global_history(user_conn)

            elif message["type"] == "create_group":
                group_name = message["message"]
                creator_name = user_conn["name"]
                
                success, response = create_group(group_name, creator_name)
                
                conn.send(f"msg=[Servidor]: {response}".encode(FORMAT))

            elif message["type"] == "invite_group":
                if user_conn is None:
                    conn.send(
                        "msg=[Servidor]: Defina seu nome primeiro.".encode(FORMAT)
                    )
                    continue

                group_name = message["message"]
                target_name = message["control"]

                group = groups.get(group_name)

                if group is None:
                    response = f"Grupo '{group_name}' não encontrado."

                elif group["creator"] != user_conn["name"]:
                    response = "Somente o criador pode convidar pessoas."

                elif target_name in group["members"]:
                    response = f"{target_name} já faz parte do grupo."

                elif target_name in group["pending_invites"]:
                    response = f"{target_name} já foi convidado."

                else:
                    target_conn = search_name_in_connections(target_name)

                    if target_conn is None:
                        response = f"Usuário '{target_name}' não está online."
                    else:
                        group["pending_invites"].append(target_name)

                        target_conn["conn"].send(
                            f"msg=[ConviteGrupo] {user_conn['name']} convidou você para o grupo '{group_name}'.".encode(FORMAT)
                        )

                        response = f"Convite enviado para {target_name}."

                conn.send(f"msg=[Servidor]: {response}".encode(FORMAT))

            
            elif message["type"] == "respond_group_invite":
                if user_conn is None:
                    conn.send(
                        "msg=[Servidor]: Defina seu nome primeiro.".encode(FORMAT)
                    )
                    continue

                group_name = message["control"]
                decision = message["message"]
                username = user_conn["name"]

                group = groups.get(group_name)

                if group is None:
                    response = f"Grupo '{group_name}' não encontrado."

                elif username not in group["pending_invites"]:
                    response = "Você não tem convite pendente para esse grupo."

                elif decision == "accept":
                    group["pending_invites"].remove(username)

                    if username not in group["members"]:
                        group["members"].append(username)

                    response = f"Você entrou no grupo '{group_name}'!"

                elif decision == "reject":
                    group["pending_invites"].remove(username)
                    response = f"Você recusou o convite para '{group_name}'."

                else:
                    response = "Resposta ao convite inválida."

                conn.send(
                    f"msg=[Servidor]: {response}".encode(FORMAT)
                )

            elif message["type"] == "group_history":
                if user_conn is None:
                    conn.send(
                        "msg=[Servidor]: Defina seu nome primeiro.".encode(FORMAT)
                    )
                    continue

                group_name = message["control"]
                group = groups.get(group_name)

                if group is None:
                    response = f"Grupo '{group_name}' não encontrado."

                elif user_conn["name"] not in group["members"]:
                    response = "Você não faz parte deste grupo."

                elif not group["messages"]:
                    response = f"O grupo '{group_name}' ainda não tem mensagens."

                else:
                    history_lines = [
                        f"{msg['sender']}: {msg['content']}"
                        for msg in group["messages"]
                    ]

                    response = (
                        f"[Histórico do grupo {group_name}]\n"
                        + "\n".join(history_lines)
                    )

                conn.send(f"msg={response}".encode(FORMAT))

            elif message["type"] == "online_usr":
                # Verificar se o usuário já se registrou
                if user_conn is None:
                    error_msg = "❌ Você precisa definir um nome primeiro!"
                    conn.send(f"msg=[Servidor]: {error_msg}".encode(FORMAT))
                    continue
                    
                # Envia a lista de usuários online
                send_online_users_list(user_conn)

            elif message["type"] == "msg":
                # Verificar se o usuário já se registrou
                if user_conn is None:
                    error_msg = "❌ Você precisa definir um nome primeiro!"
                    conn.send(f"msg=[Servidor]: {error_msg}".encode(FORMAT))
                    continue
                    
                if message["control"] == "4all":
                    # Mensagem global para todos
                    new_message = {
                        "sender": user_conn["name"],
                        "destination": "all",
                        "type": "msg",
                        "content": message["message"]
                    }
                    global_messages.append(new_message)
                    gui.log(f"[Mensagem Global] {user_conn['name']}: {message['message'][:50]}...")
                    gui.increment_message_count()
                    send_message_to_all(user_conn)

                elif message["control"].startswith("group:"):
                    group_name = message["control"][6:]
                    group = groups.get(group_name)

                    if group is None:
                        error_msg = f"❌ Grupo '{group_name}' não encontrado."
                        conn.send(f"msg=[Servidor]: {error_msg}".encode(FORMAT))
                        continue

                    elif user_conn["name"] not in group["members"]:
                        error_msg = "❌ Você não faz parte deste grupo."
                        conn.send(f"msg=[Servidor]: {error_msg}".encode(FORMAT))
                        continue

                    else:
                        new_message = {
                            "sender": user_conn["name"],
                            "destination": group_name,
                            "type": "group_msg",
                            "content": message["message"]
                        }

                    group["messages"].append(new_message)

                    if len(group["messages"]) > MAX_GROUPS_MESSAGES:
                        group["messages"].pop(0)

                    gui.log(
                        f"[Mensagem de Grupo] {group_name} - "
                        f"{user_conn['name']}: {message['message'][:50]}..."
                    )

                    gui.increment_message_count()

                    for member_name in group["members"]:
                        member_conn = search_name_in_connections(member_name)

                        if member_conn is not None:
                            member_conn["conn"].send(
                                f"msg=[Grupo: {group_name}] "
                                f"{user_conn['name']}: {message['message']}".encode(FORMAT)
                            )

                else:
                    # Mensagem privada para usuario especifico
                    destination = message["control"]
                    dest_conn = search_name_in_connections(destination)
                    if dest_conn:
                        new_message = {
                            "sender": user_conn["name"],
                            "destination": destination,
                            "type": "msg",
                            "content": message["message"]
                        }
                        private_messages.append(new_message)
                        gui.log(f"[Mensagem Privada] {user_conn['name']} -> {destination}: {message['message'][:50]}...")
                        gui.increment_message_count()
                        send_message_to_user(user_conn, dest_conn, is_private=True)
                    else:
                        # Enviar mensagem de erro para o remetente
                        error_msg = f"❌ Usuário '{destination}' não encontrado ou offline."
                        conn.send(f"msg=[Servidor]: {error_msg}".encode(FORMAT))
                        gui.log(f"[ERRO] {user_conn['name']} tentou enviar mensagem para '{destination}' (não encontrado)")

            elif message["type"] == "file":
                # Verificar se o usuário já se registrou
                if user_conn is None:
                    error_msg = "❌ Você precisa definir um nome primeiro!"
                    conn.send(f"msg=[Servidor]: {error_msg}".encode(FORMAT))
                    continue
                    
                destination = message["control"]
                filename = message.get("filename", "arquivo_recebido")
                file_data = message["message"] # Dados em base64
                
                # Verificar tamanho do arquivo (em Base64)
                file_size_b64 = len(file_data)
                file_size_bytes = (file_size_b64 * 3) // 4  # Aproximação do tamanho real
                
                gui.log(f"[ARQUIVO] {user_conn['name']} enviando '{filename}' ({file_size_bytes/1024:.1f}KB)")
                
                new_message = {
                    "sender": user_conn["name"],
                    "destination": destination,
                    "type": "file",
                    "content": file_data,
                    "filename": filename
                }
                
                if destination == "4all":
                    # Arquivo global para todos
                    global_messages.append(new_message)
                    gui.log(f"[ARQUIVO GLOBAL] {user_conn['name']}: {filename}")
                    gui.increment_message_count()
                    send_message_to_all(user_conn)
                else:
                    # Arquivo privado para usuario especifico
                    dest_conn = search_name_in_connections(destination)
                    if dest_conn:
                        private_messages.append(new_message)
                        gui.log(f"[ARQUIVO PRIVADO] {user_conn['name']} → {destination}: {filename}")
                        gui.increment_message_count()
                        send_message_to_user(user_conn, dest_conn, is_private=True)
                    else:
                        # Enviar mensagem de erro para o remetente
                        error_msg = f"❌ Usuário '{destination}' não encontrado. Arquivo '{filename}' não foi entregue."
                        conn.send(f"msg=[Servidor]: {error_msg}".encode(FORMAT))

        except json.JSONDecodeError as e:
            gui.log(f"[ERRO JSON] Conexão {addr[0]}:{addr[1]} enviou dados inválidos: {e}")
            break
        except Exception as e:
            gui.log(f"[ERRO CONEXÃO] {addr[0]}:{addr[1]} - {e}")
            break

    # Limpeza da conexao ao desconectar
    if user_conn:
        connections.remove(user_conn)
        gui.log(f"[DESCONEXÃO] '{user_conn['name']}' ({addr[0]}:{addr[1]}) desconectado")
        gui.update_stats(len(connections))
    else:
        # Remover conexao mesmo se user_conn nao foi criado (nome nao definido)
        for i, conn_data in enumerate(connections):
            if conn_data["conn"] == conn:
                connections.pop(i)
                gui.log(f"[DESCONEXÃO] Usuário não identificado ({addr[0]}:{addr[1]}) desconectado")
                gui.update_stats(len(connections))
                break
    
    conn.close()

def server_loop():
    """Loop principal do servidor em thread separada"""
    server.listen()
    
    while gui.running:
        try:
            conn, addr = server.accept() # Aceita nova conexao
            # Cria thread separada para cada cliente
            thread = threading.Thread(target=handle_clients, args=(conn, addr))
            thread.daemon = True
            thread.start()
        except Exception as e:
            if gui.running:
                gui.log(f"[ERRO SERVIDOR] {e}")
            break

def window_create():
    """
    Cria a janela principal do servidor
    - Configura titulo e tamanho
    - Adiciona label de status
    """
    window = Tk()
    window.title("Servidor de Chat")
    window.geometry("800x600")
    window.configure(bg="#2c3e50")
    

    title = Label(window, text="🖥️ SERVIDOR DE CHAT", 
                     font=("Arial", 18, "bold"), 
                     bg="#2c3e50", fg="#ecf0f1")
    title.pack(pady=15)   
    return window

def start():
    """
    Funcao principal do servidor
    - Cria a interface gráfica
    - Inicia o sistema de descoberta automatica
    - Inicia o servidor em thread separada
    - Executa o loop da interface
    """
    global gui
    
    # Criar interface gráfica
    gui = serverGUI()
    
    # Iniciar descoberta automática
    handle_discovery()
    
    # Iniciar servidor em thread separada
    server_thread = threading.Thread(target=server_loop, daemon=True)
    server_thread.start()
    
    # Executar interface gráfica (loop principal)
    gui.window.mainloop()

if __name__ == "__main__":
    try:
        start()
    except KeyboardInterrupt:
        print("\n[Servidor] Servidor encerrado pelo usuário.")
    except Exception as e:
        print(f"[Erro crítico] {e}")
    finally:
        try:
            server.close()
        except:
            pass
