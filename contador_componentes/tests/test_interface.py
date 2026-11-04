"""Testes de `interface.py` (Sprint 9, tarefa 9.1).

As funções puras são testadas sem janela. Os testes de widget criam um
`tk.Tk()` real (sem `mainloop`; eventos processados com `update`) e são
pulados se não houver display disponível (ex.: CI sem X11).

Não usam webcam nem modelo: os frames são sintéticos.

Uso (a partir da raiz do repositório, com o venv do projeto ativo):
    python -m pytest contador_componentes/tests
"""

from __future__ import annotations

import subprocess
import sys
import tkinter as tk

import numpy as np
import pytest

from contador_componentes.app import config as app_config
from contador_componentes.app import interface
from contador_componentes.app.counter import Estado

ROTULOS_ESPERADOS = {
    Estado.AGUARDANDO_CONFIGURACAO: "AGUARDANDO CONFIGURAÇÃO",
    Estado.CONTANDO: "CONTANDO",
    Estado.QUANTIDADE_ATINGIDA: "QUANTIDADE ATINGIDA",
    Estado.QUANTIDADE_EXCEDIDA: "QUANTIDADE EXCEDIDA",
    Estado.ERRO_CAMERA: "ERRO DE CÂMERA",
    Estado.MODELO_NAO_CARREGADO: "MODELO NÃO CARREGADO",
}


def _frame(largura: int = 320, altura: int = 180) -> np.ndarray:
    frame = np.zeros((altura, largura, 3), dtype=np.uint8)
    frame[..., 0] = 255  # azul em BGR
    return frame


# ---------------------------------------------------------------------------
# Funções puras
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("texto", ["", "1", "9", "12", "1000000"])
def test_texto_quantidade_aceito(texto):
    assert interface.texto_quantidade_aceitavel(texto)


@pytest.mark.parametrize("texto", ["0", "00", "012", "-1", "+3", "1.5", "1,5", " 1", "a", "1e3", "١"])
def test_texto_quantidade_recusado(texto):
    assert not interface.texto_quantidade_aceitavel(texto)


def test_texto_quantidade_respeita_maximo():
    assert interface.texto_quantidade_aceitavel("10", maximo=10)
    assert not interface.texto_quantidade_aceitavel("11", maximo=10)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("", None), ("  ", None), ("0", None), ("abc", None), ("7", 7), (" 42 ", 42)],
)
def test_interpretar_quantidade(texto, esperado):
    assert interface.interpretar_quantidade(texto) == esperado


def test_interpretar_quantidade_acima_do_maximo_e_none():
    assert interface.interpretar_quantidade("11", maximo=10) is None
    assert interface.interpretar_quantidade("10", maximo=10) == 10


@pytest.mark.parametrize(
    ("origem", "area", "esperado"),
    [
        ((1920, 1080), (960, 1080), (960, 540)),   # limitado pela largura
        ((1920, 1080), (1920, 540), (960, 540)),   # limitado pela altura
        ((640, 480), (1280, 960), (1280, 960)),    # ampliação
        ((640, 480), (1, 1), (1, 1)),              # área ainda não dimensionada
        ((640, 480), (0, -5), (1, 1)),
    ],
)
def test_calcular_tamanho_letterbox(origem, area, esperado):
    assert interface.calcular_tamanho_letterbox(*origem, *area) == esperado


def test_letterbox_mantem_proporcao_e_cabe():
    for area in [(800, 600), (300, 900), (1234, 321)]:
        w, h = interface.calcular_tamanho_letterbox(1920, 1080, *area)
        assert w <= area[0] and h <= area[1]
        assert abs(w / h - 1920 / 1080) < 0.02
        assert w == area[0] or h == area[1]


def test_letterbox_origem_invalida():
    with pytest.raises(ValueError):
        interface.calcular_tamanho_letterbox(0, 10, 100, 100)


def test_redimensionar_letterbox():
    saida = interface.redimensionar_letterbox(_frame(1920, 1080), 400, 400)
    assert saida.shape == (225, 400, 3)
    frame = _frame(400, 225)
    assert interface.redimensionar_letterbox(frame, 400, 400) is frame


def test_frame_para_ppm_converte_bgr_para_rgb():
    dados = interface.frame_para_ppm(_frame(4, 3))
    cabecalho = b"P6 4 3 255\n"
    assert dados.startswith(cabecalho)
    pixels = dados[len(cabecalho):]
    assert len(pixels) == 4 * 3 * 3
    assert pixels[:3] == bytes([0, 0, 255])  # azul BGR -> (R=0, G=0, B=255)


def test_frame_para_ppm_aceita_cinza_e_bgra():
    cinza = np.full((2, 2), 7, dtype=np.uint8)
    assert interface.frame_para_ppm(cinza).endswith(bytes([7]) * 12)
    bgra = np.zeros((2, 2, 4), dtype=np.uint8)
    assert len(interface.frame_para_ppm(bgra)) == len(b"P6 2 2 255\n") + 12


@pytest.mark.parametrize(
    "frame",
    [np.zeros((2, 2, 3), dtype=np.float32), np.zeros((2, 2, 2), dtype=np.uint8), "x"],
)
def test_frame_para_ppm_invalido(frame):
    with pytest.raises(ValueError):
        interface.frame_para_ppm(frame)


def test_estilo_do_estado_cobre_todos_os_estados_com_rotulo_exato():
    for estado in Estado:
        texto, fundo, cor_texto = interface.estilo_do_estado(estado)
        assert texto == ROTULOS_ESPERADOS[estado]
        assert fundo.startswith("#") and cor_texto.startswith("#")


def test_estados_semanticos_tem_cores_distintas():
    fundos = {e: interface.estilo_do_estado(e)[1] for e in Estado}
    principais = [
        Estado.AGUARDANDO_CONFIGURACAO,
        Estado.CONTANDO,
        Estado.QUANTIDADE_ATINGIDA,
        Estado.QUANTIDADE_EXCEDIDA,
        Estado.ERRO_CAMERA,
    ]
    assert len({fundos[e] for e in principais}) == len(principais)


def test_formatar_quantidade():
    assert interface.formatar_quantidade(None) == interface.TEXTO_SEM_VALOR
    assert interface.formatar_quantidade(0) == "0"
    assert interface.formatar_quantidade(12) == "12"


@pytest.mark.parametrize(
    ("estado", "detectado", "esperado", "k", "n", "texto"),
    [
        (Estado.CONTANDO, 5, 5, 3, 5, "estabilizando 3/5"),
        (Estado.CONTANDO, 6, 5, 1, 5, "estabilizando 1/5"),
        (Estado.CONTANDO, 4, 5, 3, 5, ""),        # abaixo do alvo: nada a confirmar
        (Estado.CONTANDO, 5, 5, 0, 5, ""),
        (Estado.CONTANDO, 5, 5, 5, 5, ""),        # sequência completa
        (Estado.CONTANDO, 5, 5, 1, 1, ""),        # sem estabilização
        (Estado.CONTANDO, 5, 5, 3, 0, ""),        # n não informado
        (Estado.CONTANDO, None, 5, 3, 5, ""),
        (Estado.QUANTIDADE_ATINGIDA, 5, 5, 5, 5, ""),
        (Estado.ERRO_CAMERA, 5, 5, 3, 5, ""),
    ],
)
def test_texto_estabilizacao(estado, detectado, esperado, k, n, texto):
    assert interface.texto_estabilizacao(estado, detectado, esperado, k, n) == texto


def test_config_quantidade_maxima_padrao_sem_limite():
    # Ponto em aberto (PRD 29.6): não inventar limite.
    assert app_config.QUANTIDADE_MAXIMA is None


def test_habilitar_dpi_awareness_noop_fora_do_windows(monkeypatch):
    monkeypatch.setattr(interface.sys, "platform", "linux")
    assert interface.habilitar_dpi_awareness() is None


def test_habilitar_dpi_awareness_nao_levanta():
    # Em subprocesso: o DPI awareness altera o processo inteiro e afetaria as
    # janelas criadas pelos outros testes.
    codigo = (
        "from contador_componentes.app import interface; "
        "interface.habilitar_dpi_awareness(); "
        "interface.habilitar_dpi_awareness()"
    )
    resultado = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr


# ---------------------------------------------------------------------------
# Widgets (precisam de display)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _tk_raiz():
    """Um único `tk.Tk()` para o módulo inteiro.

    Criar e destruir vários `tk.Tk()` no mesmo processo é instável no Windows
    (falhas intermitentes "Can't find a usable init.tcl"); por isso cada teste
    usa um `Toplevel` novo sobre esta raiz, que tem a mesma API usada pela
    interface (protocol, geometry, minsize, after...).
    """
    try:
        raiz = tk.Tk()
    except tk.TclError as exc:  # sem display
        pytest.skip(f"Tk indisponivel: {exc}")
    raiz.withdraw()
    yield raiz
    try:
        raiz.destroy()
    except tk.TclError:
        pass


@pytest.fixture
def root(_tk_raiz):
    janela = tk.Toplevel(_tk_raiz)
    janela.withdraw()
    yield janela
    try:
        janela.destroy()
    except tk.TclError:
        pass


class _Registro:
    def __init__(self) -> None:
        self.configs: list[tuple[str | None, int | None]] = []
        self.resets = 0
        self.fechamentos = 0

    def on_config_change(self, classe, quantidade):
        self.configs.append((classe, quantidade))

    def on_reset(self):
        self.resets += 1

    def on_close(self):
        self.fechamentos += 1


def _criar(root, registro, com_close=True):
    ui = interface.InterfaceContador(
        root,
        on_config_change=registro.on_config_change,
        on_reset=registro.on_reset,
        on_close=registro.on_close if com_close else None,
    )
    root.update()
    return ui


def _fechar_pela_janela(root):
    root.tk.call(root.protocol("WM_DELETE_WINDOW"))


def test_estado_inicial(root):
    reg = _Registro()
    ui = _criar(root, reg)
    assert ui._lbl_status.cget("text") == "AGUARDANDO CONFIGURAÇÃO"
    assert ui._lbl_detectado.cget("text") == interface.TEXTO_SEM_VALOR
    assert ui._lbl_esperado.cget("text") == interface.TEXTO_SEM_VALOR
    assert ui.classe_selecionada is None
    assert ui.quantidade_desejada is None
    assert str(ui._lbl_video.cget("text")) == interface.TEXTO_SEM_IMAGEM
    assert reg.configs == [] and reg.resets == 0


def test_seletor_tem_somente_parafuso_e_porca(root):
    ui = _criar(root, _Registro())
    assert set(ui._radios) == {"parafuso", "porca"}
    assert [r.cget("text") for r in ui._radios.values()] == ["Parafuso", "Porca"]


def test_atualizar_painel_todos_os_estados(root):
    ui = _criar(root, _Registro())
    for estado in Estado:
        ui.atualizar_painel(3, 5, estado, frames_consecutivos=2, n_frames=5)
        root.update_idletasks()
        assert ui._lbl_status.cget("text") == ROTULOS_ESPERADOS[estado]
        assert ui._lbl_detectado.cget("text") == "3"
        assert ui._lbl_esperado.cget("text") == "5"
    ui.atualizar_painel(5, 5, Estado.CONTANDO, frames_consecutivos=3, n_frames=5)
    assert ui._lbl_progresso.cget("text") == "estabilizando 3/5"
    ui.atualizar_painel(5, 5, Estado.QUANTIDADE_ATINGIDA, 5, 5)
    assert ui._lbl_progresso.cget("text") == ""
    ui.atualizar_painel(None, None, Estado.ERRO_CAMERA)
    assert ui._lbl_detectado.cget("text") == interface.TEXTO_SEM_VALOR


def test_mostrar_frame_e_placeholder(root):
    ui = _criar(root, _Registro())
    root.deiconify()
    root.geometry("1000x600")
    root.update()
    largura_area, altura_area = ui._area_video
    assert largura_area > 1 and altura_area > 1

    ui.mostrar_frame(_frame(1920, 1080))
    root.update()
    assert ui._photo is not None
    w, h = ui._photo.width(), ui._photo.height()
    assert w <= largura_area and h <= altura_area
    assert abs(w / h - 1920 / 1080) < 0.02
    foto_anterior = ui._photo

    # Mesmo tamanho: reaproveita a mesma PhotoImage.
    ui.mostrar_frame(_frame(1920, 1080))
    assert ui._photo is foto_anterior

    # Frame sem câmera (None) -> placeholder.
    ui.mostrar_frame(None)
    assert ui._photo is None
    assert str(ui._lbl_video.cget("text")) == interface.TEXTO_SEM_IMAGEM

    # Outros formatos/tamanhos não quebram.
    ui.mostrar_frame(_frame(640, 480))
    ui.mostrar_frame(np.zeros((10, 10), dtype=np.uint8))
    root.update()


def test_redimensionar_janela_reajusta_video(root):
    ui = _criar(root, _Registro())
    root.deiconify()
    root.geometry("1000x600")
    root.update()
    ui.mostrar_frame(_frame(1920, 1080))
    root.update()
    largura_antes = ui._photo.width()
    root.geometry("1400x800")
    root.update()
    assert ui._photo.width() > largura_antes


def test_layout_estreito_move_painel_para_baixo(root):
    ui = _criar(root, _Registro())
    root.deiconify()
    largura_larga = ui._px(interface.LARGURA_LAYOUT_ESTREITO) + 200
    root.geometry(f"{largura_larga}x{root.minsize()[1]}")
    root.update()
    assert ui._painel.grid_info()["column"] == 1
    root.geometry(f"{root.minsize()[0]}x{root.minsize()[1]}")
    root.update()
    assert ui._painel.grid_info()["row"] == 1
    assert ui._painel.grid_info()["column"] == 0


def test_validacao_do_campo_quantidade(root):
    ui = _criar(root, _Registro())
    spin = ui._spin_quantidade
    for invalido in ["abc", "-3", "0", "1.5", " "]:
        spin.delete(0, "end")
        spin.insert(0, invalido)
        assert spin.get() == ""
    spin.insert(0, "12")
    assert spin.get() == "12"
    spin.insert("end", "x")
    assert spin.get() == "12"


def test_validacao_respeita_quantidade_maxima(root, monkeypatch):
    monkeypatch.setattr(app_config, "QUANTIDADE_MAXIMA", 10)
    ui = _criar(root, _Registro())
    ui._spin_quantidade.insert(0, "11")
    assert ui._spin_quantidade.get() == ""
    ui._spin_quantidade.insert(0, "10")
    assert ui.quantidade_desejada == 10


def test_callbacks_de_configuracao(root):
    reg = _Registro()
    ui = _criar(root, reg)
    # Eventos de teclado do Tk vão para o widget com foco: mostrar a janela
    # e focar o campo antes de gerar <Return>.
    root.deiconify()
    ui._spin_quantidade.focus_force()
    root.update()

    ui._radios["parafuso"].invoke()
    assert reg.configs[-1] == ("parafuso", None)

    ui._spin_quantidade.insert(0, "12")
    ui._spin_quantidade.event_generate("<Return>")
    root.update()
    assert reg.configs[-1] == ("parafuso", 12)

    # Mesmo par de novo (ex.: Enter + saída de foco) não é reemitido.
    n = len(reg.configs)
    ui._emitir_config()
    assert len(reg.configs) == n

    ui._radios["porca"].invoke()
    assert reg.configs[-1] == ("porca", 12)

    # Seta do Spinbox também confirma.
    ui._spin_quantidade.event_generate("<<Increment>>")
    root.update()
    assert reg.configs[-1] == ("porca", 13)

    # Campo vazio -> quantidade None.
    ui._spin_quantidade.delete(0, "end")
    ui._spin_quantidade.event_generate("<Return>")
    root.update()
    assert reg.configs[-1] == ("porca", None)


def test_botao_reset_chama_callback(root):
    reg = _Registro()
    ui = _criar(root, reg)
    ui._btn_reset.invoke()
    ui._btn_reset.invoke()
    assert reg.resets == 2
    assert reg.configs == []  # reset não altera a configuração


def test_fechar_chama_on_close(root):
    reg = _Registro()
    _criar(root, reg, com_close=True)
    _fechar_pela_janela(root)
    assert reg.fechamentos == 1
    assert root.winfo_exists()  # quem destrói é o main.py


def test_fechar_sem_on_close_destroi_e_ignora_chamadas_tardias(root):
    reg = _Registro()
    ui = _criar(root, reg, com_close=False)
    ui.mostrar_frame(_frame())
    _fechar_pela_janela(root)
    assert not root.winfo_exists()
    # Chamadas agendadas pelo main.py que cheguem depois não levantam.
    ui.mostrar_frame(_frame())
    ui.mostrar_frame(None)
    ui.atualizar_painel(1, 2, Estado.CONTANDO)


def test_on_close_que_destroi_a_janela_nao_gera_excecao(root):
    ui = interface.InterfaceContador(
        root, on_config_change=lambda c, q: None, on_reset=lambda: None, on_close=root.destroy
    )
    root.update()
    ui.mostrar_frame(_frame())
    _fechar_pela_janela(root)
    ui.mostrar_frame(_frame())
    ui.atualizar_painel(None, None, Estado.ERRO_CAMERA)
