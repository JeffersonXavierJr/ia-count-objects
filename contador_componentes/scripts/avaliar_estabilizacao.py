"""Avaliação experimental do N de estabilização (Sprint 8, tarefa 8.2 do TASKS.md).

Objetivo: dar evidência para o time decidir o N de `EstabilizadorContagem`
(`config.FRAMES_ESTABILIZACAO`, hoje 5 = baseline do PRD seção 16). A decisão
final de N é PONTO EM ABERTO (PRD seção 29, "método final de estabilização" e
"número de frames para confirmação") — este script NÃO altera `config.py`.

Ideia: a contagem BRUTA por frame é obtida uma única vez (câmera ou imagens
→ detector → counter.filter_by_class/count_objects) e a MESMA sequência é
reprocessada por um `EstabilizadorContagem` para cada N de `--ns`. Assim os N
são comparados sobre exatamente as mesmas leituras.

Métricas por N (ver `ResultadoN`):
- mudanças de estado (qualquer troca entre CONTANDO/ATINGIDA/EXCEDIDA);
- entradas/saídas de QUANTIDADE ATINGIDA ("piscadas" = saídas);
- latência até a primeira ATINGIDA estável (frames; em segundos = frames/FPS);
- % de frames em ATINGIDA.

Modos (a partir da raiz do repositório, com o venv ativo):

    # 1) webcam ao vivo (aplica a ROI de config.py); q/Esc encerra antes
    python -m contador_componentes.scripts.avaliar_estabilizacao --webcam \
        --classe parafuso --alvo 10 --segundos 60 --ns 1,3,5,8,10 \
        --salvar contagens_webcam.csv

    # 2) reprocessar contagens brutas gravadas (sem câmera nem modelo)
    python -m contador_componentes.scripts.avaliar_estabilizacao \
        --csv contagens_webcam.csv --classe parafuso --alvo 10

    # 3) rodar o modelo sobre frames ordenados por nome, como se fossem vídeo
    python -m contador_componentes.scripts.avaliar_estabilizacao \
        --imagens "pasta/frame_*.jpg" --classe porca --alvo 4

    # 3b) idem, agrupando frames em rajada em "cenas" (timestamp próximo no
    #     nome frame_AAAAMMDD_HHMMSS[_NNN]) e usando a contagem do label YOLO
    #     (ground truth) de cada cena como alvo
    python -m contador_componentes.scripts.avaliar_estabilizacao \
        --imagens contador_componentes/dataset/images/train \
                  contador_componentes/dataset/images/val \
                  contador_componentes/dataset/images/test \
        --alvo-gt --saida-csv resultado.csv

Opções comuns: `--modelo CAMINHO` (padrão config.MODEL_PATH), `--conf`,
`--ns 1,3,5,8,10`, `--offsets 0,1,-1` (só com --alvo-gt: alvo = GT+offset;
offset != 0 mede ATINGIDA FALSA, ex.: +1 = falta uma peça na bandeja).

Sem banco de dados: resultados vão para stdout e, opcionalmente, CSV.
OpenCV/ultralytics só são importados nos modos que precisam deles, para que a
parte de simulação possa ser testada sem câmera nem modelo.
"""

from __future__ import annotations

import argparse
import csv
import glob
import re
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from contador_componentes.app import counter
from contador_componentes.app.counter import (
    ConfiguracaoContagem,
    EstabilizadorContagem,
    Estado,
)

NS_PADRAO = (1, 3, 5, 8, 10)
_EXTENSOES_IMAGEM = (".jpg", ".jpeg", ".png", ".bmp")
_RAIZ_PACOTE = Path(__file__).resolve().parents[1]
_LABELS_PADRAO = _RAIZ_PACOTE / "dataset" / "labels"

# frame_AAAAMMDD_HHMMSS[_NNN] — nome gerado por scripts/dataset_capture.py
# (o Roboflow acrescenta "_jpg.rf.<hash>" depois; ignorado).
_CHAVE_FRAME = re.compile(r"frame_(\d{8})_(\d{6})(?:_(\d{3}))?(?=[_.])")


# ---------------------------------------------------------------------------
# Simulação (lógica pura — testada em tests/test_avaliar_estabilizacao.py)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResultadoN:
    """Resumo de uma sequência de contagens processada com um N.

    Convenção: o estado "anterior ao primeiro frame" é CONTANDO (configuração
    recém-definida). Logo, com N=1 e o 1º frame já no alvo, isso conta como 1
    mudança e 1 entrada em ATINGIDA.
    """

    n: int
    frames: int
    mudancas_estado: int
    entradas_atingida: int
    saidas_atingida: int
    entradas_excedida: int
    primeira_atingida: int | None  # nº do frame (1-based) da 1ª ATINGIDA
    frames_atingida: int

    @property
    def elegivel(self) -> bool:
        """A sequência tem frames suficientes para alcançar ATINGIDA com este N."""
        return self.frames >= self.n


def simular(
    contagens: Sequence[int], classe: str | int, alvo: int, n: int
) -> tuple[list[Estado], ResultadoN]:
    """Passa `contagens` (brutas, uma por frame) por um `EstabilizadorContagem(n)`."""
    cfg = ConfiguracaoContagem(classe, alvo)
    estab = EstabilizadorContagem(n)
    estados = [estab.atualizar(cfg, c) for c in contagens]

    anterior = Estado.CONTANDO
    mudancas = entradas_at = saidas_at = entradas_ex = 0
    primeira: int | None = None
    for i, estado in enumerate(estados, start=1):
        if estado is not anterior:
            mudancas += 1
            if estado is Estado.QUANTIDADE_ATINGIDA:
                entradas_at += 1
                if primeira is None:
                    primeira = i
            if anterior is Estado.QUANTIDADE_ATINGIDA:
                saidas_at += 1
            if estado is Estado.QUANTIDADE_EXCEDIDA:
                entradas_ex += 1
        anterior = estado

    return estados, ResultadoN(
        n=n,
        frames=len(contagens),
        mudancas_estado=mudancas,
        entradas_atingida=entradas_at,
        saidas_atingida=saidas_at,
        entradas_excedida=entradas_ex,
        primeira_atingida=primeira,
        frames_atingida=sum(e is Estado.QUANTIDADE_ATINGIDA for e in estados),
    )


def simular_varios(
    contagens: Sequence[int], classe: str | int, alvo: int, ns: Iterable[int]
) -> list[ResultadoN]:
    """`simular` para cada N, sobre a mesma sequência."""
    return [simular(contagens, classe, alvo, n)[1] for n in ns]


@dataclass(frozen=True)
class OscilacaoBruta:
    """Quanto a contagem bruta varia ao longo da sequência (sem estabilização)."""

    frames: int
    mudancas: int  # nº de i com contagens[i] != contagens[i-1]
    valores: tuple[int, ...]  # valores distintos, ordenados
    frames_no_alvo: int


def oscilacao_bruta(contagens: Sequence[int], alvo: int | None = None) -> OscilacaoBruta:
    mudancas = sum(1 for a, b in zip(contagens, contagens[1:]) if a != b)
    no_alvo = 0 if alvo is None else sum(1 for c in contagens if c == alvo)
    return OscilacaoBruta(len(contagens), mudancas, tuple(sorted(set(contagens))), no_alvo)


def parse_ns(texto: str) -> list[int]:
    """'1,3,5' -> [1, 3, 5] (ordenado, sem repetição, cada N >= 1)."""
    try:
        ns = sorted({int(p) for p in texto.split(",") if p.strip()})
    except ValueError:
        raise ValueError(f"Lista de N invalida: {texto!r} (ex.: 1,3,5,8,10).") from None
    if not ns or ns[0] < 1:
        raise ValueError(f"Lista de N invalida: {texto!r} (cada N deve ser >= 1).")
    return ns


# ---------------------------------------------------------------------------
# Registros de frames, ordenação, agrupamento em cenas e CSV
# ---------------------------------------------------------------------------


@dataclass
class Registro:
    """Contagem bruta de um frame (e, se houver, o ground truth do label)."""

    indice: int
    contagens: dict[str, int]  # nome da classe -> contagem bruta
    tempo_s: float | None = None
    arquivo: str = ""
    origem: str = ""  # ex.: train/val/test/raw (pasta da imagem)
    gt: dict[str, int] | None = None
    cena: int | None = None


def chave_frame(nome: str) -> tuple[str, str, int] | None:
    """('AAAAMMDD', 'HHMMSS', NNN) do nome `frame_...`; `None` se não casar.

    Sem sufixo `_NNN` -> 0 (é o primeiro frame do segundo, ver
    `dataset_capture._proximo_nome_arquivo`).
    """
    m = _CHAVE_FRAME.search(nome)
    if not m:
        return None
    return m.group(1), m.group(2), int(m.group(3) or 0)


def chave_ordenacao(caminho: Path) -> tuple:
    """Ordena por timestamp+sufixo quando possível; senão, pelo nome.

    Necessário porque, em nomes do Roboflow, 'frame_X_jpg' (1º frame) vem
    DEPOIS de 'frame_X_006_jpg' na ordem alfabética pura.
    """
    chave = chave_frame(caminho.name)
    if chave is None:
        return (1, caminho.name, 0, "")
    return (0, chave[0] + chave[1], chave[2], caminho.name)


def segundos_do_nome(nome: str) -> float | None:
    chave = chave_frame(nome)
    if chave is None:
        return None
    return datetime.strptime(chave[0] + chave[1], "%Y%m%d%H%M%S").timestamp()


def agrupar_cenas(registros: list[Registro], gap_s: float = 1.0) -> list[list[Registro]]:
    """Agrupa registros consecutivos em cenas.

    Nova cena quando: o intervalo de tempo até o anterior passa de `gap_s`, o
    tempo é desconhecido, ou o ground truth muda (a bandeja mudou).
    Registros que já trazem `cena` (ex.: lidos de CSV) são agrupados por ela.
    """
    if registros and all(r.cena is not None for r in registros):
        grupos: dict[int, list[Registro]] = {}
        for r in registros:
            grupos.setdefault(r.cena, []).append(r)  # type: ignore[arg-type]
        return list(grupos.values())

    cenas: list[list[Registro]] = []
    for r in registros:
        if cenas:
            ant = cenas[-1][-1]
            mesmo = (
                r.tempo_s is not None
                and ant.tempo_s is not None
                and 0 <= r.tempo_s - ant.tempo_s <= gap_s
                and r.gt == ant.gt
            )
            if mesmo:
                cenas[-1].append(r)
                continue
        cenas.append([r])
    for i, cena in enumerate(cenas):
        for r in cena:
            r.cena = i
    return cenas


_CLASSES = list(counter.CLASSES.values())  # ["parafuso", "porca"]


def salvar_csv(caminho: Path, registros: Sequence[Registro]) -> None:
    colunas = ["indice", "tempo_s", "arquivo", "origem", "cena", *_CLASSES,
               *(f"gt_{c}" for c in _CLASSES)]
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(colunas)
        for r in registros:
            gt = r.gt or {}
            w.writerow([
                r.indice,
                "" if r.tempo_s is None else f"{r.tempo_s:.3f}",
                r.arquivo, r.origem, "" if r.cena is None else r.cena,
                *(r.contagens.get(c, 0) for c in _CLASSES),
                *(gt.get(c, "") if r.gt is not None else "" for c in _CLASSES),
            ])


def ler_csv(caminho: Path) -> list[Registro]:
    """Lê contagens brutas. Obrigatório: uma coluna por classe (parafuso, porca).

    Opcionais: indice, tempo_s, arquivo, origem, cena, gt_parafuso, gt_porca.
    """
    registros: list[Registro] = []
    with open(caminho, newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        faltando = [c for c in _CLASSES if c not in (leitor.fieldnames or [])]
        if faltando:
            raise ValueError(f"CSV {caminho} sem coluna(s) {faltando}.")
        for i, linha in enumerate(leitor):
            def _int(v: str | None) -> int | None:
                return None if v in (None, "") else int(v)

            gts = {c: _int(linha.get(f"gt_{c}")) for c in _CLASSES}
            registros.append(Registro(
                indice=_int(linha.get("indice")) if linha.get("indice") else i,
                contagens={c: int(linha[c]) for c in _CLASSES},
                tempo_s=float(linha["tempo_s"]) if linha.get("tempo_s") else None,
                arquivo=linha.get("arquivo") or "",
                origem=linha.get("origem") or "",
                gt=None if any(v is None for v in gts.values()) else gts,  # type: ignore[misc]
                cena=_int(linha.get("cena")),
            ))
    return registros


# ---------------------------------------------------------------------------
# Relatório (texto)
# ---------------------------------------------------------------------------


@dataclass
class Agregado:
    """Soma de `ResultadoN` de várias sequências (cena x classe) para um N."""

    n: int
    sequencias: int = 0
    elegiveis: int = 0
    frames: int = 0
    mudancas: int = 0
    entradas_at: int = 0
    saidas_at: int = 0
    entradas_ex: int = 0
    frames_at: int = 0
    com_atingida: int = 0
    latencias: list[int] = field(default_factory=list)

    def somar(self, r: ResultadoN) -> None:
        self.sequencias += 1
        self.elegiveis += r.elegivel
        self.frames += r.frames
        self.mudancas += r.mudancas_estado
        self.entradas_at += r.entradas_atingida
        self.saidas_at += r.saidas_atingida
        self.entradas_ex += r.entradas_excedida
        self.frames_at += r.frames_atingida
        if r.primeira_atingida is not None:
            self.com_atingida += 1
            self.latencias.append(r.primeira_atingida)


def _fmt_lat(frames: float | None, fps: float | None) -> str:
    if frames is None:
        return "-"
    if fps:
        return f"{frames:.1f} fr ({frames / fps:.2f} s)"
    return f"{frames:.1f} fr"


def tabela_agregada(agregados: Sequence[Agregado], fps: float | None) -> str:
    linhas = [
        "| N | seq. | elegiveis (len>=N) | seq. c/ ATINGIDA | mudancas estado | "
        "entradas ATING. | saidas ATING. (piscadas) | entradas EXCED. | "
        "% frames ATING. | latencia mediana 1a ATING. |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for a in agregados:
        lat = statistics.median(a.latencias) if a.latencias else None
        pct = 100 * a.frames_at / a.frames if a.frames else 0.0
        linhas.append(
            f"| {a.n} | {a.sequencias} | {a.elegiveis} | {a.com_atingida} | {a.mudancas} | "
            f"{a.entradas_at} | {a.saidas_at} | {a.entradas_ex} | {pct:.1f} | "
            f"{_fmt_lat(lat, fps)} |"
        )
    return "\n".join(linhas)


def tabela_simples(resultados: Sequence[ResultadoN], fps: float | None) -> str:
    linhas = [
        "| N | frames | mudancas estado | entradas ATING. | saidas ATING. (piscadas) | "
        "entradas EXCED. | % frames ATING. | latencia 1a ATING. | espera minima N/FPS |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in resultados:
        pct = 100 * r.frames_atingida / r.frames if r.frames else 0.0
        espera = f"{r.n / fps:.2f} s" if fps else "-"
        linhas.append(
            f"| {r.n} | {r.frames} | {r.mudancas_estado} | {r.entradas_atingida} | "
            f"{r.saidas_atingida} | {r.entradas_excedida} | {pct:.1f} | "
            f"{_fmt_lat(r.primeira_atingida, fps)} | {espera} |"
        )
    return "\n".join(linhas)


def _resumo_bruto(contagens: Sequence[int], alvo: int) -> str:
    o = oscilacao_bruta(contagens, alvo)
    pct = 100 * o.frames_no_alvo / o.frames if o.frames else 0.0
    return (f"contagem bruta: {o.frames} frames, {o.mudancas} mudancas entre frames "
            f"consecutivos, valores={list(o.valores)}, {pct:.1f}% dos frames == alvo")


def relatorio_sequencia(
    registros: Sequence[Registro], classe: str, alvo: int, ns: Sequence[int],
    fps: float | None,
) -> str:
    contagens = [r.contagens[classe] for r in registros]
    resultados = simular_varios(contagens, classe, alvo, ns)
    fps_txt = f"{fps:.2f}" if fps else "desconhecido"
    return "\n".join([
        f"classe={classe} alvo={alvo} | FPS (medido ou --fps)={fps_txt}",
        _resumo_bruto(contagens, alvo),
        "",
        tabela_simples(resultados, fps),
    ])


def relatorio_cenas(
    registros: list[Registro], ns: Sequence[int], offsets: Sequence[int],
    classes: Sequence[str], gap_s: float, min_frames: int, fps: float | None,
    saida_csv: Path | None = None,
) -> str:
    """Agrupa em cenas, usa o GT (+offset) como alvo e agrega por N."""
    com_gt = [r for r in registros if r.gt is not None]
    sem_gt = len(registros) - len(com_gt)
    cenas = [c for c in agrupar_cenas(com_gt, gap_s) if len(c) >= min_frames]

    saida: list[str] = []
    linhas_csv: list[list] = []
    tot_frames = tot_mud = tot_certos = seq_osc = 0
    det_cenas: list[str] = []
    seqs: list[tuple[int, str, int, list[int], list[Registro]]] = []
    for cena in cenas:
        gt = cena[0].gt or {}
        for classe in classes:
            if gt.get(classe, 0) > 0:
                contagens = [r.contagens[classe] for r in cena]
                seqs.append((cena[0].cena or 0, classe, gt[classe], contagens, cena))
                o = oscilacao_bruta(contagens, gt[classe])
                tot_frames += o.frames
                tot_mud += o.mudancas
                tot_certos += o.frames_no_alvo
                seq_osc += o.mudancas > 0
                origens = ",".join(sorted({r.origem for r in cena}))
                det_cenas.append(
                    f"| {cena[0].cena} | {Path(cena[0].arquivo).name[:31]} | {origens} | "
                    f"{classe} | {gt[classe]} | {o.frames} | {o.frames_no_alvo} | "
                    f"{o.mudancas} | {' '.join(map(str, contagens))} |"
                )

    pct = 100 * tot_certos / tot_frames if tot_frames else 0.0
    saida.append(
        f"Frames lidos: {len(registros)} (sem label/GT, ignorados: {sem_gt}). "
        f"Cenas com >= {min_frames} frames: {len(cenas)}. "
        f"Sequencias (cena x classe presente): {len(seqs)}."
    )
    saida.append(
        f"Oscilacao BRUTA (alvo=GT): {tot_frames} frames, {pct:.1f}% com contagem == GT, "
        f"{tot_mud} mudancas de contagem entre frames consecutivos, "
        f"{seq_osc}/{len(seqs)} sequencias com alguma oscilacao."
    )
    fps_txt = f"{fps:.2f}" if fps else "desconhecido (use --fps para converter frames em s)"
    saida.append(f"FPS usado na conversao frames->s: {fps_txt}")

    for offset in offsets:
        agregados = [Agregado(n) for n in ns]
        for cena_id, classe, gt_classe, contagens, _ in seqs:
            alvo = gt_classe + offset
            if alvo <= 0:
                continue
            for ag, r in zip(agregados, simular_varios(contagens, classe, alvo, ns)):
                ag.somar(r)
                linhas_csv.append([offset, cena_id, classe, gt_classe, alvo, r.n, r.frames,
                                   r.mudancas_estado, r.entradas_atingida,
                                   r.saidas_atingida, r.entradas_excedida,
                                   r.primeira_atingida or "", r.frames_atingida])
        if offset == 0:
            titulo = "alvo = GT (ATINGIDA e o estado CORRETO)"
        else:
            titulo = (f"alvo = GT{offset:+d} (ATINGIDA seria FALSA: bandeja com "
                      f"{'uma peca a menos' if offset > 0 else 'uma peca a mais'} que o alvo)")
        saida += ["", f"### {titulo}", "", tabela_agregada(agregados, fps)]

    saida += ["", "### Contagem bruta por cena (alvo = GT)", "",
              "| cena | 1o arquivo | origem | classe | GT | frames | frames==GT | "
              "mudancas brutas | sequencia bruta |",
              "|---|---|---|---|---|---|---|---|---|", *det_cenas]

    if saida_csv is not None:
        with open(saida_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["offset", "cena", "classe", "gt", "alvo", "n", "frames",
                        "mudancas_estado", "entradas_atingida", "saidas_atingida",
                        "entradas_excedida", "primeira_atingida", "frames_atingida"])
            w.writerows(linhas_csv)
    return "\n".join(saida)


# ---------------------------------------------------------------------------
# Modos com modelo/câmera (imports pesados locais)
# ---------------------------------------------------------------------------


def _contar_por_classe(modelo, frame, conf: float | None) -> dict[str, int]:
    from contador_componentes.app import detector

    deteccoes = detector.run_inference(modelo, frame, conf=conf)
    return {nome: counter.count_objects(counter.filter_by_class(deteccoes, cid))
            for cid, nome in counter.CLASSES.items()}


def expandir_imagens(entradas: Sequence[str]) -> list[Path]:
    """Pastas e/ou globs -> lista de imagens única, ordenada como vídeo."""
    caminhos: dict[str, Path] = {}
    for entrada in entradas:
        p = Path(entrada)
        if p.is_dir():
            achados = [x for x in p.iterdir() if x.suffix.lower() in _EXTENSOES_IMAGEM]
        else:
            achados = [Path(x) for x in glob.glob(entrada)]
        for x in achados:
            caminhos.setdefault(str(x.resolve()), x)
    return sorted(caminhos.values(), key=chave_ordenacao)


def indexar_labels(raiz: Path) -> dict[tuple[str, str, int], Path]:
    """chave do frame -> arquivo de label YOLO (busca recursiva em `raiz`)."""
    indice: dict[tuple[str, str, int], Path] = {}
    for txt in raiz.rglob("*.txt"):
        chave = chave_frame(txt.name)
        if chave is not None:
            indice.setdefault(chave, txt)
    return indice


def contar_label(caminho: Path) -> dict[str, int]:
    gt = {c: 0 for c in _CLASSES}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        partes = linha.split()
        if partes and int(float(partes[0])) in counter.CLASSES:
            gt[counter.CLASSES[int(float(partes[0]))]] += 1
    return gt


def _modo_imagens(args, modelo) -> tuple[list[Registro], float | None]:
    import cv2

    caminhos = expandir_imagens(args.imagens)
    if not caminhos:
        raise SystemExit(f"Nenhuma imagem encontrada em {args.imagens}.")
    labels = indexar_labels(args.labels) if args.alvo_gt else {}
    vistos: set[tuple[str, str, int]] = set()

    # Aquecimento: a 1a inferencia inclui inicializacao do backend e
    # distorceria a vazao medida.
    primeiro = cv2.imread(str(caminhos[0]))
    if primeiro is not None:
        _contar_por_classe(modelo, primeiro, args.conf)

    registros: list[Registro] = []
    t_inf = 0.0
    for caminho in caminhos:
        chave = chave_frame(caminho.name)
        if chave is not None:
            if chave in vistos:  # mesmo frame em duas pastas (ex.: raw e split)
                continue
            vistos.add(chave)
        frame = cv2.imread(str(caminho))
        if frame is None:
            print(f"AVISO: nao foi possivel ler {caminho}", file=sys.stderr)
            continue
        t0 = time.perf_counter()
        contagens = _contar_por_classe(modelo, frame, args.conf)
        t_inf += time.perf_counter() - t0
        gt = None
        if args.alvo_gt and chave in labels:
            gt = contar_label(labels[chave])
        registros.append(Registro(
            indice=len(registros), contagens=contagens,
            tempo_s=segundos_do_nome(caminho.name), arquivo=str(caminho),
            origem=caminho.parent.name, gt=gt,
        ))
        del frame
    fps = len(registros) / t_inf if t_inf > 0 else None
    return registros, fps


def _modo_webcam(args, modelo) -> tuple[list[Registro], float | None]:
    import cv2

    from contador_componentes.app import camera

    cfg = ConfiguracaoContagem(args.classe, args.alvo)
    estabs = {n: EstabilizadorContagem(n) for n in args.ns}
    registros: list[Registro] = []
    cam = None
    inicio = time.perf_counter()
    try:
        cam = camera.open_camera()
        inicio = time.perf_counter()
        while time.perf_counter() - inicio < args.segundos:
            roi = camera.apply_roi(camera.read_frame(cam))
            contagens = _contar_por_classe(modelo, roi, args.conf)
            registros.append(Registro(indice=len(registros), contagens=contagens,
                                      tempo_s=time.perf_counter() - inicio))
            detectado = contagens[counter.CLASSES[counter.resolver_classe(args.classe)]]
            estados = {n: e.atualizar(cfg, detectado) for n, e in estabs.items()}

            exib = roi.copy()
            cv2.putText(exib, f"bruto={detectado} alvo={args.alvo}", (10, 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            for i, (n, est) in enumerate(estados.items()):
                cor = (0, 200, 0) if est is Estado.QUANTIDADE_ATINGIDA else (200, 200, 200)
                cv2.putText(exib, f"N={n:>2}: {est.value}", (10, 58 + 26 * i),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, cor, 2)
            cv2.imshow("Avaliacao de estabilizacao (q/Esc encerra)", exib)
            if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                break
    except Exception as erro:  # noqa: BLE001
        estado = counter.estado_de_erro(erro)
        if estado is None:
            raise
        print(f"estado={estado.value} ({erro}) — avaliacao interrompida", file=sys.stderr)
    finally:
        camera.release_camera(cam)
        cv2.destroyAllWindows()
    duracao = time.perf_counter() - inicio
    fps = len(registros) / duracao if registros and duracao > 0 else None
    return registros, fps


def _fps_de_tempos(registros: Sequence[Registro]) -> float | None:
    """FPS a partir de `tempo_s` — só para CSVs gravados pela webcam.

    Em CSVs vindos de `--imagens`, `tempo_s` é o horário de captura tirado do
    nome do arquivo (resolução de 1 s, com pausas entre cenas): não é FPS.
    """
    if any(r.arquivo for r in registros):
        return None
    tempos = [r.tempo_s for r in registros if r.tempo_s is not None]
    if len(tempos) < 2 or tempos[-1] <= tempos[0]:
        return None
    return (len(tempos) - 1) / (tempos[-1] - tempos[0])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    fonte = parser.add_mutually_exclusive_group(required=True)
    fonte.add_argument("--webcam", action="store_true", help="webcam ao vivo (com ROI)")
    fonte.add_argument("--csv", type=Path, help="CSV de contagens brutas gravado")
    fonte.add_argument("--imagens", nargs="+", help="pasta(s) e/ou glob(s) de frames")
    parser.add_argument("--classe", help="parafuso ou porca")
    parser.add_argument("--alvo", type=int, help="quantidade alvo (inteiro > 0)")
    parser.add_argument("--alvo-gt", action="store_true",
                        help="agrupar em cenas e usar o label (GT) como alvo")
    parser.add_argument("--ns", default=",".join(map(str, NS_PADRAO)), help="ex.: 1,3,5,8,10")
    parser.add_argument("--offsets", default="0,1,-1", help="com --alvo-gt: alvo = GT+offset")
    parser.add_argument("--segundos", type=float, default=60.0, help="duracao no modo webcam")
    parser.add_argument("--salvar", type=Path, help="gravar contagens brutas em CSV")
    parser.add_argument("--saida-csv", type=Path, help="com --alvo-gt: resultados por cena/N")
    parser.add_argument("--labels", type=Path, default=_LABELS_PADRAO,
                        help="pasta de labels YOLO (busca recursiva)")
    parser.add_argument("--gap", type=float, default=1.0,
                        help="intervalo max. (s) entre frames da mesma cena")
    parser.add_argument("--min-frames", type=int, default=3, help="tamanho minimo de cena")
    parser.add_argument("--fps", type=float, help="FPS a usar se nao puder ser medido")
    parser.add_argument("--modelo", type=Path, help="caminho do modelo (.pt/.onnx)")
    parser.add_argument("--conf", type=float, help="limiar de confianca (0 a 1)")
    args = parser.parse_args(argv)

    try:
        args.ns = parse_ns(args.ns)
        offsets = [int(x) for x in args.offsets.split(",") if x.strip()]
    except ValueError as erro:
        parser.error(str(erro))

    usa_gt = args.alvo_gt
    if usa_gt and args.webcam:
        parser.error("--alvo-gt nao se aplica a webcam")
    if not usa_gt:
        if args.classe is None or args.alvo is None:
            parser.error("informe --classe e --alvo (ou --alvo-gt)")
        try:
            ConfiguracaoContagem(args.classe, args.alvo)
        except ValueError as erro:
            parser.error(str(erro))

    fps: float | None = None
    if args.csv is not None:
        registros = ler_csv(args.csv)
        fps = _fps_de_tempos(registros)
        if fps is None and args.fps is None:
            print("AVISO: FPS nao derivavel deste CSV; latencias so em frames "
                  "(informe --fps).", file=sys.stderr)
    else:
        from contador_componentes.app import detector

        try:
            modelo = detector.load_model(args.modelo)
        except detector.ModelError as erro:
            print(f"estado={counter.estado_de_erro(erro).value} ({erro})", file=sys.stderr)
            return 1
        if args.webcam:
            registros, fps = _modo_webcam(args, modelo)
        else:
            registros, fps = _modo_imagens(args, modelo)
    fps = fps or args.fps

    if args.salvar is not None:
        if usa_gt:
            agrupar_cenas([r for r in registros if r.gt is not None], args.gap)
        salvar_csv(args.salvar, registros)
        print(f"Contagens brutas gravadas em {args.salvar}")

    if not registros:
        print("Nenhum frame processado.", file=sys.stderr)
        return 1

    if usa_gt:
        classes = [counter.CLASSES[counter.resolver_classe(args.classe)]] if args.classe \
            else _CLASSES
        print(relatorio_cenas(registros, args.ns, offsets, classes, args.gap,
                              args.min_frames, fps, args.saida_csv))
    else:
        classe = counter.CLASSES[counter.resolver_classe(args.classe)]
        print(relatorio_sequencia(registros, classe, args.alvo, args.ns, fps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
