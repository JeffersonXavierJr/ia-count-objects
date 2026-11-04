"""Testes de integração ponta a ponta da interface (Sprint 9, tarefa 9.3).

Montam a aplicação como o `main.main()` faz — `AplicacaoContador` +
`Orquestrador` + `PipelineWorker` + `GerenciadorCamera` + a interface REAL
(`interface.InterfaceContador`) sobre uma janela Tk real — trocando apenas o
hardware: a webcam é uma "bancada" falsa (frames sintéticos, cabo que pode
ser "desconectado") e o detector é uma "cena" falsa (detecções fixas, ex.:
12 parafusos + 4 porcas). ROI (`camera.apply_roi`), desenho
(`overlay.draw_detections`), contagem e estabilização são os reais.

O teste DIRIGE OS WIDGETS (radio de componente, campo de quantidade + Enter,
setas do Spinbox, botão RESET via `.invoke()`, fechamento via protocolo
WM_DELETE_WINDOW) e confere o que aparece nos labels do painel. Não repete o
que já está coberto:
- `test_interface.py`: widgets isolados (validação do campo, layout, callbacks);
- `test_main.py`: orquestrador/worker com interface fake e um smoke com a
  interface real chamando os callbacks diretamente.

Determinismo (sem sleeps longos): a câmera falsa só entrega um frame quando
o teste libera um "passo"; o teste então bombeia `root.update()` (timeout
curto) até a interface consumir o resultado daquele frame.

SUPOSIÇÃO DOCUMENTADA (ponto em aberto, PRD 29 itens 8/9; TASKS 8.2): o N
da estabilização NÃO está decidido. Os testes usam o valor corrente de
`config.FRAMES_ESTABILIZACAO` (baseline 5) e verificam o comportamento para
qualquer N >= 1, em vez de fixar 5.

Não usam webcam real nem YOLO real (o roteiro com hardware real está em
`plano_teste_manual_interface.md`). Pulados se o Tk não puder ser iniciado.

Uso (raiz do repositório): venv\\Scripts\\python.exe -m pytest contador_componentes/tests -q
"""

from __future__ import annotations

import gc
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from functools import partial

import numpy as np
import pytest

from contador_componentes.app import config as app_config
from contador_componentes.app.camera import CameraError, apply_roi
from contador_componentes.app.counter import EstabilizadorContagem
from contador_componentes.app.detector import Deteccao, load_model, run_inference
from contador_componentes.app.interface import (
    TEXTO_SEM_IMAGEM,
    TEXTO_SEM_VALOR,
    InterfaceContador,
)
from contador_componentes.app.main import (
    AplicacaoContador,
    CaixaUltimoResultado,
    GerenciadorCamera,
    Orquestrador,
    PipelineWorker,
)
from contador_componentes.app.overlay import draw_detections

# Valor corrente (ponto em aberto) — ver docstring do módulo.
N = app_config.FRAMES_ESTABILIZACAO

LARGURA, ALTURA = 640, 480  # resolução do frame sintético
# ROI explícita cobrindo o frame inteiro: exercita o recorte real sem
# depender do `config.ROI` (que será calibrado para a câmera real).
ROI_TESTE = (0, 0, LARGURA, ALTURA)

TIMEOUT_S = 3.0
AGUARDANDO = "AGUARDANDO CONFIGURAÇÃO"
CONTANDO = "CONTANDO"
ATINGIDA = "QUANTIDADE ATINGIDA"
EXCEDIDA = "QUANTIDADE EXCEDIDA"
ERRO_CAMERA = "ERRO DE CÂMERA"
MODELO_NAO_CARREGADO = "MODELO NÃO CARREGADO"


# ---------------------------------------------------------------- fakes
class Cena:
    """Detector falso: devolve as peças "sobre a bandeja" (thread-safe)."""

    def __init__(self, parafusos: int, porcas: int) -> None:
        self._lock = threading.Lock()
        self.definir(parafusos, porcas)
        self.inferencias = 0

    def definir(self, parafusos: int, porcas: int) -> None:
        with self._lock:
            self._parafusos, self._porcas = parafusos, porcas

    def inferir(self, recorte: np.ndarray) -> list[Deteccao]:
        with self._lock:
            self.inferencias += 1
            classes = [0] * self._parafusos + [1] * self._porcas
        altura, largura = recorte.shape[:2]
        deteccoes = []
        for i, classe_id in enumerate(classes):
            # Caixas 40x40 em grade de 8 colunas, dentro do recorte.
            x, y = 10 + (i % 8) * 70, 10 + (i // 8) * 70
            assert x + 40 < largura and y + 40 < altura
            deteccoes.append(
                Deteccao(
                    classe_id=classe_id,
                    classe_nome={0: "parafuso", 1: "porca"}[classe_id],
                    confianca=0.9,
                    bbox=(x, y, x + 40, y + 40),
                )
            )
        return deteccoes


class _CameraFalsa:
    def __init__(self) -> None:
        self.liberacoes = 0


class Bancada:
    """Webcam falsa: entrega um frame por "passo" liberado pelo teste e pode
    ter o cabo "desconectado" (abrir/ler passam a levantar `CameraError`)."""

    def __init__(self, conectada: bool = True) -> None:
        self.passos = threading.Semaphore(0)
        self._lock = threading.Lock()
        self._conectada = conectada
        self.cameras: list[_CameraFalsa] = []
        self.falhas_abertura = 0

    def conectar(self) -> None:
        with self._lock:
            self._conectada = True

    def desconectar(self) -> None:
        with self._lock:
            self._conectada = False
        # Destrava uma leitura pendente para que ela falhe agora.
        self.passos.release()

    def abrir(self) -> _CameraFalsa:
        with self._lock:
            if not self._conectada:
                self.falhas_abertura += 1
                raise CameraError("teste: webcam desconectada")
            camera = _CameraFalsa()
            self.cameras.append(camera)
            return camera

    def ler(self, _camera: _CameraFalsa) -> np.ndarray:
        if not self.passos.acquire(timeout=5.0):
            raise CameraError("teste: nenhum frame liberado")
        with self._lock:
            if not self._conectada:
                raise CameraError("teste: falha de leitura (cabo removido)")
        return np.full((ALTURA, LARGURA, 3), 90, dtype=np.uint8)

    def liberar(self, camera: _CameraFalsa) -> None:
        camera.liberacoes += 1


class CaixaInstrumentada(CaixaUltimoResultado):
    """Conta quantos resultados COM frame a interface já consumiu.

    Resultados de erro (frame `None`) não contam: assim um passo só termina
    quando o frame liberado pelo teste chegou à tela.
    """

    def __init__(self) -> None:
        super().__init__()
        self.frames_consumidos = 0
        self.consumidos = 0  # inclui resultados de erro

    def retirar(self):
        resultado = super().retirar()
        if resultado is not None:
            self.consumidos += 1
        if resultado is not None and resultado.frame_anotado is not None:
            self.frames_consumidos += 1
        return resultado


class DesenhoEspiao:
    """Usa o `draw_detections` real e registra as caixas desenhadas."""

    def __init__(self) -> None:
        self.ultimas: list[Deteccao] = []

    def __call__(self, frame, deteccoes):
        self.ultimas = list(deteccoes)
        return draw_detections(frame, deteccoes)


@dataclass
class App:
    root: tk.Toplevel
    app: AplicacaoContador
    ui: InterfaceContador
    worker: PipelineWorker
    orquestrador: Orquestrador
    caixa: CaixaInstrumentada
    bancada: Bancada
    cena: Cena
    desenho: DesenhoEspiao
    cargas_modelo: list


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def tk_raiz():
    """Um único `tk.Tk()` por módulo (criar/destruir vários `Tk` no mesmo
    processo é instável no Windows — ver `test_interface.py`). Cada teste usa
    um `Toplevel` como janela da aplicação; `AplicacaoContador.encerrar`
    destrói esse `Toplevel` como destruiria a raiz.

    Criar um `Tk` novo depois que outro módulo já criou/destruiu o seu falha
    de forma INTERMITENTE no Windows ("Can't find a usable tk.tcl" /
    "invalid command name tcl_findLibrary"), embora o Tk esteja disponível.
    Por isso há algumas tentativas antes de pular: um skip aqui esconderia
    os testes da 9.3 sem ninguém perceber."""
    ultimo_erro: tk.TclError | None = None
    for _ in range(5):
        try:
            raiz = tk.Tk()
            break
        except tk.TclError as erro:
            ultimo_erro = erro
            time.sleep(0.05)
    else:
        pytest.skip(f"Tk indisponivel apos 5 tentativas: {ultimo_erro}")
    raiz.withdraw()
    yield raiz
    try:
        raiz.destroy()
    except tk.TclError:
        pass


@pytest.fixture
def montar(tk_raiz):
    # Coleta na thread principal o lixo Tk de testes anteriores (StringVar de
    # janelas já destruídas). Sem isso, um gc disparado na thread worker
    # (ex.: durante `load_model`) roda `Variable.__del__` fora da thread do Tk
    # -> "RuntimeError: main thread is not in main loop" (ignorado, mas ruidoso).
    gc.collect()
    criados: list[App] = []

    def _montar(
        *,
        cena: Cena | None = None,
        bancada: Bancada | None = None,
        carregar=None,
    ) -> App:
        cena = cena or Cena(parafusos=12, porcas=4)
        bancada = bancada or Bancada()
        cargas: list = []

        def carregar_padrao():
            cargas.append(time.monotonic())
            return cena.inferir

        root = tk.Toplevel(tk_raiz)
        desenho = DesenhoEspiao()
        orquestrador = Orquestrador(
            EstabilizadorContagem(),  # N = config.FRAMES_ESTABILIZACAO
            aplicar_roi=partial(apply_roi, roi=ROI_TESTE),
            desenhar=desenho,
        )
        caixa = CaixaInstrumentada()
        worker = PipelineWorker(
            orquestrador,
            caixa,
            GerenciadorCamera(abrir=bancada.abrir, ler=bancada.ler, liberar=bancada.liberar),
            carregar_inferencia=carregar or carregar_padrao,
            intervalo_reconexao_s=0.01,
        )
        app = AplicacaoContador(
            root,
            orquestrador,
            caixa,
            worker,
            criar_interface=InterfaceContador,
            intervalo_ms=5,
            timeout_encerramento_s=2.0,
        )
        app.iniciar()
        # Janela visível: eventos de teclado (Enter) vão para o widget com foco.
        root.deiconify()
        root.update()
        ctx = App(
            root, app, app._interface, worker, orquestrador, caixa, bancada, cena, desenho, cargas
        )
        criados.append(ctx)
        return ctx

    yield _montar

    for ctx in criados:  # garante limpeza mesmo se o teste falhar no meio
        ctx.bancada.conectar()
        ctx.bancada.passos.release(1000)
        ctx.app.encerrar()
    criados.clear()
    gc.collect()


# ---------------------------------------------------------------- helpers
def painel(ctx: App) -> dict[str, str]:
    ui = ctx.ui
    return {
        "detectada": str(ui._lbl_detectado.cget("text")),
        "desejada": str(ui._lbl_esperado.cget("text")),
        "status": str(ui._lbl_status.cget("text")),
        "progresso": str(ui._lbl_progresso.cget("text")),
    }


def video_mostra_imagem(ctx: App) -> bool:
    lbl = ctx.ui._lbl_video
    return str(lbl.cget("image")) != "" and str(lbl.cget("text")) == ""


def bombear_ate(ctx: App, condicao, timeout: float = TIMEOUT_S) -> None:
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        ctx.root.update()
        if condicao():
            return
        time.sleep(0.002)
    raise AssertionError(f"Condicao nao atingida em {timeout} s; painel={painel(ctx)}")


def passo(ctx: App) -> dict[str, str]:
    """Libera UM frame da câmera e espera ele aparecer na janela."""
    antes = ctx.caixa.frames_consumidos
    ctx.bancada.passos.release()
    bombear_ate(ctx, lambda: ctx.caixa.frames_consumidos > antes)
    return painel(ctx)


def passos(ctx: App, quantidade: int) -> list[dict[str, str]]:
    return [passo(ctx) for _ in range(quantidade)]


def selecionar(ctx: App, componente: str) -> None:
    """Clica no radio "Parafuso"/"Porca"."""
    ctx.ui._radios[componente].invoke()
    ctx.root.update()


def digitar_quantidade(ctx: App, texto: str) -> None:
    """Apaga o campo, digita `texto` e confirma com Enter."""
    spin = ctx.ui._spin_quantidade
    spin.focus_force()
    ctx.root.update()
    spin.delete(0, "end")
    spin.insert(0, texto)
    spin.event_generate("<Return>")
    ctx.root.update()


def esperar_atingir(ctx: App, alvo_status: str) -> list[dict[str, str]]:
    """N frames iguais: os N-1 primeiros ainda CONTANDO, o N-ésimo no alvo."""
    historico = passos(ctx, N)
    assert [p["status"] for p in historico] == [CONTANDO] * (N - 1) + [alvo_status]
    return historico


def fechar_pelo_x(ctx: App) -> None:
    """O que o botão X da janela faz (protocolo WM_DELETE_WINDOW)."""
    ctx.bancada.passos.release(1000)  # destrava uma leitura pendente
    ctx.root.tk.call(ctx.root.protocol("WM_DELETE_WINDOW"))


def assert_encerrada(ctx: App) -> None:
    assert not ctx.worker._thread.is_alive()
    assert [c.liberacoes for c in ctx.bancada.cameras] == [1] * len(ctx.bancada.cameras)
    # A janela da aplicação (um Toplevel sobre a raiz do módulo) foi destruída.
    assert not ctx.root.winfo_exists()


def classes_desenhadas(ctx: App) -> list[int]:
    return sorted(d.classe_id for d in ctx.desenho.ultimas)


# ------------------------------------------------------------ 9.3.1
def test_9_3_1_troca_de_componente_muda_contagem_exibida(montar):
    """Cena com 12 parafusos + 4 porcas: Parafuso -> 12, Porca -> 4 (RB-01)."""
    ctx = montar(cena=Cena(parafusos=12, porcas=4))

    # Sem componente: aguardando, nada contado, todas as 16 caixas desenhadas.
    p = passo(ctx)
    assert p["status"] == AGUARDANDO
    assert p["detectada"] == TEXTO_SEM_VALOR
    assert video_mostra_imagem(ctx)
    assert len(ctx.desenho.ultimas) == 16

    # Parafuso (ainda sem quantidade): mostra 12, segue aguardando config.
    selecionar(ctx, "parafuso")
    p = passo(ctx)
    assert (p["detectada"], p["desejada"], p["status"]) == ("12", TEXTO_SEM_VALOR, AGUARDANDO)
    assert classes_desenhadas(ctx) == [0] * 12  # só parafusos na imagem

    digitar_quantidade(ctx, "12")
    assert ctx.orquestrador.configuracao.quantidade == 12
    historico = esperar_atingir(ctx, ATINGIDA)
    assert all(h["detectada"] == "12" and h["desejada"] == "12" for h in historico)

    # Troca para Porca: mesma cena, contagem exibida passa a 4 já no 1º frame.
    selecionar(ctx, "porca")
    p = passo(ctx)
    assert (p["detectada"], p["desejada"], p["status"]) == ("4", "12", CONTANDO)
    assert classes_desenhadas(ctx) == [1] * 4

    digitar_quantidade(ctx, "4")
    esperar_atingir(ctx, ATINGIDA)
    assert painel(ctx)["detectada"] == "4"

    # Volta para Parafuso (alvo 4): 12 > 4 -> EXCEDIDA só após N frames novos.
    selecionar(ctx, "parafuso")
    p = passo(ctx)
    assert (p["detectada"], p["status"]) == ("12", CONTANDO)
    if N > 1:
        assert p["progresso"] == f"estabilizando 1/{N}"
    passos(ctx, N - 1)
    assert painel(ctx)["status"] == EXCEDIDA

    fechar_pelo_x(ctx)
    assert_encerrada(ctx)


# ------------------------------------------------------------ 9.3.2
def test_9_3_2_quantidade_desejada_atualiza_em_tempo_real(montar):
    """Mudar a quantidade atualiza "desejada" e o status sem reiniciar a app."""
    ctx = montar(cena=Cena(parafusos=12, porcas=4))
    selecionar(ctx, "parafuso")
    digitar_quantidade(ctx, "20")
    p = passo(ctx)
    assert (p["detectada"], p["desejada"], p["status"], p["progresso"]) == (
        "12", "20", CONTANDO, ""
    )
    thread_original = ctx.worker._thread

    # 20 -> 12: desejada muda já no próximo frame; ATINGIDA só após N.
    digitar_quantidade(ctx, "12")
    historico = esperar_atingir(ctx, ATINGIDA)
    assert historico[0]["desejada"] == "12"
    if N > 1:
        assert [h["progresso"] for h in historico[:-1]] == [
            f"estabilizando {k}/{N}" for k in range(1, N)
        ]
    assert historico[-1]["progresso"] == ""

    # 12 -> 10 com ATINGIDA na tela: não fica "atingida" velha; reestabiliza.
    digitar_quantidade(ctx, "10")
    historico = esperar_atingir(ctx, EXCEDIDA)
    assert historico[0]["desejada"] == "10"

    # Setas do Spinbox (10 -> 11 -> 12) também valem em tempo real.
    for _ in range(2):
        ctx.ui._spin_quantidade.event_generate("<<Increment>>")
        ctx.root.update()
    assert ctx.orquestrador.configuracao.quantidade == 12
    historico = esperar_atingir(ctx, ATINGIDA)
    assert historico[0]["desejada"] == "12"

    # Campo apagado + Enter: sem alvo -> AGUARDANDO, desejada "—".
    digitar_quantidade(ctx, "")
    p = passo(ctx)
    assert (p["desejada"], p["status"]) == (TEXTO_SEM_VALOR, AGUARDANDO)

    # Nada foi reiniciado: mesma thread, um único carregamento do modelo e
    # uma única abertura de câmera durante todo o teste.
    assert ctx.worker._thread is thread_original and thread_original.is_alive()
    assert len(ctx.cargas_modelo) == 1
    assert len(ctx.bancada.cameras) == 1

    fechar_pelo_x(ctx)
    assert_encerrada(ctx)


# ------------------------------------------------------------ 9.3.3
def test_9_3_3_reset_permite_nova_contagem(montar):
    """RB-05: ATINGIDA -> RESET -> recomeça e volta a ATINGIDA após N frames."""
    ctx = montar(cena=Cena(parafusos=12, porcas=4))
    selecionar(ctx, "parafuso")
    digitar_quantidade(ctx, "12")
    esperar_atingir(ctx, ATINGIDA)

    # RESET com a mesma cena: recomeça do zero (CONTANDO 1/N) e reatinge.
    ctx.ui._btn_reset.invoke()
    ctx.root.update()
    historico = esperar_atingir(ctx, ATINGIDA)
    if N > 1:
        assert historico[0]["progresso"] == f"estabilizando 1/{N}"

    # Fluxo real do operador: descarga manual (bandeja vazia) -> RESET ->
    # novo lote de 12 -> ATINGIDA de novo após N frames.
    ctx.cena.definir(parafusos=0, porcas=0)
    p = passo(ctx)
    assert (p["detectada"], p["status"]) == ("0", CONTANDO)
    ctx.ui._btn_reset.invoke()
    ctx.root.update()

    # O RESET mantém a configuração (componente e quantidade).
    assert ctx.ui.classe_selecionada == "parafuso"
    assert ctx.ui._spin_quantidade.get() == "12"
    assert ctx.orquestrador.configuracao.quantidade == 12, ctx.ui._spin_quantidade.get()
    assert painel(ctx)["desejada"] == "12"

    ctx.cena.definir(parafusos=12, porcas=4)
    historico = esperar_atingir(ctx, ATINGIDA)
    assert all(h["detectada"] == "12" for h in historico)

    # Vários RESETs seguidos antes do próximo frame equivalem a um só.
    for _ in range(3):
        ctx.ui._btn_reset.invoke()
    esperar_atingir(ctx, ATINGIDA)

    fechar_pelo_x(ctx)
    assert_encerrada(ctx)


# ------------------------------------------------------------ 9.3.4
def test_9_3_4_camera_desconectada_mostra_erro_e_reconecta(montar):
    """Sem webcam -> ERRO DE CÂMERA; conecta -> conta; cabo removido no meio
    -> ERRO DE CÂMERA; reconecta -> volta a contar (sem reiniciar a app)."""
    bancada = Bancada(conectada=False)
    ctx = montar(bancada=bancada, cena=Cena(parafusos=12, porcas=4))
    selecionar(ctx, "parafuso")
    digitar_quantidade(ctx, "12")

    # Aplicação aberta sem webcam: erro na tela, placeholder, segue tentando.
    bombear_ate(ctx, lambda: painel(ctx)["status"] == ERRO_CAMERA)
    bombear_ate(ctx, lambda: bancada.falhas_abertura >= 3)
    assert str(ctx.ui._lbl_video.cget("text")) == TEXTO_SEM_IMAGEM
    assert painel(ctx)["detectada"] == TEXTO_SEM_VALOR
    # O erro é republicado periodicamente com a configuração corrente.
    bombear_ate(ctx, lambda: painel(ctx)["desejada"] == "12")
    assert painel(ctx)["status"] == ERRO_CAMERA
    assert ctx.root.winfo_exists()

    # Webcam conectada: volta a contar sem reiniciar a aplicação.
    bancada.conectar()
    esperar_atingir(ctx, ATINGIDA)
    assert video_mostra_imagem(ctx)

    # Cabo removido com a contagem ATINGIDA na tela.
    bancada.desconectar()
    bombear_ate(ctx, lambda: painel(ctx)["status"] == ERRO_CAMERA)
    p = painel(ctx)
    assert (p["detectada"], p["desejada"], p["progresso"]) == (TEXTO_SEM_VALOR, "12", "")
    assert str(ctx.ui._lbl_video.cget("text")) == TEXTO_SEM_IMAGEM
    # A câmera com falha foi liberada (uma vez) para tentar reabrir.
    bombear_ate(ctx, lambda: bancada.cameras[0].liberacoes == 1)

    # Reconectado: a estabilização recomeça do zero (não volta "atingida" direto).
    bancada.conectar()
    historico = esperar_atingir(ctx, ATINGIDA)
    if N > 1:
        assert historico[0]["progresso"] == f"estabilizando 1/{N}"
    assert len(bancada.cameras) == 2
    assert len(ctx.cargas_modelo) == 1  # modelo não foi recarregado

    fechar_pelo_x(ctx)
    assert_encerrada(ctx)


@pytest.mark.parametrize("problema", ["inexistente", "corrompido"])
def test_9_3_4_modelo_ausente_mostra_modelo_nao_carregado(montar, tmp_path, problema):
    """`best.pt` ausente/corrompido -> MODELO NÃO CARREGADO, janela continua
    utilizável e fecha normalmente. Usa o `detector.load_model` REAL."""
    caminho = tmp_path / "best.pt"
    if problema == "corrompido":
        caminho.write_bytes(b"isto nao e um modelo YOLO")
    tentativas: list[int] = []

    def carregar_real():
        tentativas.append(1)
        return partial(run_inference, load_model(caminho))

    ctx = montar(carregar=carregar_real)
    bombear_ate(ctx, lambda: painel(ctx)["status"] == MODELO_NAO_CARREGADO, timeout=30.0)
    assert str(ctx.ui._lbl_video.cget("text")) == TEXTO_SEM_IMAGEM
    assert painel(ctx)["detectada"] == TEXTO_SEM_VALOR

    # Controles continuam funcionando: a desejada acompanha a configuração.
    selecionar(ctx, "porca")
    digitar_quantidade(ctx, "4")
    bombear_ate(ctx, lambda: painel(ctx)["desejada"] == "4")
    assert painel(ctx)["status"] == MODELO_NAO_CARREGADO
    ctx.ui._btn_reset.invoke()
    antes = ctx.caixa.consumidos
    bombear_ate(ctx, lambda: ctx.caixa.consumidos > antes)  # próxima republicação
    assert painel(ctx)["status"] == MODELO_NAO_CARREGADO

    # Sem modelo a câmera nunca é aberta; uma só tentativa de carga.
    assert ctx.bancada.cameras == []
    assert len(tentativas) == 1

    fechar_pelo_x(ctx)
    assert_encerrada(ctx)
