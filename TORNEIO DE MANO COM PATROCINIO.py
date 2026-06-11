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
    layout="wide" if st.session_state.get("modo_telao", False) else "centered"
)

NOME_CRIADOR = "Eduardo Luis Ferreira"
ARQUIVO_BACKUP = "torneio_atual.json"
ARQUIVO_GALERIA = "galeria_campeoes.json"

CHAVE_ADMINISTRADOR = "truco123"

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
        "salvo_na_galeria": st.session_state.get("salvo_na_galeria", False),
        "historico_confrontos_diretos": st.session_state.historico_confrontos_diretos,
        "resultados_salvos_rodada": st.session_state.get("resultados_salvos_rodada", {})
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
            st.session_state.historico_confrontos_diretos = estado.get("historico_confrontos_diretos", [])
            st.session_state.resultados_salvos_rodada = estado.get("resultados_salvos_rodada", {})
            
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
    "salvo_na_galeria": False,
    "historico_confrontos_diretos": [],
    "resultados_salvos_rodada": {},
    "modo_telao": False,
    "admin_logado": False
}

for chave, valor in valores_padrao.items():
    if chave not in st.session_state:
        st.session_state[chave] = valor

if os.path.exists(ARQUIVO_BACKUP):
    carregar_estado_do_disco()

# --- REFRESH AUTOMÁTICO DO CRONÔMETRO ---
if st.session_state.cronometro_ativo and st.session_state.hora_inicio_rodada:
    st.fragment(run_every=1.0)(lambda: None)()

# --- CÁLCULO DO TEMPO ADIANTADO PARA ESTILIZAÇÃO ---
avisar_fim_tempo = False
minutos, segundos = 45, 0
if st.session_state.cronometro_ativo and st.session_state.hora_inicio_rodada:
    tempo_limite = st.session_state.hora_inicio_rodada + timedelta(minutes=45)
    tempo_atual = datetime.now()
    if tempo_atual < tempo_limite:
        tempo_restante = tempo_limite - tempo_atual
        minutos = int(tempo_restante.total_seconds() // 60)
        segundos = int(tempo_restante.total_seconds() % 60)
        if minutos < 5:
            avisar_fim_tempo = True
    else:
        minutos, segundos = 0, 0

# --- INJEÇÃO DE CSS AVANÇADO (RENDERIZAÇÃO) ---
classe_cronometro = "cronometro-urgente" if avisar_fim_tempo else "cronometro-normal"
tamanho_fonte_mesa = "2rem" if st.session_state.modo_telao else "1.3rem"

st.markdown(f"""
    <style>
    @keyframes pulsarVermelho {{
        0% {{ border-color: #d4af37; box-shadow: 0 0 5px #d4af37; }}
        50% {{ border-color: #ff4b4b; box-shadow: 0 0 20px #ff4b4b; }}
        100% {{ border-color: #d4af37; box-shadow: 0 0 5px #d4af37; }}
    }}
    .stApp {{ background-color: #123329; }}
    h1, h2, h3, h4, p, label, .stMarkdown {{ color: #ffffff !important; }}
    
    /* Enquadramento de Cards Dinâmicos */
    .card-mesa-pendente {{ background: linear-gradient(135deg, #1b4d3e, #225c4b); padding: 20px; border-radius: 12px; margin-bottom: 15px; border: 2px solid #d4af37; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }}
    .card-mesa-concluida {{ background: linear-gradient(135deg, #14382d, #194235); padding: 20px; border-radius: 12px; margin-bottom: 15px; border: 2px solid #2ecc71; opacity: 0.85; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
    .card-mesa-chapeu {{ background: linear-gradient(135deg, #4a3b18, #5c491e); padding: 20px; border-radius: 12px; margin-bottom: 15px; border: 2px dashed #d4af37; text-align: center; }}
    
    .texto-mesa {{ font-size: {tamanho_fonte_mesa}; font-weight: bold; color: #ffffff; text-align: center; margin-bottom: 10px; }}
    .badge-concluido {{ background-color: #2ecc71; color: #ffffff; padding: 3px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; float: right; }}
    
    /* Cronômetros Estilizados */
    .cronometro-normal {{ background-color: #0d1f1a; border: 3px solid #d4af37; padding: 20px; border-radius: 12px; text-align: center; font-family: 'Courier New', Courier, monospace; margin-bottom: 25px; box-shadow: inset 0 0 15px rgba(212,175,55,0.2); }}
    .cronometro-urgente {{ background-color: #2b0d0d; border: 3px solid #ff4b4b; padding: 20px; border-radius: 12px; text-align: center; font-family: 'Courier New', Courier, monospace; margin-bottom: 25px; animation: pulsarVermelho 2s infinite; }}
    
    /* Pódio e Campeões */
    .box-campeao {{ background: linear-gradient(135deg, #d4af37, #f1c40f); padding: 35px; border-radius: 15px; text-align: center; color: #111111 !important; border: 4px solid #ffffff; box-shadow: 0 10px 25px rgba(0,0,0,0.5); margin-bottom: 25px; }}
    .box-campeao h1, .box-campeao h2 {{ color: #111111 !important; font-weight: 900; }}
    .podio-posicao {{ padding: 18px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 12px; font-size: 1.1rem; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }}
    .podio-vice {{ background-color: #bdc3c7; border: 2px solid #ecf0f1; color: #2c3e50 !important; }}
    .podio-terceiro {{ background-color: #d35400; border: 2px solid #e67e22; color: #ffffff !important; }}
    .podio-quarto {{ background-color: #34495e; border: 2px solid #7f8c8d; color: #ffffff !important; }}
    
    .box-flores {{ background: linear-gradient(135deg, #5c1d30, #7d2641); padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #ff4b4b; margin-bottom: 25px; font-weight: bold; }}
    .creditos {{ text-align: center; color: #8ba89f !important; font-size: 0.85rem; margin-top: 60px; padding: 20px 0; }}
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

# --- CONTROLE DE ACESSO E SIDEBAR (CORRIGIDO) ---
st.sidebar.markdown("### 🔐 Controle de Acesso")

if not st.session_state.admin_logado:
    senha_inserida = st.sidebar.text_input("Chave do Operador:", type="password", key="campo_senha")
    if st.sidebar.button("🔑 Entrar"):
        if senha_inserida == CHAVE_ADMINISTRADOR:
            st.session_state.admin_logado = True
            st.rerun()
        else:
            st.sidebar.error("❌ Senha Incorreta!")
else:
    if st.sidebar.button("🚪 Sair do Modo Adm"):
        st.session_state.admin_logado = False
        st.rerun()

is_admin = st.session_state.admin_logado

# --- CONFIGURAÇÕES DE TELA ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 📺 Configurações de Tela")
st.session_state.modo_telao = st.sidebar.checkbox("Ativar Modo Telão (TV/Projetor)", value=st.session_state.modo_telao)

if is_admin:
    st.sidebar.success("⚡ Modo Administrator Ativo")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🌐 Link de Acesso Público")
    url_torneio = st.sidebar.text_input("Link Atual:", value=st.session_state.get("url_override", url_oficial))
    st.session_state["url_override"] = url_torneio
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

# --- TRAVA MATEMÁTICA DO TRUCO ---
def conferir_e_ajustar_valores(s1, s2, t1, t2, n1, n2, mesa_id):
    if (s1 == 2 and s2 == 2) or (s1 < 2 and s2 < 2):
        return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Placar de Sets inválido ({s1}x{s2}). Alguém precisa fechar com exatamente 2 sets."
    if s1 == 2 and s2 == 0:
        t1 = 72 
        if t2 > 46: return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Inconsistência! No 2x0, o perdedor ({n2}) não pode somar mais do que 46 tentos."
    elif s2 == 2 and s1 == 0:
        t2 = 72 
        if t1 > 46: return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Inconsistência! No 2x0, o perdedor ({n1}) não pode somar mais do que 46 tentos."
    elif s1 == 2 and s2 == 1:
        if t1 < 48: return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Inconsistência! Como {n1} fez 2 sets, ele precisa ter no mínimo 48 tentos."
        if t2 < 24: return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Inconsistência! Como {n2} fez 1 set, ele precisa ter no mínimo 24 tentos."
    elif s2 == 2 and s1 == 1:
        if t2 < 48: return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Inconsistência! Como {n2} fez 2 sets, ele precisa ter no mínimo 48 tentos."
        if t1 < 24: return True, s1, s2, t1, t2, f"Mesa {mesa_id}: Inconsistência! Como {n1} fez 1 set, ele precisa ter no mínimo 24 tentos."
    return False, s1, s2, t1, t2, ""

# --- ALGORITMO SUÍÇO ADAPTADO ---
def gerar_rodada_web():
    if st.session_state.rodada_atual == 1:
        lista_rodada = list(st.session_state.jogadores)
        random.shuffle(lista_rodada)
    else:
        df_ord = st.session_state.classificacao.sort_values(
            by=['Vitorias', 'Sets_Ganhos', 'Saldo_Tentos', 'Flores'], 
            ascending=[False, False, False, False]
        )
        lista_rodada = list(df_ord.index)

    st.session_state.confrontos = []
    st.session_state.resultados_salvos_rodada = {}
    
    if len(lista_rodada) % 2 != 0:
        cand_chapeu = [j for j in lista_rodada if j not in st.session_state.jogadores_no_chapeu]
        chapeu = random.choice(cand_chapeu if cand_chapeu else lista_rodada)
        lista_rodada.remove(chapeu)
        st.session_state.jogadores_no_chapeu.add(chapeu)
        st.session_state.confrontos.append((chapeu, "CHAPÉU (Folga)"))

    if st.session_state.rodada_atual > 1:
        pareados = []
        while len(lista_rodada) > 1:
            j1 = lista_rodada.pop(0)
            encontrou_par = False
            for idx, j2 in enumerate(lista_rodada):
                par_ordenado = tuple(sorted([j1, j2]))
                if par_ordenado not in st.session_state.historico_confrontos_diretos:
                    lista_rodada.pop(idx)
                    st.session_state.confrontos.append((j1, j2))
                    pareados.append(par_ordenado)
                    encontrou_par = True
                    break
            if not encontrou_par:
                j2 = lista_rodada.pop(0)
                st.session_state.confrontos.append((j1, j2))
                pareados.append(tuple(sorted([j1, j2])))
    else:
        for i in range(0, len(lista_rodada), 2):
            st.session_state.confrontos.append((lista_rodada[i], lista_rodada[i+1]))
            
    st.session_state.hora_inicio_rodada = None
    st.session_state.cronometro_ativo = False
    salvar_estado_no_disco()

def iniciar_fase_matamata(lista_jogadores, nome_fase):
    st.session_state.em_matamata = True
    st.session_state.fase_matamata = nome_fase
    st.session_state.confrontos_mm = []
    st.session_state.resultados_salvos_rodada = {}
    n = len(lista_jogadores)
    for i in range(n // 2):
        st.session_state.confrontos_mm.append({
            "tipo": "normal", 
            "j1": lista_jogadores[i], 
            "j2": lista_jogadores[n - 1 - i]
        })
    st.session_state.hora_inicio_rodada = None
    st.session_state.cronometro_ativo = False
    salvar_estado_no_disco()

# --- COBERTURA DO TÍTULO PRINCIPAL ---
if st.session_state.modo_telao:
    st.markdown(f"<h1 style='text-align: center; font-size: 3.5rem; margin-bottom: 0;'>🏆 {st.session_state.get('nome_torneio', 'Torneio de Truco')} 🏆</h1>", unsafe_allow_html=True)
else:
    st.title("🏆 Torneio de Truco de Mano")

# === TELA 1: INSCRIÇÕES E CONFIGURAÇÃO ===
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
                        st.rerun()
        
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
                st.session_state.historico_confrontos_diretos = []
                st.session_state.resultados_salvos_rodada = {}
                st.session_state.campeao = None
                gerar_rodada_web()
                st.rerun()
                
    with aba2:
        st.markdown("### 🏛️ Registro de Campeões")
        if os.path.exists(ARQUIVO_GALERIA):
            with open(ARQUIVO_GALERIA, "r", encoding="utf-8") as f:
                dados_galeria = json.load(f)
            if dados_galeria:
                df_galeria = pd.DataFrame(dados_galeria)
                df_galeria.columns = ["📅 Data/Hora", "🏟️ Torneio", "🥇 Campeão", "🥈 Vice", "🥉 3º Lugar", "🎖️ 4º Lugar", "🌸 Rei das Flores"]
                st.dataframe(df_galeria, use_container_width=True, hide_index=True)

# === TELA 2: ANDAMENTO DO TORNEIO ===
else:
    if not st.session_state.modo_telao:
        st.markdown(f"#### 🏟️ {st.session_state.nome_torneio}")
    
    # --- TORNEIO CONCLUÍDO (TELA DE PREMIAÇÃO) ---
    if st.session_state.campeao:
        st.balloons()
        st.markdown("<h2 style='text-align: center; color: #d4af37 !important; font-size: 2.5rem;'>✨ CERIMÔNIA DE PREMIAÇÃO FINAL ✨</h2>", unsafe_allow_html=True)
        rei_das_flores = st.session_state.classificacao.sort_values(by='Flores', ascending=False).index[0]
        max_flores = int(st.session_state.classificacao.loc[rei_das_flores, 'Flores'])
            
        if not st.session_state.get("salvo_na_galeria", False):
            salvar_na_galeria(st.session_state.nome_torneio, st.session_state.campeao, st.session_state.vice_campeao, st.session_state.terceiro_lugar, st.session_state.quarto_lugar, rei_das_flores, max_flores)
            st.session_state.salvo_na_galeria = True
            salvar_estado_no_disco()
        
        st.markdown(f'<div class="box-campeao"><h1>🥇 1º LUGAR - CAMPEÃO 🥇</h1><h2>🌟 {st.session_state.campeao} 🌟</h2></div>', unsafe_allow_html=True)
        
        col_podio = st.columns(3)
        with col_podio[0]:
            st.markdown(f'<div class="podio-posicao podio-vice">🥈 2º LUGAR<br>{st.session_state.vice_campeao}</div>', unsafe_allow_html=True)
        with col_podio[1]:
            st.markdown(f'<div class="podio-posicao podio-terceiro">🥉 3º LUGAR<br>{st.session_state.terceiro_lugar}</div>', unsafe_allow_html=True)
        with col_podio[2]:
            st.markdown(f'<div class="podio-posicao podio-quarto">🎖️ 4º LUGAR<br>{st.session_state.quarto_lugar}</div>', unsafe_allow_html=True)
            
        st.markdown(f'<div class="box-flores">🌸 REI DAS FLORES: {rei_das_flores} ({max_flores} flores computadas)</div>', unsafe_allow_html=True)
        
        if is_admin and st.button("🏁 Limpar e Preparar Novo Torneio"):
            if os.path.exists(ARQUIVO_BACKUP): os.remove(ARQUIVO_BACKUP)
            jsalvos = list(st.session_state.jogadores)
            st.session_state.clear()
            st.session_state.jogadores = jsalvos
            st.rerun()

    # --- FASE DE MATA-MATA ---
    elif st.session_state.em_matamata:
        st.markdown(f"<h3 style='text-align: center; color: #d4af37 !important;'>⚡ FASE ATUAL: {st.session_state.fase_matamata} ⚡</h3>", unsafe_allow_html=True)
        
        if st.session_state.cronometro_ativo and st.session_state.hora_inicio_rodada:
            if minutos == 0 and segundos == 0:
                st.markdown(f'<div class="{classe_cronometro}"><h1 style="margin:0; font-size: 3.5rem; color:#ff4b4b !important;">⏰ TEMPO ESGOTADO!</h1></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="{classe_cronometro}"><h1 style="margin:0; font-size: 3.5rem; color:#d4af37 !important;">⏱️ {minutos:02d}:{segundos:02d}</h1><p style="margin:0; font-weight:bold;">TEMPO RESTANTE DA RODADA</p></div>', unsafe_allow_html=True)
            
            if is_admin:
                c_c1, c_c2 = st.columns(2)
                with c_c1:
                    if st.button("⏹️ Pausar/Resetar Cronômetro"):
                        st.session_state.hora_inicio_rodada = None
                        st.session_state.cronometro_ativo = False
                        salvar_estado_no_disco()
                        st.rerun()
                with c_c2:
                    if st.button("🔓 Adicionar +5 Minutos"):
                        st.session_state.hora_inicio_rodada += timedelta(minutes=5)
                        salvar_estado_no_disco()
                        st.rerun()
        else:
            st.markdown('<div class="cronometro-normal"><h3 style="margin:0; color:#a0a0a0 !important;">⏱️ CRONÔMETRO PAUSADO OU AGUARDANDO INÍCIO</h3></div>', unsafe_allow_html=True)
            if is_admin and st.button("▶️ INICIAR CONTAGEM REGRESSIVA (45 MIN)"):
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
                    
                    st.markdown(f'<div class="card-mesa-pendente"><div class="texto-mesa">{texto_mesa}</div></div>', unsafe_allow_html=True)
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
                
                if st.form_submit_button("💾 SALVAR E COMPUTAR RESULTADOS DOS JOGOS"):
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
            cols_mesas = st.columns(2)
            for idx, c in enumerate(st.session_state.confrontos_mm):
                lbl = "🏆 Grande Final" if c["tipo"] == "normal" and st.session_state.fase_matamata == "FINAIS" else ("Disputa de 3º Lugar" if c["tipo"] == "bronze" else f"Mesa {idx+1}")
                with cols_mesas[idx % 2]:
                    st.markdown(f"""
                        <div class="card-mesa-pendente">
                            <div class="texto-mesa">{lbl}</div>
                            <h3 style="text-align:center; margin:5px 0;">{c['j1']} <span style="color:#d4af37;">⚔️</span> {c['j2']}</h3>
                        </div>
                    """, unsafe_allow_html=True)

# --- FASE CLASSIFICATÓRIA ---
    else:
        tab_mesas, tab_tabela, tab_hist = st.tabs(["⚔️ Mesas da Rodada", "📊 Tabela Geral", "📜 Histórico de Jogos"])
        
        with tab_mesas:
            if st.session_state.rodada_atual <= 5:
                st.markdown(f"<h3 style='text-align: center; color: #d4af37 !important;'>📅 ANDAMENTO: RODADA {st.session_state.rodada_atual} DE 5</h3>", unsafe_allow_html=True)
                
                if st.session_state.cronometro_ativo and st.session_state.hora_inicio_rodada:
                    if minutos == 0 and segundos == 0:
                        st.markdown(f'<div class="{classe_cronometro}"><h1 style="margin:0; font-size: 3.5rem; color:#ff4b4b !important;">⏰ TEMPO ESGOTADO!</h1></div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="{classe_cronometro}"><h1 style="margin:0; font-size: 3.5rem; color:#d4af37 !important;">⏱️ {minutos:02d}:{segundos:02d}</h1><p style="margin:0; font-weight:bold;">TEMPO RESTANTE DA RODADA</p></div>', unsafe_allow_html=True)
                    
                    if is_admin:
                        c_c1, c_c2 = st.columns(2)
                        with c_c1:
                            if st.button("⏹️ Pausar/Resetar Cronômetro", key="rc_class"):
                                st.session_state.hora_inicio_rodada = None
                                st.session_state.cronometro_ativo = False
                                salvar_estado_no_disco()
                                st.rerun()
                        with c_c2:
                            if st.button("🔓 Adicionar +5 Minutos", key="m5_class"):
                                st.session_state.hora_inicio_rodada += timedelta(minutes=5)
                                salvar_estado_no_disco()
                                st.rerun()
                else:
                    st.markdown('<div class="cronometro-normal"><h3 style="margin:0; color:#a0a0a0 !important;">⏱️ CRONÔMETRO PAUSADO OU AGUARDANDO INÍCIO</h3></div>', unsafe_allow_html=True)
                    if is_admin and st.button("▶️ INICIAR CONTAGEM REGRESSIVA (45 MIN)", key="start_class"):
                        st.session_state.hora_inicio_rodada = datetime.now()
                        st.session_state.cronometro_ativo = True
                        salvar_estado_no_disco()
                        st.rerun()
                
                if is_admin:
                    with st.form(key=f"form_rodada_exec_{st.session_state.rodada_atual}"):
                        placares = []
                        for idx, (j1, j2) in enumerate(st.session_state.confrontos):
                            if j2 == "CHAPÉU (Folga)":
                                st.markdown(f'<div class="card-mesa-chapeu">🤠 <b>{j1}</b> foi sorteado e está no <b>CHAPÉU (Folga Garantida)</b></div>', unsafe_allow_html=True)
                                placares.append(None)
                            else:
                                status_estilo = "card-mesa-concluida" if f"mesa_{idx}" in st.session_state.resultados_salvos_rodada else "card-mesa-pendente"
                                badge_texto = '<span class="badge-concluido">SALVO</span>' if status_estilo == "card-mesa-concluida" else ""
                                
                                st.markdown(f'<div class="{status_estilo}"><div class="texto-mesa">Mesa {idx+1} {badge_texto}</div></div>', unsafe_allow_html=True)
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
                                
                                if s1 > 0 or s2 > 0 or t1 > 0 or t2 > 0:
                                    st.session_state.resultados_salvos_rodada[f"mesa_{idx}"] = True
                        
                        if st.form_submit_button("💾 COMPUTAR E ENCERRAR RODADA ATUAL"):
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
                                        
                                        st.session_state.historico_confrontos_diretos.append(tuple(sorted([j1, j2])))
                                
                                st.session_state.historico_rodadas[f"Rodada {st.session_state.rodada_atual}"] = dados_hist
                                st.session_state.classificacao['Saldo_Tentos'] = st.session_state.classificacao['Tentos_Pro'] - st.session_state.classificacao['Tentos_Contra']
                                st.session_state.rodada_atual += 1
                                if st.session_state.rodada_atual <= 5: gerar_rodada_web()
                                salvar_estado_no_disco()
                                st.rerun()
                else:
                    cols_grade = st.columns(3)
                    for idx, (j1, j2) in enumerate(st.session_state.confrontos):
                        with cols_grade[idx % 3]:
                            if j2 == "CHAPÉU (Folga)":
                                st.markdown(f'<div class="card-mesa-chapeu">🤠 <b>{j1}</b><br><span style="color:#d4af37; font-size:0.9rem;">CHAPÉU (FOLGA)</span></div>', unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                    <div class="card-mesa-pendente">
                                        <div class="texto-mesa">Mesa {idx+1}</div>
                                        <p style="text-align:center; margin:5px 0; font-size:1.1rem;"><b>{j1}</b><br><span style="color:#d4af37;">✖</span><br><b>{j2}</b></p>
                                    </div>
                                """, unsafe_allow_html=True)
            else:
                st.success("🎉 Fase de Classificatória Totalmente Encerrada!")
                if is_admin:
                    n_insc = len(st.session_state.jogadores)
                    f_nome = "OITAVAS DE FINAL" if n_insc > 16 else ("QUARTAS DE FINAL" if n_insc >= 8 else "SEMIFINAL")
                    qtd_c = 16 if n_insc > 16 else (8 if n_insc >= 8 else 4)
                    if st.button(f"🏆 GERAR CHAVE ELIMINATÓRIA DE {f_nome}"):
                        df_v = st.session_state.classificacao.sort_values(
                            by=['Vitorias', 'Sets_Ganhos', 'Saldo_Tentos', 'Flores'], 
                            ascending=[False, False, False, False]
                        )
                        iniciar_fase_matamata(list(df_v.index[:qtd_c]), f_nome)
                        st.rerun()

        with tab_tabela:
            df_exibir = st.session_state.classificacao.sort_values(
                by=['Vitorias', 'Sets_Ganhos', 'Saldo_Tentos', 'Flores'], 
                ascending=[False, False, False, False]
            )
            
            st.markdown("#### 📈 Estatísticas do Campeonato")
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric(label="Total de Jogadores", value=len(st.session_state.jogadores))
            with m2:
                st.metric(label="Líder Atual", value=df_exibir.index[0] if len(df_exibir) > 0 else "Nenhum")
            with m3:
                tentos_totais = int(df_exibir['Tentos_Pro'].sum())
                st.metric(label="Tentos Rodados", value=f"{tentos_totais} pts")
            
            st.markdown("---")
            st.markdown("#### 📊 Tabela Classificatória Geral")
            st.dataframe(df_exibir[['Vitorias', 'Sets_Ganhos', 'Saldo_Tentos', 'Flores']], use_container_width=True)

        with tab_hist:
            st.markdown("#### 🔍 Histórico Completo de Partidas")
            for r_nome in sorted(st.session_state.historico_rodadas.keys(), reverse=True):
                with st.expander(r_nome):
                    for jogo in st.session_state.historico_rodadas[r_nome]:
                        st.write(f"🔹 **Mesa {jogo['Mesa']}:** {jogo['Jogador 1']} {jogo['Placar']} {jogo['Jogador 2']}")

        if is_admin:
            st.markdown("---")
            if st.button("🚨 Reiniciar Todo o Torneio"):
                if os.path.exists(ARQUIVO_BACKUP): os.remove(ARQUIVO_BACKUP)
                st.session_state.clear()
                st.rerun()

st.markdown(f"""
    <div class="creditos">
        <hr style="border-color: #2c6b56;">
        💻 Desenvolvido por <b>{NOME_CRIADOR}</b> | Painel de Controle de Eventos © 2026
    </div>
""", unsafe_allow_html=True)
