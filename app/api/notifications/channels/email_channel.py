import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import logging
from .base_channel import BaseNotificationChannel, NotificationResult

logger = logging.getLogger(__name__)

class EmailChannel(BaseNotificationChannel):
    """Canal de notificação por email"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.from_email = config.get('from_email', self.username)
        self.from_name = config.get('from_name', 'Sistema Mensura')
        
        if not self.validate_config(config):
            raise ValueError("Configuração inválida para canal de email")
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Valida a configuração do canal de email"""
        required_fields = ['username', 'password']
        return all(field in config for field in required_fields)
    
    def get_channel_name(self) -> str:
        return "email"
    
    async def send(
        self,
        recipient: str,
        title: str,
        message: str,
        channel_metadata: Optional[Dict[str, Any]] = None
    ) -> NotificationResult:
        """Envia email"""
        try:
            # Cria a mensagem
            msg = MIMEMultipart('alternative')
            msg['Subject'] = title
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient
            
            # Adiciona o corpo da mensagem
            text_content = message
            html_content = self._create_html_content(title, message, channel_metadata)
            
            # Adiciona as partes da mensagem
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Envia o email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)
            
            self._log_success(recipient)
            return self._create_success_result("Email enviado com sucesso")
            
        except Exception as e:
            error_msg = f"Erro ao enviar email: {str(e)}"
            self._log_error(recipient, error_msg)
            return self._create_error_result(error_msg, {"exception": str(e)})
    
    def _create_html_content(self, title: str, message: str, channel_metadata: Optional[Dict[str, Any]] = None) -> str:
        """Cria conteúdo HTML para o email"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
                .content { padding: 20px; }
                .footer { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{title}</h2>
                </div>
                <div class="content">
                    {message}
                </div>
                <div class="footer">
                    <p>Esta é uma mensagem automática do sistema Mensura.</p>
                    <p>Por favor, não responda a este email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template.format(title=title, message=message.replace('\n', '<br>'))
