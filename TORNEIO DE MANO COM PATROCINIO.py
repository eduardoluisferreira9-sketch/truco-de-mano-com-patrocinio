import streamlit as st
import pandas as pd
import random
import json
import os
import qrcode
import socket
from io import BytesIO
from datetime import datetime, timedelta

st.set_page_config(
    page_title="Sistema de Torneios de Truco de Mano",
    page_icon="🏆",
    layout="centered"
)

NOME_CRIADOR = "Eduardo Luis Ferreira"
ARQUIVO_BACKUP = "torneio_atual.json"
ARQUIVO_GALERIA = "galeria_campeoes.json"

CHAVE_ADMINISTRADOR = "truco123"

# ==========================================
# 🎯 BANCO DE DADOS DE PATROCINADORES CORRIGIDO (PNG/JPG ESTÁVEIS)
# ==========================================
PATROCINADORES = {
    "master": {
        "nome": "Sicredi",
        # Link corrigido para um arquivo PNG estelar de alta resolução (sem bloqueio)
        "logo": "https://upload.wikimedia.org/wikipedia/commons/e/e3/Logo_Sicredi.png", 
    },
    "mesas": [
        {"nome": "Sicredi", "logo": "https://upload.wikimedia.org/wikipedia/commons/e/e3/Logo_Sicredi.png"},
        {"nome": "Coca-Cola", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/ce/Coca-Cola_logo_PNG1.png/240px-Coca-Cola_logo_PNG1.png"},
        {"nome": "Salgadinho", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/31/Pringles_New_Logo.svg/220px-Pringles_New_Logo.svg.png"}, 
        {"nome": "Barbearia", "logo": "https://i.imgur.com/KdfGvQG.jpg"},
        {"nome": "Churrascaria", "logo": "https://i.imgur.com/vHkaVIn.jpg"}
    ]
}

# --- FUNÇÕES DE SALVAMENTO E RECUPERAÇÃO ---
def salvar_estado_no_disco():
    estado = {
        "jogadores": st.session_state.jogadores,
        "torneio_iniciado": st.session_state.torneio_iniciado,
        "rodada_atual": st.session_state.rodada_atual,
        "confrontos": st.session_state.confrontos,
        "jogadores_no_chapeu": list(st.session_state.jogadores_no_chapeu),
        "hora_inicio_rodada": st.session_state.hora_inicio_rodada.isoformat() if st.session_state.hora_inicio_rodada else None,
        "cronometro_ativo": st.session_state.cronometro_ativo,
        "historico_rodadas": st.session_state.historico_rodadas,
        "nome_torneio": st.session_state.get("nome_torneio", "Torneio de Truco do CTG"),
        "em_matamata": st.session_state.em_matamata,
        "fase_matamata": st.session_state.fase_matamata,
        "confrontos_mm": st.session_state.confrontos_mm,
        "campeao": st.session_state.campeao,
        "vice_campeao": st.session_state.vice_campeao,
        "terceiro_lugar": st.session_state.terceiro_lugar,
        "quarto_lugar": st.session_state.quarto_lugar,
        "perdedores_semi": st.session_state.perdedores_semi,
        "salvo_na_galeria": st.session_state.get("salvo_na_galeria", False)
    }
    if st.session_state.classificacao is not None:
        estado["classificacao"] = st.session_state.classificacao.to_dict(orient="index")
    else:
        estado["classificacao"] = None
        
    with open(ARQUIVO_BACKUP, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=4)

def carregar_estado_do_disco():
    if os.path.exists(ARQUIVO_BACKUP):
        try:
            with open(ARQUIVO_BACKUP, "r", encoding="utf-8") as f:
                estado = json.load(f)
            
            st.session_state.jogadores = estado.get("jogadores", [])
            st.session_state.torneio_iniciado = estado.get("torneio_iniciado", False)
            st.session_state.rodada_atual = estado.get("rodada_atual", 1)
            st.session_state.confrontos = estado.get("confrontos", [])
            st.session_state.jogadores_no_chapeu = set(estado.get("jogadores_no_chapeu", []))
            st.session_state.historico_rodadas = estado.get("historico_rodadas", {})
            st.session_state.nome_torneio = estado.get("nome_torneio", "Torneio de Truco do CTG")
            st.session_state.em_matamata = estado.get("em_matamata", False)
            st.session_state.fase_matamata = estado.get("fase_matamata", "")
            st.session_state.confrontos_mm = estado.get("confrontos_mm", [])
            st.session_state.campeao = estado.get("campeao", None)
            st.session_state.vice_campeao = estado.get("vice_campeao", None)
            st.session_state.terceiro_lugar = estado.get("terceiro_lugar", None)
            st.session_state.quarto_lugar = estado.get("quarto_lugar", None)
            st.session_state.perdedores_semi = estado.get("perdedores_semi", [])
            st.session_state.salvo_na_galeria = estado.get("salvo_na_galeria", False)
            st.session_state.cronometro_ativo = estado.get("cronometro_ativo", False)
            
            if estado.get("hora_inicio_rodada"):
                st.session_state.hora_inicio_rodada = datetime.fromisoformat(estado["hora_inicio_rodada"])
            else:
                st.session_state.hora_inicio_rodada = None
                
            if estado.get("classificacao") is not None:
                st.session_state.classificacao = pd.DataFrame.from_dict(estado["classificacao"], orient="index")
            else:
                st.session_state.classificacao = None
        except Exception:
            pass

def salvar_na_galeria(torneio, campeao, vice, terceiro, quarto, rei_flores, qtd_flores):
    registros = []
    if os.path.exists(ARQUIVO_GALERIA):
        try:
            with open(ARQUIVO_GALERIA, "r", encoding="utf-8") as f:
                registros = json.load(f)
        except Exception:
            registros = []
            
    novo_registro = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "torneio": torneio,
        "campeao": campeao,
        "vice": vice,
        "terceiro": terceiro,
        "quarto": quarto,
        "rei_flores": f"{rei_flores} ({qtd_flores} fl.)"
    }
    registros.insert(0, novo_registro)
    with open(ARQUIVO_GALERIA, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=4)

# --- INICIALIZAÇÃO DE MEMÓRIA ---
valores_padrao = {
    "jogadores": [],
    "torneio_iniciado": False,
    "rodada_atual": 1,
    "classificacao": None,
    "confrontos": [],
    "jogadores_no_chapeu": set(),
    "hora_inicio_rodada": None,
    "cronometro_ativo": False,
    "historico_rodadas": {},
    "em_matamata": False,
    "fase_matamata": "",
    "confrontos_mm": [],
    "campeao": None,
    "vice_campeao": None,
    "terceiro_lugar": None,
    "quarto_lugar": None,
    "perdedores_semi": [],
    "salvo_na_galeria": False
}

for chave, valor in valores_padrao.items():
    if chave not in st.session_state:
        st.session_state[chave] = valor

if os.path.exists(ARQUIVO_BACKUP):
    carregar_estado_do_disco()

# --- ESTILIZAÇÃO CSS ATUALIZADA ---
st.markdown("""
    <style>
    .stApp { background-color: #1b4d3e; }
    h1, h2, h3, h4, p, label, .stMarkdown { color: #ffffff !important; }
    .stButton>button {
        background-color: #d4af37 !important; color: #111111 !important;
        font-weight: bold !important; border-radius: 8px !important; width: 100%;
    }
    
    /* Box das Mesas Ajustada para Logos */
    .card-mesa { 
        background-color: #2c6b56; 
        padding: 12px 20px; 
        border-radius: 10px; 
        margin-bottom: 15px; 
        border: 1px solid #d4af37;
        display: flex;
        justify-content: space-between;
        align-items: center;
        min-height: 65px;
    }
    .texto-mesa-box {
        font-size: 1.15rem;
        font-weight: bold;
    }
    .tag-patrocinio-img {
        max-height: 32px;
        max-width: 110px;
        width: auto;
        background-color: #ffffff;
        padding: 4px 8px;
        border-radius: 6px;
        object-fit: contain;
    }
    
    .card-historico { background-color: #14382d; padding: 10px; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid #d4af37; }
    .cronometro-box { background-color: #11221a; border: 2px solid #d4af37; padding: 10px; border-radius: 8px; text-align: center; font-family: 'Courier New', Courier, monospace; margin-bottom: 15px; }
    .box-campeao { background-color: #d4af37; padding: 25px; border-radius: 15px; text-align: center; color: #111111 !important; border: 3px solid #ffffff; margin-bottom: 15px; }
    .podio-posicao { padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 10px; color: #ffffff !important; }
    .podio-vice { background-color: #a0a0a0; border: 2px solid #d1d1d1; }
    .podio-terceiro { background-color: #cd7f32; border: 2px solid #e5a65d; }
    .podio-quarto { background-color: #2c6b56; border: 2px solid #d4af37; }
    .box-flores { background-color: #4a1525; padding: 15px; border-radius: 10px; text-align: center; color: #ffffff !important; border: 2px solid #ff4b4b; margin-top: 15px; margin-bottom: 20px; }
    .creditos { text-align: center; color: #a0c0b5 !important; font-size: 0.8rem; margin-top: 50px; }
    
    /* Espaço Patrocinador Master Topo */
    .banner-master {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        border: 3px solid #d4af37;
        margin-bottom: 25px;
    }
    .banner-master img {
        max-height: 48px;
        width: auto;
        object-fit: contain;
    }
    </style>
""", unsafe_allow_html=True)

# --- GERADOR AUTOMÁTICO DE LINK DE REDE ---
def obter_ip_da_rede():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return f"http://{ip}:8501"
    except Exception:
        return "http://localhost:8501"

url_oficial = obter_ip_da_rede()

# --- CONTROLE DE ACESSO E SIDEBAR COMMERCIAL ---
st.sidebar.markdown("### 🔐 Controle de Acesso")
senha_inserida = st.sidebar.text_input("Chave do Operador:", type="password")
is_admin = (senha_inserida == CHAVE_ADMINISTRADOR)

if is_admin:
    st.sidebar.success("⚡ Modo Administrador Ativo")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🌐 Link de Acesso Público")
    
    url_torneio = st.sidebar.text_input("Link Atual:", value=st.session_state.get("url_override", url_oficial))
    st.session_state["url_override"] = url_torneio
    
    st.sidebar.markdown("**Compartilhar no WhatsApp:**")
    st.sidebar.code(url_torneio, language="text")
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url_torneio)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img_qr.save(buf, format="PNG")
    st.sidebar.image(buf.getvalue(), caption="Jogadores: Escaneiem para abrir!", use_container_width=True)
else:
    st.sidebar.info("👁️ Modo Visualizador Público")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🤝 Parceiro de Destaque")
    st.sidebar.markdown(f"""
        <div style="background-color: #ffffff; padding: 15px; border-radius: 8px; text-align: center; border: 2px solid #d4af37;">
            <p style="color: #1b4d3e !important; font-weight: bold; font-size:0.8rem; margin-bottom: 10px;">APOIO EXCLUSIVO</p>
            <img src="{PATROCINADORES['master']['logo']}" style="max-width: 90%; height: auto; max-height: 40px; object-fit: contain;">
            <p style="color: #444444 !important; font-size: 0.75rem; margin-top: 10px; margin-bottom:0;">Valorize quem apoia o esporte tradicionalista local!</p>
        </div>
    """, unsafe_allow_html=True)

# --- TRAVA MATEMÁTICA ---
def conferir_e_ajustar_valores(s1, s2, t1, t2, n1, n2, mesa_id):
    if (s1 == 2 and s2 == 2) or (s1 < 2 and s2 < 2):
        return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Placar de Sets inválido ({s1}x{s2}). Alguém precisa fechar com exatamente 2 sets."

    if s1 == 2 and s2 == 0:
        t1 = 72 
        if t2 > 46:
            return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Inconsistência! No 2x0, o perdedor ({n2}) não pode somar mais do que 46 tentos."

    elif s2 == 2 and s1 == 0:
        t2 = 72 
        if t1 > 46:
            return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Inconsistência! No 2x0, o perdedor ({n1}) não pode somar mais do que 46 tentos."

    elif s1 == 2 and s2 == 1:
        if t1 < 48:
            return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Inconsistência! Como {n1} fez 2 sets, ele precisa ter no mínimo 48 tentos."
        if t2 < 24:
            return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Inconsistência! Como {n2} fez 1 set, ele precisa ter no mínimo 24 tentos."

    elif s2 == 2 and s1 == 1:
        if t2 < 48:
            return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Inconsistência! Como {n2} fez 2 sets, ele precisa ter no mínimo 48 tentos."
        if t1 < 24:
            return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Inconsistência! Como {n1} fez 1 set, ele precisa ter no mínimo 24 tentos."

    return False, s1, s2, t1, t2, ""

# --- FUNÇÕES DE LÓGICA DE RODADA ---
def gerar_rodada_web():
    if st.session_state.rodada_atual == 1:
        lista_rodada = list(st.session_state.jogadores)
        random.shuffle(lista_rodada)
    else:
        df_ord = st.session_state.classificacao.sort_values(by=['Vitorias', 'Sets_Ganhos', 'Saldo_Tentos'], ascending=False)
        lista_rodada = list(df_ord.index)

    st.session_state.confrontos = []
    if len(lista_rodada) % 2 != 0:
        cand = [j for j in lista_rodada if j not in st.session_state.jogadores_no_chapeu]
        chapeu = random.choice(cand if cand else lista_rodada)
        lista_rodada.remove(chapeu)
        st.session_state.jogadores_no_chapeu.add(chapeu)
        st.session_state.confrontos.append((chapeu, "CHAPÉU (Folga)"))

    for i in range(0, len(lista_rodada), 2):
        st.session_state.confrontos.append((lista_rodada[i], lista_rodada[i+1]))
        
    st.session_state.hora_inicio_rodada = None
    st.session_state.cronometro_ativo = False
    salvar_estado_no_disco()

def iniciar_fase_matamata(lista_jogadores, nome_fase):
    st.session_state.em_matamata = True
    st.session_state.fase_matamata = nome_fase
    st.session_state.confrontos_mm = []
    n = len(lista_jogadores)
    for i in range(n // 2):
        st.session_state.confrontos_mm.append({"tipo": "normal", "j1": lista_jogadores[i], "j2": lista_jogadores[n - 1 - i]})
    st.session_state.hora_inicio_rodada = None
    st.session_state.cronometro_ativo = False
    salvar_estado_no_disco()

# --- CONTEÚDO PRINCIPAL ---
st.title("🏆 Painel Interativo de Truco")

# 🌟 BANNER MASTER SUPERIOR CORRIGIDO COM IMAGEM PNG DIRETA
st.markdown(f"""
    <div class="banner-master">
        <img src="{PATROCINADORES['master']['logo']}">
        <p style="color: #2e7d32 !important; font-weight: bold; font-size: 0.8rem; margin: 8px 0 0 0; letter-spacing: 1.5px;">PATROCINADOR MASTER COOPERATIVO</p>
    </div>
""", unsafe_allow_html=True)

if not st.session_state.torneio_iniciado and is_admin:
    st.info(f"📢 **COMO FAZER OS JOGADORES ENTRAREM PELO CELULAR AGORA:**\n\n"
            f"1. Ligue o **Ponto de Acesso/Roteador** do seu celular e conecte o seu notebook a ele.\n"
            f"2. Peça para os jogadores se conectarem ao **mesmo Wi-Fi**.\n"
            f"3. Pronto! Eles só precisam ler o QR Code da barra lateral ou acessar: `{url_oficial}`")

# === TELA 1: CADASTRO / CONFIGURAÇÃO DO TORNEIO ===
if not st.session_state.torneio_iniciado:
    aba1, aba2 = st.tabs(["🎮 Painel de Inscrições", "📜 Galeria de Campeões"])
    
    with aba1:
        st.markdown("### 🎪 Identificação do Evento")
        if is_admin:
            nome_torneio = st.text_input("Nome do Torneio ou CTG:", value=st.session_state.get("nome_torneio", "Torneio de Truco do CTG"))
        else:
            st.markdown(f"**{st.session_state.get('nome_torneio', 'Torneio de Truco do CTG')}**")
        
        st.markdown("---")
        st.markdown("### 👤 Cadastro de Jogadores")
        
        if is_admin:
            with st.form(key="form_cadastro", clear_on_submit=True):
                novo_jogador = st.text_input("Nome do Jogador:")
                if st.form_submit_button("➕ Adicionar Jogador") and novo_jogador:
                    name_clean = novo_jogador.strip()
                    if name_clean in st.session_state.jogadores:
                        st.warning(f"⚠️ O jogador '{name_clean}' já está inscrito!")
                    elif name_clean != "":
                        st.session_state.jogadores.append(name_clean)
                        salvar_estado_no_disco()
                        st.success(f"🃏 {name_clean} adicionado!")
                        st.rerun()
        else:
            st.info("🔒 O cadastro de jogadores está fechado para o público.")

        total_inscritos = len(st.session_state.jogadores)
        st.markdown(f"**Inscritos atuais: {total_inscritos} / 64**")
        st.write(", ".join(st.session_state.jogadores))
        
        if is_admin and total_inscritos > 0:
            jogador_remover = st.selectbox("Selecione para remover:", [""] + st.session_state.jogadores)
            if st.button("❌ Remover Jogador Selecionado") and jogador_remover:
                st.session_state.jogadores.remove(jogador_remover)
                salvar_estado_no_disco()
                st.rerun()
                    
        st.markdown("---")
        if is_admin and total_inscritos >= 4:
            if st.button("🃏 INICIAR CLASSIFICATÓRIA (5 RODADAS) 🃏"):
                st.session_state.nome_torneio = nome_torneio
                st.session_state.classificacao = pd.DataFrame({
                    'Jogador': st.session_state.jogadores,
                    'Vitorias': 0, 'Sets_Ganhos': 0, 'Tentos_Pro': 0, 'Tentos_Contra': 0, 'Saldo_Tentos': 0, 'Flores': 0
                }).set_index('Jogador')
                st.session_state.torneio_iniciado = True
                st.session_state.em_matamata = False
                st.session_state.campeao = None
                gerar_rodada_web()
                st.rerun()
                
    with aba2:
        st.markdown("### 🏛️ Registro de Campeões")
        if is_admin:
            if os.path.exists(ARQUIVO_GALERIA):
                if st.button("🗑️ Limpar Todo o Histórico da Galeria", type="primary"):
                    try:
                        os.remove(ARQUIVO_GALERIA)
                        st.success("Galeria de campeões apagada com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao limpar galeria: {e}")

        if os.path.exists(ARQUIVO_GALERIA):
            with open(ARQUIVO_GALERIA, "r", encoding="utf-8") as f:
                dados_galeria = json.load(f)
            if dados_galeria:
                df_galeria = pd.DataFrame(dados_galeria)
                df_galeria.columns = ["📅 Data/Hora", "🏟️ Torneio", "🥇 Campeão", "🥈 Vice", "🥉 3º Lugar", "🎖️ 4º Lugar", "🌸 Rei das Flores"]
                st.dataframe(df_galeria, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum registro encontrado na galeria ainda.")
        else:
            st.info("A galeria de honra está limpa.")

# === TELA 2: ANDAMENTO DO TORNEIO ===
else:
    st.markdown(f"### 🏟️ {st.session_state.nome_torneio}")
    
    if st.session_state.campeao:
        st.markdown("<h2 style='text-align: center; color: #d4af37 !important;'>✨ CERIMÔNIA DE PREMIAÇÃO FINAL ✨</h2>", unsafe_allow_html=True)
        rei_das_flores = st.session_state.classificacao.sort_values(by='Flores', ascending=False).index[0]
        max_flores = int(st.session_state.classificacao.loc[rei_das_flores, 'Flores'])
            
        if not st.session_state.get("salvo_na_galeria", False):
            salvar_na_galeria(st.session_state.nome_torneio, st.session_state.campeao, st.session_state.vice_campeao, st.session_state.terceiro_lugar, st.session_state.quarto_lugar, rei_das_flores, max_flores)
            st.session_state.salvo_na_galeria = True
            salvar_estado_no_disco()
        
        st.markdown(f'<div class="box-campeao"><h1>🥇 1º LUGAR - CAMPEÃO 🥇</h1><h2>🌟 {st.session_state.campeao} 🌟</h2></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="podio-posicao podio-vice">🥈 2º LUGAR: {st.session_state.vice_campeao}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="podio-posicao podio-terceiro">🥉 3º LUGAR: {st.session_state.terceiro_lugar}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="podio-posicao podio-quarto">🎖️ 4º LUGAR: {st.session_state.quarto_lugar}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="box-flores">🌸 REI DAS FLORES: {rei_das_flores} ({max_flores} fl.)</div>', unsafe_allow_html=True)
        
        if is_admin and st.button("🏁 Novo Torneio (Limpar Tudo)"):
            if os.path.exists(ARQUIVO_BACKUP): os.remove(ARQUIVO_BACKUP)
            jsalvos = list(st.session_state.jogadores)
            st.session_state.clear()
            st.session_state.jogadores = jsalvos
            st.rerun()

    elif st.session_state.em_matamata:
        st.markdown(f"#### ⚡ Fase: {st.session_state.fase_matamata}")
        
        if st.session_state.cronometro_ativo and st.session_state.hora_inicio_rodada:
            tempo_limite = st.session_state.hora_inicio_rodada + timedelta(minutes=45)
            tempo_atual = datetime.now()
            if tempo_atual < tempo_limite:
                tempo_restante = tempo_limite - tempo_atual
                minutos, segundos = int(tempo_restante.total_seconds() // 60), int(tempo_restante.total_seconds() % 60)
                st.markdown(f'<div class="cronometro-box"><h3 style="margin:0; color:#d4af37 !important;">⏱️ TEMPO RESTANTE DO MATA-MATA: {minutos:02d}:{segundos:02d}</h3></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="cronometro-box"><h3 style="margin:0; color:#ff4b4b !important;">⏰ TEMPO ESGOTADO NESTA FASE!</h3></div>', unsafe_allow_html=True)
            
            if is_admin:
                c_c1, c_c2 = st.columns(2)
                with c_c1:
                    if st.button("⏹️ Resetar Tempo"):
                        st.session_state.hora_inicio_rodada = None
                        st.session_state.cronometro_ativo = False
                        salvar_estado_no_disco()
                        st.rerun()
                with c_c2:
                    if st.button("🔓 Conceder +5 Minutos"):
                        st.session_state.hora_inicio_rodada += timedelta(minutes=5)
                        salvar_estado_no_disco()
                        st.rerun()
        else:
            st.markdown('<div class="cronometro-box"><h3 style="margin:0; color:#a0a0a0 !important;">⏱️ CRONÔMETRO PAUSADO / AGUARDANDO INÍCIO</h3></div>', unsafe_allow_html=True)
            if is_admin and st.button("▶️ DISPARAR CRONÔMETRO (45 MIN)"):
                st.session_state.hora_inicio_rodada = datetime.now()
                st.session_state.cronometro_ativo = True
                salvar_estado_no_disco()
                st.rerun()
        
        if is_admin:
            with st.form(key=f"mm_form_{st.session_state.fase_matamata}"):
                resultados_fase = []
                for idx, confronto in enumerate(st.session_state.confrontos_mm):
                    j1, j2 = confronto["j1"], confronto["j2"]
                    texto_mesa = "🏆 GRANDE FINAL" if st.session_state.fase_matamata == "FINAIS" and not confronto.get("tipo") == "bronze" else ("🥉 DISPUTA DO 3º LUGAR" if confronto.get("tipo") == "bronze" else f"Mesa {idx+1}")
                    patro_url = PATROCINADORES["mesas"][idx % len(PATROCINADORES["mesas"])]["logo"]
                    
                    st.markdown(f'<div class="card-mesa"><span class="texto-mesa-box">{texto_mesa}</span><img src="{patro_url}" class="tag-patrocinio-img"></div>', unsafe_allow_html=True)
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**{j1}**")
                        s1 = st.number_input("Sets:", min_value=0, max_value=2, step=1, key=f"mm_s1_{idx}")
                        t1 = st.number_input("Tentos:", min_value=0, max_value=72, step=1, key=f"mm_t1_{idx}")
                        f1 = st.number_input("Flores:", min_value=0, max_value=20, step=1, key=f"mm_f1_{idx}")
                    with c2:
                        st.markdown(f"**{j2}**")
                        s2 = st.number_input("Sets:", min_value=0, max_value=2, step=1, key=f"mm_s2_{idx}")
                        t2 = st.number_input("Tentos:", min_value=0, max_value=72, step=1, key=f"mm_t2_{idx}")
                        f2 = st.number_input("Flores:", min_value=0, max_value=20, step=1, key=f"mm_f2_{idx}")
                    resultados_fase.append({"j1": j1, "j2": j2, "s1": s1, "s2": s2, "t1": t1, "t2": t2, "f1": f1, "f2": f2, "is_bronze": confronto.get("tipo") == "bronze", "mesa": idx+1})
                
                if st.form_submit_button("💾 COMPUTAR RESULTADOS"):
                    sucesso_validacao = True
                    dados_ajustados = []
                    
                    for r in resultados_fase:
                        bloqueia, ns1, ns2, nt1, nt2, msg = conferir_e_ajustar_valores(r["s1"], r["s2"], r["t1"], r["t2"], r["j1"], r["j2"], r["mesa"])
                        if bloqueia:
                            st.error(msg)
                            sucesso_validacao = False
                        else:
                            dados_ajustados.append({"j1": r["j1"], "j2": r["j2"], "s1": ns1, "s2": ns2, "t1": nt1, "t2": nt2, "f1": r["f1"], "f2": r["f2"], "is_bronze": r["is_bronze"]})
                    
                    if sucesso_validacao:
                        vencedores, perdedores = [], []
                        for r in dados_ajustados:
                            j1, j2, s1, s2 = r["j1"], r["j2"], r["s1"], r["s2"]
                            s1_computado = 3 if (s1 == 2 and s2 == 0) else s1
                            s2_computado = 3 if (s2 == 2 and s1 == 0) else s2
                            
                            st.session_state.classificacao.loc[j1, ['Sets_Ganhos', 'Tentos_Pro', 'Tentos_Contra', 'Flores']] += [s1_computado, r["t1"], r["t2"], r["f1"]]
                            st.session_state.classificacao.loc[j2, ['Sets_Ganhos', 'Tentos_Pro', 'Tentos_Contra', 'Flores']] += [s2_computado, r["t2"], r["t1"], r["f2"]]
                            
                            if r["is_bronze"]:
                                if s1 > s2: st.session_state.terceiro_lugar, st.session_state.quarto_lugar = j1, j2
                                else: st.session_state.terceiro_lugar, st.session_state.quarto_lugar = j2, j1
                            else:
                                if s1 > s2: vencedores.append(j1); perdedores.append(j2)
                                else: vencedores.append(j2); perdedores.append(j1)
                                    
                        if st.session_state.fase_matamata == "OITAVAS DE FINAL": iniciar_fase_matamata(vencedores, "QUARTAS DE FINAL")
                        elif st.session_state.fase_matamata == "QUARTAS DE FINAL": iniciar_fase_matamata(vencedores, "SEMIFINAL")
                        elif st.session_state.fase_matamata == "SEMIFINAL":
                            st.session_state.fase_matamata = "FINAIS"
                            st.session_state.confrontos_mm = [
                                {"tipo": "normal", "j1": vencedores[0], "j2": vencedores[1]},
                                {"tipo": "bronze", "j1": perdedores[0], "j2": perdedores[1]}
                            ]
                        elif st.session_state.fase_matamata == "FINAIS":
                            st.session_state.campeao = vencedores[0]
                            st.session_state.vice_campeao = perdedores[0]
                        salvar_estado_no_disco()
                        st.rerun()
        else:
            for idx, c in enumerate(st.session_state.confrontos_mm):
                lbl = "🏆 Grande Final" if c["tipo"] == "normal" and st.session_state.fase_matamata == "FINAIS" else ("Disputa de 3º Lugar" if c["tipo"] == "bronze" else f"Mesa {idx+1}")
                patro_url = PATROCINADORES["mesas"][idx % len(PATROCINADORES["mesas"])]["logo"]
                st.markdown(f'<div class="card-mesa"><span class="texto-mesa-box">{lbl}: {c["j1"]} ⚔️ {c["j2"]}</span><img src="{patro_url}" class="tag-patrocinio-img"></div>', unsafe_allow_html=True)

    else:
        tab_mesas, tab_tabela, tab_hist = st.tabs(["⚔️ Mesas da Rodada", "📊 Tabela Geral", "📜 Histórico de Jogos"])
        
        with tab_mesas:
            if st.session_state.rodada_atual <= 5:
                st.markdown(f"#### 📅 Rodada {st.session_state.rodada_atual} de 5")
                
                if st.session_state.cronometro_ativo and st.session_state.hora_inicio_rodada:
                    tempo_limite = st.session_state.hora_inicio_rodada + timedelta(minutes=45)
                    tempo_atual = datetime.now()
                    if tempo_atual < tempo_limite:
                        tempo_restante = tempo_limite - tempo_atual
                        minutos, segundos = int(tempo_restante.total_seconds() // 60), int(tempo_restante.total_seconds() % 60)
                        st.markdown(f'<div class="cronometro-box"><h3 style="margin:0; color:#d4af37 !important;">⏱️ TEMPO RESTANTE: {minutos:02d}:{segundos:02d}</h3></div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="cronometro-box"><h3 style="margin:0; color:#ff4b4b !important;">⏰ TEMPO ESGOTADO!</h3></div>', unsafe_allow_html=True)
                
                if is_admin:
                    with st.form(key=f"form_rodada_exec_{st.session_state.rodada_atual}"):
                        placares = []
                        for idx, (j1, j2) in enumerate(st.session_state.confrontos):
                            patro_url = PATROCINADORES["mesas"][idx % len(PATROCINADORES["mesas"])]["logo"]
                            st.markdown(f'<div class="card-mesa"><span class="texto-mesa-box">Mesa {idx+1}</span><img src="{patro_url}" class="tag-patrocinio-img"></div>', unsafe_allow_html=True)
                            if j2 == "CHAPÉU (Folga)":
                                st.markdown(f"🤠 **{j1}** está no CHAPÉU")
                                placares.append(None)
                            else:
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.markdown(f"**{j1}**")
                                    s1 = st.number_input("Sets:", 0, 2, 0, key=f"s1_{idx}")
                                    t1 = st.number_input("Tentos:", 0, 72, 0, key=f"t1_{idx}")
                                    f1 = st.number_input("Flores:", 0, 20, 0, key=f"f1_{idx}")
                                with c2:
                                    st.markdown(f"**{j2}**")
                                    s2 = st.number_input("Sets:", 0, 2, 0, key=f"s2_{idx}")
                                    t2 = st.number_input("Tentos:", 0, 72, 0, key=f"t2_{idx}")
                                    f2 = st.number_input("Flores:", 0, 20, 0, key=f"f2_{idx}")
                                placares.append((s1, s2, t1, t2, f1, f2))
                        
                        if st.form_submit_button("💾 COMPUTAR RODADA"):
                            sucesso_validacao = True
                            dados_ajustados = []
                            
                            for idx, c in enumerate(placares):
                                j1, j2 = st.session_state.confrontos[idx]
                                if j2 != "CHAPÉU (Folga)":
                                    s1, s2, t1, t2, f1, f2 = c
                                    bloqueia, ns1, ns2, nt1, nt2, msg = conferir_e_ajustar_valores(s1, s2, t1, t2, j1, j2, idx+1)
                                    if bloqueia:
                                        st.error(msg)
                                        sucesso_validacao = False
                                    else: dados_ajustados.append((ns1, ns2, nt1, nt2, f1, f2))
                                else: dados_ajustados.append(None)
                                        
                            if sucesso_validacao:
                                dados_hist = []
                                for idx, c in enumerate(dados_ajustados):
                                    j1, j2 = st.session_state.confrontos[idx]
                                    if j2 == "CHAPÉU (Folga)":
                                        st.session_state.classificacao.loc[j1, ['Vitorias', 'Sets_Ganhos', 'Tentos_Pro']] += [1, 3, 72]
                                        dados_hist.append({"Mesa": idx+1, "Jogador 1": j1, "Placar": "CHAPÉU", "Jogador 2": "Folga"})
                                    else:
                                        s1, s2, t1, t2, f1, f2 = c
                                        s1_computado = 3 if (s1 == 2 and s2 == 0) else s1
                                        s2_computado = 3 if (s2 == 2 and s1 == 0) else s2
                                        
                                        st.session_state.classificacao.loc[j1, ['Vitorias', 'Sets_Ganhos', 'Tentos_Pro', 'Tentos_Contra', 'Flores']] += [(1 if s1 > s2 else 0), s1_computado, t1, t2, f1]
                                        st.session_state.classificacao.loc[j2, ['Vitorias', 'Sets_Ganhos', 'Tentos_Pro', 'Tentos_Contra', 'Flores']] += [(1 if s2 > s1 else 0), s2_computado, t2, t1, f2]
                                        dados_hist.append({"Mesa": idx+1, "Jogador 1": j1, "Placar": f"({s1}s | {t1}t) ✖ ({s2}s | {t2}t)", "Jogador 2": j2})
                                
                                st.session_state.historico_rodadas[f"Rodada {st.session_state.rodada_atual}"] = dados_hist
                                st.session_state.classificacao['Saldo_Tentos'] = st.session_state.classificacao['Tentos_Pro'] - st.session_state.classificacao['Tentos_Contra']
                                st.session_state.rodada_atual += 1
                                if st.session_state.rodada_atual <= 5: gerar_rodada_web()
                                salvar_estado_no_disco()
                                st.rerun()
                else:
                    for idx, (j1, j2) in enumerate(st.session_state.confrontos):
                        patro_url = PATROCINADORES["mesas"][idx % len(PATROCINADORES["mesas"])]["logo"]
                        st.markdown(f'<div class="card-mesa"><span class="texto-mesa-box">Mesa {idx+1}: {j1} ⚔️ {j2}</span><img src="{patro_url}" class="tag-patrocinio-img"></div>', unsafe_allow_html=True)
            else:
                st.success("🎉 Classificatória Encerrada!")
                if is_admin:
                    n_insc = len(st.session_state.jogadores)
                    f_nome = "OITAVAS DE FINAL" if n_insc > 16 else ("QUARTAS DE FINAL" if n_insc >= 8 else "SEMIFINAL")
                    qtd_c = 16 if n_insc > 16 else (8 if n_insc >= 8 else 4)
                    if st.button(f"🏆 GERAR CHAVE DE {f_nome}"):
                        df_v = st.session_state.classificacao.sort_values(by=['Vitorias', 'Sets_Ganhos', 'Saldo_Tentos'], ascending=False)
                        iniciar_fase_matamata(list(df_v.index[:qtd_c]), f_nome)
                        st.rerun()

        with tab_tabela:
            st.markdown("#### 📊 Tabela de Classificação")
            df_exibir = st.session_state.classificacao.sort_values(by=['Vitorias', 'Sets_Ganhos', 'Saldo_Tentos'], ascending=False)
            st.dataframe(df_exibir[['Vitorias', 'Sets_Ganhos', 'Saldo_Tentos', 'Flores']], use_container_width=True)

        with tab_hist:
            st.markdown("#### 🔍 Histórico de Partidas")
            for r_nome in sorted(st.session_state.historico_rodadas.keys(), reverse=True):
                with st.expander(r_nome):
                    for jogo in st.session_state.historico_rodadas[r_nome]:
                        st.write(f"Mesa {jogo['Mesa']}: {jogo['Jogador 1']} {jogo['Placar']} {jogo['Jogador 2']}")

        if is_admin:
            st.markdown("---")
            if st.button("🚨 Reiniciar Todo o Torneio"):
                if os.path.exists(ARQUIVO_BACKUP): os.remove(ARQUIVO_BACKUP)
                st.session_state.clear()
                st.rerun()

# 🌟 PAINEL DE RODAPÉ ATUALIZADO (BACKDROP DE MARCAS COM LINKS EM ALTA DISPONIBILIDADE)
st.markdown(f"""
    <div class="creditos">
        <hr style="border-color: #2c6b56; margin-bottom: 20px;">
        <p style='margin:0 0 15px 0; font-weight: bold;'>🌟 PARCEIROS OFICIAIS DO ESPORTE E DA TRADIÇÃO 🌟</p>
        <div style="display: flex; justify-content: center; align-items: center; gap: 20px; flex-wrap: wrap; background-color: #11221a; padding: 25px; border-radius: 12px; border: 1px solid #2c6b56;">
            <div style="background: white; padding: 6px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><img src="{PATROCINADORES['master']['logo']}" style="height: 25px; width: auto; object-fit: contain;"></div>
            <div style="background: white; padding: 6px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><img src="{PATROCINADORES['mesas'][1]['logo']}" style="height: 25px; width: auto; object-fit: contain;"></div>
            <div style="background: white; padding: 6px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><img src="{PATROCINADORES['mesas'][2]['logo']}" style="height: 25px; width: auto; object-fit: contain;"></div>
            <div style="background: white; padding: 6px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><img src="{PATROCINADORES['mesas'][3]['logo']}" style="height: 25px; width: auto; object-fit: contain;"></div>
            <div style="background: white; padding: 6px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: center;"><img src="{PATROCINADORES['mesas'][4]['logo']}" style="height: 25px; width: auto; object-fit: contain;"></div>
        </div>
        <p style="margin-top: 25px; font-size: 0.75rem;">💻 Criado por <b>{NOME_CRIADOR}</b> | Todos os direitos reservados © 2026</p>
    </div>
""", unsafe_allow_html=True)
