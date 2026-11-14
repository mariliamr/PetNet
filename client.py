"""Controlador de rede do cliente. Não cria nem manipula widgets Tkinter."""

import base64
import json
import os
import socket
import threading

from client_gui import ChatClientGUI

FORMAT = "utf-8"
PORT = 5050


def discover_server(timeout=5):
    """Descobre automaticamente o servidor de chat na rede local."""
    print("🔍 Procurando servidor na rede local...")
    discover_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    discover_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    discover_socket.settimeout(timeout)
    try:
        discover_socket.sendto(b"CHAT_DISCOVER", ("<broadcast>", 5051))
        data, addr = discover_socket.recvfrom(1024)
        if data == b"CHAT_SERVER":
            print(f"✅ Servidor encontrado: {addr[0]}")
            return addr[0]
    except socket.timeout:
        print("❌ Nenhum servidor encontrado automaticamente.")
    except Exception as exc:
        print(f"❌ Erro na descoberta: {exc}")
    finally:
        discover_socket.close()
    return None


class ChatClient:
    """Conexão, protocolo e transferência de arquivos do cliente."""

    def __init__(self, view):
        self.view = view
        self.client = None
        self.running = True
        self.name_registered = False
        self.waiting_for_name = False
        self.current_user = ""

    def connect_to_server(self):
        try:
            server_ip = discover_server()
            if not server_ip:
                server_ip = self.view.ask_server_ip()
                if not server_ip:
                    return False
            self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client.connect((server_ip, PORT))
            self.view.log_message(f"🔗 Conectado ao servidor {server_ip}:{PORT}", "#27ae60")
            self.view.update_status("🟡 Conectado - Configurando nome...", "#f39c12")
            receiver = threading.Thread(target=self.handle_messages, daemon=True)
            receiver.start()
            self.view.window.after(1000, self.view.request_name)
            return True
        except Exception as exc:
            self.view.log_message(f"❌ Erro ao conectar: {exc}", "#e74c3c")
            self.view.show_error("Erro de Conexão", "Não foi possível conectar ao servidor: " + str(exc))
            return False

    def _send_payload(self, payload):
        if not self.running or self.client is None:
            self.view.log_message("❌ Não há conexão ativa com o servidor.", "#e74c3c")
            return False
        try:
            self.client.sendall(json.dumps(payload).encode(FORMAT))
            return True
        except Exception as exc:
            self.view.log_message(f"❌ Erro de comunicação: {exc}", "#e74c3c")
            self.view.show_error("Erro", f"Erro ao enviar dados: {exc}")
            return False

    def register_name(self, name):
        self.current_user = name.strip()
        return self._send_payload({"type": "name", "control": "dontcare", "message": self.current_user})

    def send_text(self, content, destination="4all"):
        if not self.name_registered:
            self.view.show_warning("Aviso", "Configure seu nome primeiro!")
            return False
        return self._send_payload({"type": "msg", "control": destination, "message": content})

    def send_file(self, filepath, destination):
        try:
            with open(filepath, "rb") as source:
                encoded = base64.b64encode(source.read()).decode(FORMAT)
            payload = {"type": "file", "control": destination, "message": encoded, "filename": os.path.basename(filepath)}
            return self._send_payload(payload)
        except Exception as exc:
            self.view.show_error("Erro", f"Erro ao ler ou enviar arquivo: {exc}")
            return False

    def create_group(self, group_name):
        return self._send_payload({"type": "create_group", "control": "dontcare", "message": group_name})

    def invite_to_group(self, group_name, target_names):
        return self._send_payload({
            "type": "invite_group",
            "control": "dontcare",
            "message": group_name,
            "targets": target_names})

    def respond_group_invite(self, group_name, accepted):
        decision = "accept" if accepted else "reject"
        return self._send_payload({"type": "respond_group_invite", "control": group_name, "message": decision})

    def request_group_history(self, group_name):
        return self._send_payload({"type": "group_history", "control": group_name, "message": ""})

    def refresh_users(self):
        return self._send_payload({"type": "online_usr", "control": "dontcare", "message": "dontcare"})

    def save_received_file(self, filename, encoded_data):
        try:
            os.makedirs("downloads", exist_ok=True)
            base_name, extension = os.path.splitext(filename)
            target = os.path.join("downloads", filename)
            counter = 1
            while os.path.exists(target):
                target = os.path.join("downloads", f"{base_name}_{counter}{extension}")
                counter += 1
            with open(target, "wb") as destination:
                destination.write(base64.b64decode(encoded_data))
            return target
        except Exception as exc:
            self.view.log_message(f"❌ Erro ao baixar arquivo: {exc}", "#e74c3c")
            self.view.show_error("Erro", f"Erro ao baixar arquivo: {exc}")
            return None

    def handle_messages(self):
        while self.running:
            try:
                raw_message = self.client.recv(2048 * 10).decode(FORMAT)
                if not raw_message:
                    break
                key, value = raw_message.split("=", 1)
                if key == "msg":
                    self._handle_text_message(value)
                elif key == "online_users":
                    try:
                        users = json.loads(value)
                        self.view.update_users_list(users)
                        self.view.log_message(f"👥 {len(users)} outros usuários online", "#3498db")
                    except json.JSONDecodeError as exc:
                        self.view.log_message(f"❌ Erro ao processar lista de usuários: {exc}", "#e74c3c")
                elif key == "file":
                    parts = value.split("||", 2)
                    if len(parts) == 3:
                        sender, filename, encoded_data = parts
                        file_size = (len(encoded_data) * 3) // 4
                        self.view.log_message(f"📎 Arquivo recebido de {sender}: {filename}", "#3498db")
                        self.view.window.after(
                            0,
                            lambda s=sender, f=filename, d=encoded_data, z=file_size:
                                self.view.process_file_offer(s, f, d, z),
                        )
                    else:
                        self.view.log_message("❌ Arquivo recebido em formato inválido", "#e74c3c")
            except Exception as exc:
                if self.running:
                    self.view.log_message(f"❌ Erro ao receber mensagem: {exc}", "#e74c3c")
                break
        if self.running:
            self.name_registered = False
            self.view.enable_controls(False)
            self.view.update_status("🔴 Desconectado", "#e74c3c")

    def _handle_text_message(self, value):
        if value.startswith("[ConviteGrupo]"):
            try:
                group_name = value.split(" para o grupo '", 1)[1].rsplit("'.", 1)[0]
                self.view.window.after(0, lambda gn=group_name, text=value: self.view.ask_group_invite(gn, text))
            except (IndexError, ValueError):
                self.view.log_message("❌ Convite recebido em formato inválido", "#e74c3c")
        elif "[Servidor]:" in value:
            if "já está sendo usado" in value:
                self.waiting_for_name = True
                self.name_registered = False
                self.view.log_message(value, "#e74c3c")
                self.view.window.after(0, self.view.request_new_name)
            elif "Bem-vindo ao chat" in value:
                self.name_registered = True
                self.waiting_for_name = False
                self.view.log_message(value, "#27ae60")
                self.view.update_status("🟢 Conectado", "#27ae60")
                self.view.enable_controls(True)
                self.refresh_users()
            else:
                self.view.log_message(value, "#f39c12")
        else:
            self.view.log_message(value, "#ecf0f1")

    def close_connection(self):
        self.running = False
        if self.client is not None:
            try:
                self.client.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.client.close()
            except OSError:
                pass


def main():
    view = ChatClientGUI()
    controller = ChatClient(view)
    view.set_controller(controller)
    if controller.connect_to_server():
        view.run()
    else:
        view.on_closing()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Cliente desconectado.")
    except Exception as exc:
        print(f"❌ Erro no cliente: {exc}")
