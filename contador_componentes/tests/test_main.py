"""Testes da orquestração `app/main.py` (Sprint 9, tarefa 9.2).

Sem hardware e sem YOLO real: câmera, modelo e interface são fakes. Cobrem
filtragem pela classe selecionada (RB-01), troca de configuração e reset
reiniciando a estabilização, erro de câmera (com reconexão), modelo ausente
e encerramento liberando a câmera exatamente uma vez.

Uso (raiz do repositório): python -m pytest contador_componentes/tests -q
"""

from __future__ import annotations

import threading
import time

import numpy as np
import pytest

from contador_componentes.app.camera import CameraError
from contador_componentes.app.counter import EstabilizadorContagem, Estado
from contador_componentes.app.detector import Deteccao, ModelError
from contador_componentes.app.main import (
    AplicacaoContador,
    CaixaUltimoResultado,
    GerenciadorCamera,
    Orquestrador,
    PipelineWorker,
    ResultadoFrame,
)

N = 3


def _det(classe_id: int) -> Deteccao:
    nome = {0: "parafuso", 1: "porca"}[classe_id]
    return Deteccao(classe_id=classe_id, classe_nome=nome, confianca=0.9, bbox=(1, 1, 10, 10))


def _frame() -> np.ndarray:
    return np.zeros((40, 40, 3), dtype=np.uint8)


def _inferir_fixo(parafusos: int, porcas: int):
    deteccoes = [_det(0)] * parafusos + [_det(1)] * porcas
    return lambda _frame: list(deteccoes)


class _DesenhoEspiao:
    """Substitui `draw_detections`, registrando o que seria desenhado."""

    def __init__(self) -> None:
        self.desenhadas: list = []

    def __call__(self, frame, deteccoes):
        self.desenhadas = list(deteccoes)
        return frame.copy()


def _orquestrador(desenho=None) -> Orquestrador:
    return Orquestrador(
        EstabilizadorContagem(n_frames=N),
        aplicar_roi=lambda f: f,
        desenhar=desenho or _DesenhoEspiao(),
    )


# --------------------------------------------------------------- Orquestrador
def test_conta_somente_classe_selecionada():
    desenho = _DesenhoEspiao()
    orq = _orquestrador(desenho)
    inferir = _inferir_fixo(parafusos=3, porcas=2)

    orq.definir_configuracao("parafuso", 10)
    r = orq.processar_frame(_frame(), inferir)
    assert r.detectado == 3
    assert all(d.classe_id == 0 for d in desenho.desenhadas)
    assert len(desenho.desenhadas) == 3

    orq.definir_configuracao("porca", 10)
    r = orq.processar_frame(_frame(), inferir)
    assert r.detectado == 2
    assert all(d.classe_id == 1 for d in desenho.desenhadas)


def test_sem_classe_aguarda_e_desenha_todas():
    desenho = _DesenhoEspiao()
    orq = _orquestrador(desenho)
    r = orq.processar_frame(_frame(), _inferir_fixo(2, 2))
    assert r.estado is Estado.AGUARDANDO_CONFIGURACAO
    assert r.detectado is None
    assert len(desenho.desenhadas) == 4
    assert r.frame_anotado is not None


def test_atinge_apos_n_frames_e_troca_de_config_reinicia():
    orq = _orquestrador()
    inferir = _inferir_fixo(parafusos=3, porcas=2)
    orq.definir_configuracao("parafuso", 3)

    estados = [orq.processar_frame(_frame(), inferir).estado for _ in range(N)]
    assert estados[:-1] == [Estado.CONTANDO] * (N - 1)
    assert estados[-1] is Estado.QUANTIDADE_ATINGIDA

    # Troca de componente (porca, alvo 2): a estabilização recomeça do zero.
    orq.definir_configuracao("porca", 2)
    r = orq.processar_frame(_frame(), inferir)
    assert r.estado is Estado.CONTANDO
    assert r.frames_consecutivos == 1
    assert r.esperado == 2
    for _ in range(N - 1):
        r = orq.processar_frame(_frame(), inferir)
    assert r.estado is Estado.QUANTIDADE_ATINGIDA


def test_troca_de_quantidade_reinicia_estabilizacao():
    orq = _orquestrador()
    inferir = _inferir_fixo(parafusos=3, porcas=0)
    orq.definir_configuracao("parafuso", 3)
    for _ in range(N):
        orq.processar_frame(_frame(), inferir)
    orq.definir_configuracao("parafuso", 2)  # agora 3 > 2
    r = orq.processar_frame(_frame(), inferir)
    assert r.estado is Estado.CONTANDO
    assert r.frames_consecutivos == 1


def test_reset_reinicia_estabilizacao_mantendo_config():
    orq = _orquestrador()
    inferir = _inferir_fixo(parafusos=3, porcas=0)
    orq.definir_configuracao("parafuso", 3)
    for _ in range(N):
        r = orq.processar_frame(_frame(), inferir)
    assert r.estado is Estado.QUANTIDADE_ATINGIDA

    orq.solicitar_reset()
    r = orq.processar_frame(_frame(), inferir)
    assert r.estado is Estado.CONTANDO
    assert r.frames_consecutivos == 1
    assert r.esperado == 3


def test_configuracao_invalida_mantem_anterior():
    orq = _orquestrador()
    orq.definir_configuracao("parafuso", 3)
    with pytest.raises(ValueError):
        orq.definir_configuracao("arruela", 3)
    with pytest.raises(ValueError):
        orq.definir_configuracao("porca", 0)
    assert orq.configuracao.classe == "parafuso"
    assert orq.configuracao.quantidade == 3


def test_erro_de_camera_quebra_sequencia():
    orq = _orquestrador()
    inferir = _inferir_fixo(parafusos=3, porcas=0)
    orq.definir_configuracao("parafuso", 3)
    for _ in range(N - 1):
        orq.processar_frame(_frame(), inferir)

    r = orq.processar_erro(CameraError("desconectada"))
    assert r.estado is Estado.ERRO_CAMERA
    assert r.frame_anotado is None
    assert r.detectado is None
    assert r.esperado == 3

    r = orq.processar_frame(_frame(), inferir)
    assert r.estado is Estado.CONTANDO
    assert r.frames_consecutivos == 1


def test_erro_de_modelo_e_erro_imprevisto():
    orq = _orquestrador()
    assert orq.processar_erro(ModelError("sem best.pt")).estado is Estado.MODELO_NAO_CARREGADO
    with pytest.raises(ValueError):
        orq.processar_erro(RuntimeError("outro"))


# ------------------------------------------------------------------ fakes
class _CameraFake:
    def __init__(self) -> None:
        self.liberacoes = 0


class _Hardware:
    """Funções abrir/ler/liberar falsas, com falhas programáveis."""

    def __init__(
        self,
        falhas_abertura: int = 0,
        falhar_leitura_n: int | None = None,
        passo_a_passo: bool = False,
    ) -> None:
        # passo_a_passo: cada leitura espera `liberar_frames` (teste determinístico).
        self.passos = threading.Semaphore(0) if passo_a_passo else None
        self.falhas_abertura = falhas_abertura
        self.falhar_leitura_n = falhar_leitura_n
        self.cameras: list[_CameraFake] = []
        self.leituras = 0
        self.lock = threading.Lock()

    def abrir(self):
        with self.lock:
            if self.falhas_abertura > 0:
                self.falhas_abertura -= 1
                raise CameraError("webcam ausente")
            camera = _CameraFake()
            self.cameras.append(camera)
            return camera

    def liberar_frames(self, quantidade: int = 1) -> None:
        for _ in range(quantidade):
            self.passos.release()

    def ler(self, camera):
        if self.passos is not None:
            if not self.passos.acquire(timeout=5.0):
                raise CameraError("teste sem frames liberados")
        else:
            time.sleep(0.002)
        with self.lock:
            self.leituras += 1
            if self.falhar_leitura_n is not None and self.leituras == self.falhar_leitura_n:
                raise CameraError("falha de leitura")
        return _frame()

    def liberar(self, camera) -> None:
        camera.liberacoes += 1

    def gerenciador(self) -> GerenciadorCamera:
        return GerenciadorCamera(abrir=self.abrir, ler=self.ler, liberar=self.liberar)


def _coletar(caixa: CaixaUltimoResultado, condicao, timeout: float = 3.0) -> list[ResultadoFrame]:
    """Retira resultados da caixa até `condicao(resultados)` ser verdadeira."""
    resultados: list[ResultadoFrame] = []
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        r = caixa.retirar()
        if r is not None:
            resultados.append(r)
            if condicao(resultados):
                return resultados
        time.sleep(0.001)
    raise AssertionError(f"Condicao nao atingida; resultados: {[x.estado for x in resultados]}")


def _worker(orq, caixa, hw, carregar=None) -> PipelineWorker:
    return PipelineWorker(
        orq,
        caixa,
        hw.gerenciador(),
        carregar_inferencia=carregar or (lambda: _inferir_fixo(3, 1)),
        intervalo_reconexao_s=0.01,
    )


# ------------------------------------------------------------------ worker
def test_worker_modelo_ausente_nao_abre_camera():
    def carregar():
        raise ModelError("best.pt nao encontrado")

    hw = _Hardware()
    caixa = CaixaUltimoResultado()
    worker = _worker(_orquestrador(), caixa, hw, carregar)
    worker.iniciar()
    try:
        r = _coletar(caixa, lambda rs: True)
        assert r[0].estado is Estado.MODELO_NAO_CARREGADO
        assert r[0].frame_anotado is None
    finally:
        worker.sinalizar_parada()
        assert worker.aguardar(2.0)
    assert hw.cameras == []


def test_worker_erro_de_camera_e_reconexao():
    hw = _Hardware(falhas_abertura=2)
    orq = _orquestrador()
    orq.definir_configuracao("parafuso", 3)
    caixa = CaixaUltimoResultado()
    worker = _worker(orq, caixa, hw)
    worker.iniciar()
    try:
        rs = _coletar(caixa, lambda rs: rs[-1].estado is Estado.QUANTIDADE_ATINGIDA)
        assert rs[0].estado is Estado.ERRO_CAMERA
        assert rs[-1].detectado == 3
    finally:
        worker.sinalizar_parada()
        assert worker.aguardar(2.0)
    assert len(hw.cameras) == 1
    assert hw.cameras[0].liberacoes == 1


def test_worker_falha_de_leitura_libera_e_reabre():
    hw = _Hardware(falhar_leitura_n=3)
    orq = _orquestrador()
    orq.definir_configuracao("parafuso", 3)
    caixa = CaixaUltimoResultado()
    worker = _worker(orq, caixa, hw)
    worker.iniciar()
    try:
        _coletar(caixa, lambda rs: len(hw.cameras) >= 2 and rs[-1].estado is not Estado.ERRO_CAMERA)
    finally:
        worker.sinalizar_parada()
        assert worker.aguardar(2.0)
    assert [c.liberacoes for c in hw.cameras] == [1] * len(hw.cameras)


def test_worker_roi_invalida_vira_erro_de_camera():
    def roi_invalida(_frame):
        raise ValueError("ROI fora do frame")

    hw = _Hardware()
    orq = Orquestrador(EstabilizadorContagem(n_frames=N), aplicar_roi=roi_invalida)
    caixa = CaixaUltimoResultado()
    worker = _worker(orq, caixa, hw)
    worker.iniciar()
    try:
        r = _coletar(caixa, lambda rs: True)
        assert r[0].estado is Estado.ERRO_CAMERA
    finally:
        worker.sinalizar_parada()
        assert worker.aguardar(2.0)


def test_caixa_guarda_somente_o_mais_recente():
    caixa = CaixaUltimoResultado()
    assert caixa.retirar() is None
    a = ResultadoFrame(None, 1, 2, Estado.CONTANDO)
    b = ResultadoFrame(None, 2, 2, Estado.CONTANDO)
    caixa.publicar(a)
    caixa.publicar(b)
    assert caixa.retirar() is b
    assert caixa.retirar() is None


def test_gerenciador_nao_abre_apos_encerrar():
    hw = _Hardware()
    ger = hw.gerenciador()
    ger.ler_frame()
    ger.encerrar()
    ger.encerrar()
    with pytest.raises(CameraError):
        ger.ler_frame()
    assert len(hw.cameras) == 1
    assert hw.cameras[0].liberacoes == 1


# ------------------------------------------------------------- lado Tk (fake)
class _RootFake:
    def __init__(self) -> None:
        self.agendados: list = []
        self.cancelados: list = []
        self.destruicoes = 0

    def after(self, _ms, callback):
        self.agendados.append(callback)
        return len(self.agendados)

    def after_cancel(self, id_after) -> None:
        self.cancelados.append(id_after)

    def destroy(self) -> None:
        self.destruicoes += 1

    def rodar_pendente(self) -> None:
        callback = self.agendados[-1]
        callback()


class _InterfaceFake:
    def __init__(self, root, *, on_config_change, on_reset, on_close=None) -> None:
        self.root = root
        self.on_config_change = on_config_change
        self.on_reset = on_reset
        self.on_close = on_close
        self.frames: list = []
        self.paineis: list[tuple] = []
        self.thread_ids: set[int] = set()

    def mostrar_frame(self, frame_bgr) -> None:
        self.thread_ids.add(threading.get_ident())
        self.frames.append(frame_bgr)

    def atualizar_painel(self, detectado, esperado, estado, frames_consecutivos=0, n_frames=0):
        self.thread_ids.add(threading.get_ident())
        self.paineis.append((detectado, esperado, estado, frames_consecutivos, n_frames))


def _app(hw, carregar=None):
    root = _RootFake()
    orq = _orquestrador()
    caixa = CaixaUltimoResultado()
    worker = _worker(orq, caixa, hw, carregar)
    app = AplicacaoContador(
        root, orq, caixa, worker, criar_interface=_InterfaceFake, timeout_encerramento_s=2.0
    )
    return app, root, worker


def _rodar_ate(root, interface, condicao, timeout: float = 3.0) -> None:
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        root.rodar_pendente()
        if interface.paineis and condicao(interface.paineis[-1]):
            return
        time.sleep(0.005)
    raise AssertionError(f"Painel nao atingiu a condicao: {interface.paineis[-1:]}")


def _proximo_painel(root, interface, hw, timeout: float = 3.0) -> tuple:
    """Libera UM frame da câmera fake e roda o `after` até o painel mudar."""
    antes = len(interface.paineis)
    hw.liberar_frames()
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        root.rodar_pendente()
        if len(interface.paineis) > antes:
            return interface.paineis[-1]
        time.sleep(0.002)
    raise AssertionError("Painel nao foi atualizado.")


def test_aplicacao_fluxo_completo_e_encerramento():
    hw = _Hardware(passo_a_passo=True)
    app, root, worker = _app(hw)
    interface = app._interface
    app.iniciar()

    assert interface.paineis[0][2] is Estado.AGUARDANDO_CONFIGURACAO
    assert interface.frames[0] is None

    # Sem configuração: aguardando, sem contagem exibida.
    assert _proximo_painel(root, interface, hw)[:3] == (None, None, Estado.AGUARDANDO_CONFIGURACAO)
    assert interface.frames[-1] is not None

    # Usuário escolhe parafuso/3 na interface: aplicado em tempo real.
    interface.on_config_change("parafuso", 3)
    paineis = [_proximo_painel(root, interface, hw) for _ in range(N)]
    assert [p[2] for p in paineis] == [Estado.CONTANDO] * (N - 1) + [Estado.QUANTIDADE_ATINGIDA]
    assert paineis[-1] == (3, 3, Estado.QUANTIDADE_ATINGIDA, N, N)

    # Configuração inválida vinda da interface é ignorada sem derrubar a app.
    interface.on_config_change("arruela", 3)
    assert _proximo_painel(root, interface, hw)[:3] == (3, 3, Estado.QUANTIDADE_ATINGIDA)

    # RESET: estabilização recomeça do zero e volta a atingir após N frames.
    interface.on_reset()
    assert _proximo_painel(root, interface, hw)[2:4] == (Estado.CONTANDO, 1)
    for _ in range(N - 1):
        ultimo = _proximo_painel(root, interface, hw)
    assert ultimo[2] is Estado.QUANTIDADE_ATINGIDA

    # Troca de componente: porca (1 no frame fake) com alvo 1.
    interface.on_config_change("porca", 1)
    assert _proximo_painel(root, interface, hw)[:4] == (1, 1, Estado.CONTANDO, 1)

    # Interface só é chamada na thread "do Tk" (a deste teste).
    assert interface.thread_ids == {threading.get_ident()}

    hw.liberar_frames(1000)  # destrava o worker para o join
    interface.on_close()
    interface.on_close()  # idempotente
    assert root.destruicoes == 1
    assert not worker._thread.is_alive()
    assert len(hw.cameras) == 1
    assert hw.cameras[0].liberacoes == 1


def test_aplicacao_modelo_ausente_continua_aberta():
    def carregar():
        raise ModelError("best.pt nao encontrado")

    hw = _Hardware()
    app, root, _worker_ = _app(hw, carregar)
    interface = app._interface
    app.iniciar()
    _rodar_ate(root, interface, lambda p: p[2] is Estado.MODELO_NAO_CARREGADO)
    assert interface.frames[-1] is None
    assert root.destruicoes == 0  # janela continua aberta

    # Painel acompanha a quantidade esperada mesmo sem modelo.
    interface.on_config_change("porca", 4)
    _rodar_ate(root, interface, lambda p: p[1] == 4 and p[2] is Estado.MODELO_NAO_CARREGADO)

    app.encerrar()
    assert root.destruicoes == 1
    assert hw.cameras == []


def test_encerrar_com_worker_travado_libera_camera_uma_vez():
    """Join estoura o timeout: câmera liberada mesmo assim, uma única vez."""
    liberar_inferencia = threading.Event()
    em_inferencia = threading.Event()

    def inferir_travado(_frame):
        em_inferencia.set()
        liberar_inferencia.wait(5.0)
        return []

    hw = _Hardware()
    root = _RootFake()
    orq = _orquestrador()
    caixa = CaixaUltimoResultado()
    worker = _worker(orq, caixa, hw, lambda: inferir_travado)
    app = AplicacaoContador(
        root, orq, caixa, worker, criar_interface=_InterfaceFake, timeout_encerramento_s=0.05
    )
    app.iniciar()
    assert em_inferencia.wait(2.0)

    app.encerrar()
    assert root.destruicoes == 1
    assert hw.cameras[0].liberacoes == 1

    # Quando o worker destrava e termina, não libera de novo.
    liberar_inferencia.set()
    assert worker.aguardar(2.0)
    assert hw.cameras[0].liberacoes == 1


# ------------------------------------------------------ interface Tk real
def test_integracao_com_interface_real():
    """Mesmo fluxo com `interface.InterfaceContador` e um `tk.Tk` real.

    Pulado se não houver display/Tk disponível (ex.: CI headless).
    """
    tk = pytest.importorskip("tkinter")
    interface_mod = pytest.importorskip("contador_componentes.app.interface")
    try:
        root = tk.Tk()
    except tk.TclError as erro:
        pytest.skip(f"Tk indisponivel: {erro}")
    root.withdraw()

    hw = _Hardware()
    orq = _orquestrador()
    caixa = CaixaUltimoResultado()
    worker = _worker(orq, caixa, hw)
    app = AplicacaoContador(
        root,
        orq,
        caixa,
        worker,
        criar_interface=interface_mod.InterfaceContador,
        intervalo_ms=5,
        timeout_encerramento_s=2.0,
    )
    try:
        app.iniciar()
        app._ao_mudar_configuracao("parafuso", 3)
        limite = time.monotonic() + 3.0
        while time.monotonic() < limite and hw.leituras < N + 2:
            root.update()
            time.sleep(0.005)
        assert hw.leituras >= N + 2
        app._ao_resetar()
        root.update()
    finally:
        # O que o botão de fechar faz: on_close -> encerrar (não destrói sozinha).
        app._interface._ao_fechar()
    assert not worker._thread.is_alive()
    assert len(hw.cameras) == 1
    assert hw.cameras[0].liberacoes == 1
    with pytest.raises(tk.TclError):
        root.winfo_exists()
