<?php
/**
 * Plugin Name: ChatANJE
 * Description: Chatbot inteligente para www.anje.pt - órgãos sociais, programas, contactos
 * Version: 3.0.0
 * Author: Pedro Silva
 * Text Domain: chatanje
 */

if (!defined('ABSPATH')) exit;

class ChatANJE {
    
    private $option_key = 'chatanje_settings';
    
    public function __construct() {
        add_action('wp_enqueue_scripts', [$this, 'enqueue_assets']);
        add_action('wp_footer', [$this, 'render_chatbot'], 100);
        add_action('admin_menu', [$this, 'add_admin_menu']);
        add_action('admin_init', [$this, 'register_settings']);
        add_action('wp_ajax_chatanje_chat', [$this, 'handle_chat']);
        add_action('wp_ajax_nopriv_chatanje_chat', [$this, 'handle_chat']);
    }
    
    public function enqueue_assets() {
        wp_register_style('chatanje-css', false);
        wp_enqueue_style('chatanje-css');
        wp_add_inline_style('chatanje-css', '
            #chatanje-widget{position:fixed;bottom:20px;right:20px;z-index:999999;font-family:sans-serif}
            #chatanje-toggle{width:60px;height:60px;border-radius:50%;border:none;background:#007bff;color:#fff;cursor:pointer;box-shadow:0 4px 16px rgba(0,123,255,.4);font-size:28px;display:flex;align-items:center;justify-content:center}
            #chatanje-window{position:absolute;bottom:75px;right:0;width:380px;height:520px;background:#fff;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.15);display:none;flex-direction:column;overflow:hidden}
            #chatanje-header{background:#007bff;color:#fff;padding:14px;display:flex;align-items:center;gap:10px}
            #chatanje-header strong{display:block;font-size:14px}
            #chatanje-header small{font-size:11px;opacity:.8}
            #chatanje-header-info{flex:1}
            #chatanje-close{background:none;border:none;color:#fff;font-size:20px;cursor:pointer;opacity:.8}
            #chatanje-messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:10px;background:#f8f9fa}
            .c-msg{max-width:85%;padding:10px 14px;border-radius:12px;font-size:13.5px;line-height:1.55;word-wrap:break-word}
            .c-bot{background:#fff;color:#333;align-self:flex-start}
            .c-user{background:#007bff;color:#fff;align-self:flex-end}
            .c-bot a{color:#0066cc!important;text-decoration:underline!important}
            .c-bot strong{color:#1a1a2e}
            #chatanje-input-area{display:flex;padding:10px;background:#fff;border-top:1px solid #ddd;gap:8px}
            #chatanje-input{flex:1;padding:10px;border:1px solid #ddd;border-radius:20px;outline:none;font-size:13.5px}
            #chatanje-send{width:40px;height:40px;border-radius:50%;border:none;background:#007bff;color:#fff;cursor:pointer;font-size:18px}
            #chatanje-send:disabled{background:#ccc}
            @media(max-width:480px){#chatanje-window{width:calc(100vw - 20px);height:calc(100vh - 100px);right:-10px}}
        ');
    }
    
    public function render_chatbot() {
        $welcome = "Olá! 👋 Sou o assistente virtual da ANJE.\n\nPosso ajudar com:\n• 🏛️ Sobre a ANJE\n• 👥 Órgãos sociais\n• 📋 Programas\n• 📞 Contactos\n• 🔗 Páginas do site\n\nO que procura?";
        $ajax = admin_url('admin-ajax.php');
        $nonce = wp_create_nonce('chatanje_nc');
        ?>
        <div id="chatanje-widget">
            <button id="chatanje-toggle">&#128172;</button>
            <div id="chatanje-window">
                <div id="chatanje-header">
                    <strong>ChatBot ANJE</strong>
                    <small style="opacity:.8">Online</small>
                    <div style="flex:1"></div>
                    <button id="chatanje-close">&#10005;</button>
                </div>
                <div id="chatanje-messages"></div>
                <div id="chatanje-input-area">
                    <input type="text" id="chatanje-input" placeholder="Escreva a sua pergunta...">
                    <button id="chatanje-send">&#10148;</button>
                </div>
            </div>
        </div>
        <script>
        (function(){
            var ajaxUrl="<?php echo $ajax; ?>";
            var nonce="<?php echo $nonce; ?>";
            var welcome=<?php echo json_encode($welcome); ?>;
            var busy=false;
            var shown=false;
            
            document.getElementById('chatanje-toggle').onclick=function(){
                var w=document.getElementById('chatanje-window');
                if(w.style.display==='flex'){w.style.display='none';}
                else{w.style.display='flex';document.getElementById('chatanje-input').focus();if(!shown&&welcome){addMsg(welcome,'bot');shown=true;}}
            };
            document.getElementById('chatanje-close').onclick=function(){document.getElementById('chatanje-window').style.display='none';};
            document.getElementById('chatanje-send').onclick=send;
            document.getElementById('chatanje-input').onkeypress=function(e){if(e.key==='Enter')send();};
            
            function send(){
                var inp=document.getElementById('chatanje-input');
                var msg=inp.value.trim();
                if(!msg||busy)return;
                busy=true;
                document.getElementById('chatanje-send').disabled=true;
                addMsg(msg,'user');
                inp.value='';
                addTyping();
                var xhr=new XMLHttpRequest();
                xhr.open('POST',ajaxUrl);
                xhr.setRequestHeader('Content-Type','application/x-www-form-urlencoded');
                xhr.timeout=25000;
                xhr.onload=function(){
                    var t=document.getElementById('typing');if(t)t.remove();
                    try{var r=JSON.parse(xhr.responseText);addMsg(r.data.response||'Erro.','bot');}catch(e){addMsg('Erro.','bot');}
                };
                xhr.onerror=function(){var t=document.getElementById('typing');if(t)t.remove();addMsg('Erro ligação.','bot');};
                xhr.ontimeout=function(){var t=document.getElementById('typing');if(t)t.remove();addMsg('Timeout.','bot');};
                xhr.onreadystatechange=function(){if(xhr.readyState===4){busy=false;document.getElementById('chatanje-send').disabled=false;inp.focus();}};
                xhr.send('action=chatanje_chat&message='+encodeURIComponent(msg)+'&nonce='+nonce);
            }
            
            function addMsg(t,type){
                var d=document.createElement('div');
                d.className='c-msg c-'+type;
                d.innerHTML=t.replace(/\\n/g,'<br>').replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>');
                document.getElementById('chatanje-messages').appendChild(d);
                d.scrollIntoView({behavior:'smooth'});
            }
            function addTyping(){
                var d=document.createElement('div');
                d.className='c-msg c-bot';
                d.id='typing';
                d.textContent='A escrever...';
                document.getElementById('chatanje-messages').appendChild(d);
            }
        })();
        </script>
        <?php
    }
    
    public function handle_chat() {
        check_ajax_referer('chatanje_nc','nonce');
        $msg=sanitize_text_field($_POST['message']??'');
        if(empty($msg))wp_send_json_error('Vazio',400);
        
        $s=get_option($this->option_key,[]);
        $key=$s['openrouter_key']??'';
        
        if(empty($key)){
            wp_send_json_success(['response'=>'⚠️ Configure a OpenRouter API Key em <a href="'.admin_url('options-general.php?page=chatanje').'">Definições > ChatANJE</a>']);
        }
        
        $r=wp_remote_post('https://openrouter.ai/api/v1/chat/completions',[
            'timeout'=>25,
            'headers'=>['Authorization'=>"Bearer {$key}",'Content-Type'=>'application/json'],
            'body'=>json_encode([
                'model'=>$s['model']??'openrouter/owl-alpha',
                'messages'=>[
                    ['role'=>'system','content'=>$this->get_prompt()],
                    ['role'=>'user','content'=>"Pergunta: {$msg}"],
                ],
                'temperature'=>0.1,
                'max_tokens'=>500,
            ]),
        ]);
        
        if(is_wp_error($r))wp_send_json_success(['response'=>'Erro de ligação.']);
        $d=json_decode(wp_remote_retrieve_body($r),true);
        if(isset($d['error']))wp_send_json_success(['response'=>'Erro: '.($d['error']['message']??'Desconhecido')]);
        wp_send_json_success(['response'=>$d['choices'][0]['message']['content']??'Erro.']);
    }
    
    private function get_prompt(){
        return "És o assistente virtual da ANJE (anje.pt).

SOBRE: A ANJE é uma associação de direito privado e utilidade pública que representa os jovens empresários portugueses. Fundada em 1986.

ÓRGÃOS SOCIAIS:
- Presidente: Carlos Carvalho
- Vice-Presidentes: Nuno Malheiro, Filipa Pinto de Carvalho, Gonçalo Simões de Almeida
- Diretores: Filipe Quinaz, Miguel Teixeira Bastos, Sofia Correia de Sousa, Tiago Araújo, António Fragateiro, Beatriz Almeida
- Presidente Assembleia Geral: Miguel Moreira da Silva
- Presidente Conselho Fiscal: Catarina Azevedo

PROGRAMAS: Prémio Jovem Empreendedor, Rede de Incubação, Formação, Bolsas de Formadores

PÁGINAS (INCLUI URL COMPLETO NAS RESPOSTAS):
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
- Se perguntarem quem é o PRESIDENTE: responde 'O presidente da ANJE é Carlos Carvalho'
- Se perguntarem ÓRGÃOS SOCIAIS: lista todos os nomes
- Usa **negrita** para títulos
- Inclui sempre o URL completo quando fala de uma página
- Se não souberes, sugere contactar anje@anje.pt";
    }
    
    public function add_admin_menu(){
        add_options_page('ChatANJE','ChatANJE','manage_options','chatanje',[$this,'admin_page']);
    }
    
    public function register_settings(){
        register_setting('chatanje_grp',$this->option_key);
    }
    
    public function admin_page(){
        $s=get_option($this->option_key,[]);
        ?>
        <div class="wrap">
            <h1>🤖 ChatANJE - Configurações</h1>
            <form method="post" action="options.php">
                <?php settings_fields('chatanje_grp');?>
                <table class="form-table">
                    <tr>
                        <th><label>OpenRouter API Key</label></th>
                        <td>
                            <input type="password" name="chatanje_settings[openrouter_key]" value="<?php echo esc_attr($s['openrouter_key']??'');?>" class="regular-text" placeholder="sk-or-...">
                            <p class="description">Obter em <a href="https://openrouter.ai/keys" target="_blank">openrouter.ai</a></p>
                        </td>
                    </tr>
                    <tr>
                        <th><label>Modelo LLM</label></th>
                        <td>
                            <input type="text" name="chatanje_settings[model]" value="<?php echo esc_attr($s['model']??'openrouter/owl-alpha');?>" class="regular-text">
                            <p class="description">Ex: openrouter/owl-alpha, anthropic/claude-sonnet-4</p>
                        </td>
                    </tr>
                </table>
                <?php submit_button('Guardar');?>
            </form>
            <hr>
            <h2>Estado</h2>
            <table class="widefat" style="max-width:400px">
                <tr><td>API Key</td><td><?php echo !empty($s['openrouter_key'])?'<span style="color:green">✓ Configurada</span>':'<span style="color:red">✗ Não configurada</span>';?></td></tr>
            </table>
        </div>
        <?php
    }
}

new ChatANJE();
