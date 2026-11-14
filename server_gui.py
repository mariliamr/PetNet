"""Interface gráfica do servidor de chat. Não contém lógica de sockets."""

import datetime
from tkinter import *
from tkinter import scrolledtext


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



class ServerGUI:
    """
    Classe para gerenciar a interface grafica do servidor
    - Exibe mensagens de status e conexoes ativas
    - Permite interacao com o servidor via GUI
    """
    def __init__(self, server_ip, port, discovery_port, on_close=None, connection_count=None):
        self.server_ip = server_ip
        self.port = port
        self.discovery_port = discovery_port
        self.on_close_callback = on_close
        self.connection_count = connection_count or (lambda: 0)
        self.window = window_create()

    # Frame para informações do servidor
        info_frame = Frame(self.window, bg="#34495e", relief="raised", bd=2)
        info_frame.pack(pady=10, padx=20, fill="x")

    # Informações do servidor
        server_info = Label(info_frame, text=f"📡 Servidor ativo em: {self.server_ip}:{self.port}", 
                           font=("Arial", 12, "bold"), 
                           bg="#34495e", fg="#1abc9c")
        server_info.pack(pady=8)
        
        discovery_info = Label(info_frame, text=f"🔍 Sistema de descoberta automática ativo na porta {self.discovery_port}", 
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
        self.log(f"[SERVIDOR] Sistema de descoberta ativo na porta {self.discovery_port}")
        self.log(f"[SERVIDOR] Servidor principal ouvindo em {self.server_ip}:{self.port}")
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
        self.update_stats(self.connection_count())
    
    def clear_log(self):
        """Limpa o log da interface"""
        self.log_text.delete(1.0, END)
        self.log("[SERVIDOR] Log limpo pelo usuário")
    
    def on_closing(self):
        """Fecha a interface e avisa o controlador do servidor."""
        if not self.running:
            return
        self.running = False
        if self.on_close_callback:
            self.on_close_callback()
        self.window.destroy()

    def run(self):
        """Executa o loop principal da interface."""
        self.window.mainloop()

