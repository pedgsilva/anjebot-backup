<?php
/**
 * Plugin Name: ChatANJE
 * Description: Chatbot inteligente para www.anje.pt
 * Version: 1.0.0
 * Author: Pedro Silva
 */

if (!defined('ABSPATH')) exit;

class ChatANJE {
    
    private $option_key = 'chatanje_settings';
    
    public function __construct() {
        add_action('wp_enqueue_scripts', [$this, 'enqueue_assets']);
        add_action('wp_footer', [$this, 'render_chatbot'], 100);
        add_action('wp_ajax_chatanje_chat', [$this, 'handle_chat']);
        add_action('wp_ajax_nopriv_chatanje_chat', [$this, 'handle_chat']);
    }
    
    public function enqueue_assets() {
        wp_register_style('chatanje-css', false);
        wp_enqueue_style('chatanje-css');
        wp_add_inline_style('chatanje-css', '
            #chatanje-widget{position:fixed;bottom:20px;right:20px;z-index:999999;font-family:sans-serif}
            #chatanje-toggle{width:60px;height:60px;border-radius:50%;border:none;background:#007bff;color:#fff;cursor:pointer;box-shadow:0 4px 16px rgba(0,123,255,.4);font-size:28px;display:flex;align-items:center;justify-content:center;transition:transform .3s}
            #chatanje-toggle:hover{transform:scale(1.1)}
            #chatanje-window{position:absolute;bottom:75px;right:0;width:380px;max-width:calc(100vw - 40px);height:520px;background:#fff;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.15);display:none;flex-direction:column;overflow:hidden}
            #chatanje-header{background:#007bff;color:#fff;padding:14px 16px;display:flex;align-items:center;gap:10px}
            #chatanje-header-info{flex:1}
            #chatanje-header-info strong{display:block;font-size:14px}
            #chatanje-header-info small{font-size:11px;opacity:.8}
            #chatanje-close{background:none;border:none;color:#fff;font-size:20px;cursor:pointer;padding:4px;opacity:.8}
            #chatanje-messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;background:#f8f9fa}
            .chatanje-msg{max-width:85%;padding:10px 14px;border-radius:12px;font-size:13.5px;line-height:1.55}
            .chatanje-bot{background:#fff;color:#333;align-self:flex-start;border-bottom-left-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
            .chatanje-user{background:#007bff;color:#fff;align-self:flex-end;border-bottom-right-radius:4px}
            .chatanje-bot a{color:#0066cc!important;text-decoration:underline!important;word-break:break-all}
            .chatanje-bot strong{color:#1a1a2e}
            #chatanje-input-area{display:flex;padding:10px 12px;background:#fff;border-top:1px solid #e9ecef;gap:8px}
            #chatanje-input{flex:1;padding:10px 14px;border:1px solid #ddd;border-radius:20px;outline:none;font-size:13.5px}
            #chatanje-input:focus{border-color:#007bff}
            #chatanje-send{width:40px;height:40px;border-radius:50%;border:none;background:#007bff;color:#fff;cursor:pointer;font-size:18px}
            #chatanje-send:hover{background:#0056b3}
            #chatanje-send:disabled{background:#ccc;cursor:not-allowed}
            .chatanze-typing{display:flex;gap:4px;padding:10px 14px;background:#fff;border-radius:12px;align-self:flex-start;box-shadow:0 1px 3px rgba(0,0,0,.08)}
            .chatanze-typing span{width:7px;height:7px;background:#999;border-radius:50%;animation:blink 1.2s infinite}
            .chatanze-typing span:nth-child(2){animation-delay:.2s}
            .chatanze-typing span:nth-child(3){animation-delay:.4s}
            @keyframes blink{0%,80%,100%{opacity:.2}40%{opacity:1}}
            @media(max-width:480px){#chatanje-window{width:calc(100vw - 20px);height:calc(100vh - 100px);right:-10px}}
        ');
    }
    
    public function render_chatbot() {
        $settings = get_option($this->option_key, []);
        $welcome = !empty($settings['welcome_message']) ? $settings['welcome_message'] : "Olá! 👋 Sou o assistente virtual da ANJE.\n\nPosso ajudar com:\n• 🏛️ Sobre a ANJE\n• 👥 Órgãos sociais\n• 📋 Programas\n• 📞 Contactos\n\nO que procura?";
        $ajax_url = admin_url('admin-ajax.php');
        $nonce = wp_create_nonce('chatanje_nonce');
        ?>
        <div id="chatanje-widget">
            <button id="chatanje-toggle">&#128172;</button>
            <div id="chatanje-window" style="display:none;">
                <div id="chatanje-header">
                    <div style="font-size:28px;width:40px;height:40px;background:rgba(255,255,255,.2);border-radius:50%;display:flex;align-items:center;justify-content:center">&#129302;</div>
                    <div id="chatanje-header-info">
                        <strong>ChatBot ANJE</strong>
                        <small>Online</small>
                    </div>
                    <button id="chatanje-close">&#10005;</button>
                </div>
                <div id="chatanje-messages"></div>
                <div id="chatanje-input-area">
                    <input type="text" id="chatanje-input" placeholder="Escreva a sua pergunta..." autocomplete="off">
                    <button id="chatanje-send">&#10148;</button>
                </div>
            </div>
        </div>
        <script>
        (function(){
            var ajaxUrl = '<?php echo $ajax_url; ?>';
            var nonce = '<?php echo $nonce; ?>';
            var welcome = <?php echo json_encode($welcome); ?>;
            var isWaiting = false;
            
            document.getElementById('chatanje-toggle').onclick = function(){
                var win = document.getElementById('chatanje-window');
                if(win.style.display==='flex'){win.style.display='none';this.innerHTML='&#128172;';}
                else{win.style.display='flex';this.innerHTML='&#10005;';document.getElementById('chatanje-input').focus();if(welcome)addMsg(welcome,'bot');}
            };
            
            document.getElementById('chatanje-close').onclick = function(){
                document.getElementById('chatanje-window').style.display='none';
                document.getElementById('chatanje-toggle').innerHTML='&#128172;';
            };
            
            document.getElementById('chatanje-send').onclick = send;
            document.getElementById('chatanje-input').onkeypress = function(e){if(e.key==='Enter')send();};
            
            function send(){
                var inp = document.getElementById('chatanje-input');
                var msg = inp.value.trim();
                if(!msg||isWaiting) return;
                isWaiting = true;
                document.getElementById('chatanje-send').disabled = true;
                addMsg(msg,'user');
                inp.value = '';
                addTyping();
                var xhr = new XMLHttpRequest();
                xhr.open('POST', ajaxUrl);
                xhr.setRequestHeader('Content-Type','application/x-www-form-urlencoded');
                xhr.timeout = 25000;
                xhr.onload = function(){
                    var typing = document.getElementById('typing');
                    if(typing) typing.remove();
                    try{
                        var res = JSON.parse(xhr.responseText);
                        addMsg(res.data.response||'Erro.','bot');
                    }catch(e){addMsg('Erro na resposta.','bot');}
                };
                xhr.onerror = function(){var t=document.getElementById('typing');if(t)t.remove();addMsg('Erro de ligação.','bot');};
                xhr.ontimeout = function(){var t=document.getElementById('typing');if(t)t.remove();addMsg('Timeout.','bot');};
                xhr.onreadystatechange = function(){
                    if(xhr.readyState===4){isWaiting=false;document.getElementById('chatanje-send').disabled=false;inp.focus();}
                };
                xhr.send('action=chatanje_chat&message='+encodeURIComponent(msg)+'&nonce='+nonce);
            }
            
            function addMsg(t,type){
                var d = document.createElement('div');
                d.className = 'chatanje-msg chatanje-'+type;
                d.innerHTML = t.replace(/\\n/g,'<br>');
                document.getElementById('chatanje-messages').appendChild(d);
                d.scrollIntoView({behavior:'smooth'});
            }
            
            function addTyping(){
                var d = document.createElement('div');
                d.className = 'chatanje-msg chatanje-bot';
                d.id = 'typing';
                d.innerHTML = 'A escrever...';
                document.getElementById('chatanje-messages').appendChild(d);
            }
        })();
        </script>
        <?php
    }
    
    public function handle_chat() {
        check_ajax_referer('chatanje_nonce', 'nonce');
        $message = sanitize_text_field($_POST['message'] ?? '');
        if (empty($message)) wp_send_json_error('Vazio', 400);
        
        $settings = get_option($this->option_key, []);
        $api_key = $settings['openrouter_key'] ?? '';
        
        if (empty($api_key)) {
            wp_send_json_success(['response' => '⚠️ Configure a OpenRouter API Key em Definições > ChatANJE']);
        }
        
        $response = wp_remote_post('https://openrouter.ai/api/v1/chat/completions', [
            'timeout' => 25,
            'headers' => ['Authorization' => "Bearer {$api_key}", 'Content-Type' => 'application/json'],
            'body' => json_encode([
                'model' => $settings['model'] ?? 'openrouter/owl-alpha',
                'messages' => [
                    ['role' => 'system', 'content' => $this->get_system_prompt()],
                    ['role' => 'user', 'content' => "Pergunta: {$message}"],
                ],
                'temperature' => 0.1,
                'max_tokens' => 500,
            ]),
        ]);
        
        if (is_wp_error($response)) {
            wp_send_json_success(['response' => 'Erro de ligação.']);
        }
        
        $data = json_decode(wp_remote_retrieve_body($response), true);
        if (isset($data['error'])) {
            wp_send_json_success(['response' => 'Erro: ' . ($data['error']['message'] ?? 'Desconhecido')]);
        }
        
        $reply = $data['choices'][0]['message']['content'] ?? 'Erro na resposta.';
        wp_send_json_success(['response' => $reply]);
    }
    
    private function get_system_prompt() {
        return "És o assistente virtual da ANJE (anje.pt).

SOBRE: A ANJE é uma associação de direito privado e utilidade pública que representa os jovens empresários portugueses. Fundada em 1986.

ÓRGÃOS SOCIAIS:
- Presidente: Carlos Carvalho
- Vice-Presidentes: Nuno Malheiro, Filipa Pinto de Carvalho, Gonçalo Simões de Almeida
- Diretores: Filipe Quinaz, Miguel Teixeira Bastos, Sofia Correia de Sousa, Tiago Araújo, António Fragateiro, Beatriz Almeida
- Presidente Assembleia Geral: Miguel Moreira da Silva
- Presidente Conselho Fiscal: Catarina Azevedo

PROGRAMAS:
- Prémio Jovem Empreendedor
- Rede de Incubação ANJE
- Formação ANJE
- Bolsas de Formadores

PÁGINAS (INCLUI URL COMPLETO):
- Estatutos: https://anje.pt/anje/estatutos/
- Associados: https://anje.pt/associados/
- Incubação: https://anje.pt/incubacao/
- Formação: https://anje.pt/formacao/
- Prémio: https://anje.pt/premio-do-jovem-empreendedor/
- Órgãos Sociais: https://anje.pt/orgaos-sociais/
- Contactos: https://anje.pt/contactos/
- Blog: https://anje.pt/blog/
- Comunicação: https://anje.pt/comunicacao/

REGRAS:
- Português de Portugal
- Se perguntarem quem é o PRESIDENTE: O presidente é Carlos Carvalho
- Se perguntarem ÓRGÃOS SOCIAIS: lista todos os nomes acima
- Usa **negrita** para títulos
- Se não souberes, sugere contactar anje@anje.pt";
    }
}

new ChatANJE();
