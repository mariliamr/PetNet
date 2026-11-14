#server.py

import socket
import threading
import time
import json

from server_gui import ServerGUI

SERVER_IP = "0.0.0.0" # Aceita conexoes de qualquer IP
PORT = 5050 # Porta principal do chat
DISC_PORT = 5051 # Porta para descoberta automatica
ADDR = (SERVER_IP, PORT)
FORMAT = 'utf-8'          # Codificação de caracteres

server = None
discovery_socket = None

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
    global discovery_socket
    discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    discovery_socket.bind(('', 5051))
    
    def discovery_loop():
        while gui.running:
            try:
                data, addr = discovery_socket.recvfrom(1024)
                if data == b"CHAT_DISCOVER":
                    gui.log(f"[Descoberta] Requisição de {addr[0]}")
                    discovery_socket.sendto(b"CHAT_SERVER", addr)
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
MAX_GROUP_INVITES_PER_REQUEST = 5

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
                if user_conn is None:
                    conn.send("msg=[Servidor]: Defina seu nome primeiro.".encode(FORMAT))
                    continue

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
                target_names = message.get("targets")

                # Compatibilidade com solicitações antigas de convite individual
                if target_names is None:
                    single_target = message.get("control")
                    target_names = [single_target] if isinstance(single_target, str) else []

                group = groups.get(group_name)

                if group is None:
                    response = f"Grupo '{group_name}' não encontrado."

                elif group["creator"] != user_conn["name"]:
                    response = "Somente o criador pode convidar pessoas."

                elif not isinstance(target_names, list) or not target_names:
                    response = "Informe pelo menos um usuário para convidar."

                elif len(target_names) > MAX_GROUP_INVITES_PER_REQUEST:
                    response = (
                        f"Você pode convidar no máximo "
                        f"{MAX_GROUP_INVITES_PER_REQUEST} pessoas por vez."
                    )

                else:
                    sent = []
                    not_sent = []
                    processed = set()

                    for target_name in target_names:
                        if not isinstance(target_name, str) or not target_name.strip():
                            not_sent.append("Nome inválido")
                            continue

                        target_name = target_name.strip()

                        if target_name in processed:
                            not_sent.append(
                                f"{target_name}: nome repetido na solicitação"
                            )
                            continue

                        processed.add(target_name)

                        if target_name in group["members"]:
                            not_sent.append(
                                f"{target_name}: já faz parte do grupo"
                            )
                            continue

                        if target_name in group["pending_invites"]:
                            not_sent.append(
                                f"{target_name}: já foi convidado"
                            )
                            continue

                        target_conn = search_name_in_connections(target_name)

                        if target_conn is None:
                            not_sent.append(
                                f"{target_name}: não está online"
                            )
                            continue

                        group["pending_invites"].append(target_name)

                        target_conn["conn"].send(
                            f"msg=[ConviteGrupo] {user_conn['name']} "
                            f"convidou você para o grupo '{group_name}'."
                            .encode(FORMAT)
                        )

                        sent.append(target_name)

                    if sent:
                        response = f"Convites enviados para: {', '.join(sent)}."
                    else:
                        response = "Nenhum convite foi enviado."

                    if not_sent:
                        response += "\nNão enviados: " + "; ".join(not_sent)

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

def shutdown_server():
    """Fecha os sockets do servidor sem depender da interface gráfica."""
    if server is not None:
        try:
            server.close()
        except OSError:
            pass
    if discovery_socket is not None:
        try:
            discovery_socket.close()
        except OSError:
            pass


def start():
    """Inicia o servidor, a descoberta UDP e a interface gráfica."""
    global gui, server

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(ADDR)

    gui = ServerGUI(
        SERVER_IP,
        PORT,
        DISC_PORT,
        on_close=shutdown_server,
        connection_count=lambda: len(connections),
    )

    handle_discovery()
    server_thread = threading.Thread(target=server_loop, daemon=True)
    server_thread.start()
    gui.run()
    shutdown_server()


if __name__ == "__main__":
    try:
        start()
    except KeyboardInterrupt:
        print("\n[Servidor] Servidor encerrado pelo usuário.")
    except Exception as e:
        print(f"[Erro crítico] {e}")
    finally:
        shutdown_server()
