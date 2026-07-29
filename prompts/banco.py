"""Banco de perguntas LLMO — persistência em JSON."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from uuid import UUID, uuid4

from models.schemas import BancoPerguntasQuery, CategoriaEnum, Pergunta, RodadaEnum

logger = logging.getLogger(__name__)

CATEGORIAS_DISTRIBUICAO = [
    ("reconhecimento", 2),
    ("recomendacao", 2),
    ("reputacao", 2),
    ("servicos", 2),
    ("localizacao", 1),
    ("generica", 1),
]

RODADAS_ORDEM = [RodadaEnum.r1, RodadaEnum.r2, RodadaEnum.r3, RodadaEnum.r4, RodadaEnum.r5]


class BancoPerguntas:
    CAMINHO_SEED = Path("data/perguntas_seed.json")
    CAMINHO_BANCO = Path("data/perguntas.json")

    def __init__(self) -> None:
        self._perguntas: list[Pergunta] = []
        self.carregar()

    def carregar(self) -> None:
        if self.CAMINHO_BANCO.exists():
            raw = json.loads(self.CAMINHO_BANCO.read_text(encoding="utf-8"))
        elif self.CAMINHO_SEED.exists():
            raw = json.loads(self.CAMINHO_SEED.read_text(encoding="utf-8"))
            self.CAMINHO_BANCO.parent.mkdir(parents=True, exist_ok=True)
            # Atribui UUIDs ao copiar do seed
            perguntas = []
            for item in raw:
                dados = dict(item)
                dados.setdefault("id", str(uuid4()))
                perguntas.append(Pergunta.model_validate(dados))
            self._perguntas = perguntas
            self.salvar()
            logger.info("Banco inicializado a partir do seed (%s perguntas)", len(self._perguntas))
            return
        else:
            self._perguntas = []
            return

        self._perguntas = [Pergunta.model_validate(item) for item in raw]
        logger.info("Banco carregado: %s perguntas", len(self._perguntas))

    def salvar(self) -> None:
        self.CAMINHO_BANCO.parent.mkdir(parents=True, exist_ok=True)
        payload = [p.model_dump(mode="json") for p in self._perguntas]
        self.CAMINHO_BANCO.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def listar(self, query: BancoPerguntasQuery | None = None) -> list[Pergunta]:
        query = query or BancoPerguntasQuery()
        resultado = self._perguntas

        if query.apenas_ativas:
            resultado = [p for p in resultado if p.ativa]
        if query.segmento:
            resultado = [p for p in resultado if p.segmento.lower() == query.segmento.lower()]
        if query.especialidade:
            esp = query.especialidade.lower()
            resultado = [
                p for p in resultado
                if p.especialidade and p.especialidade.lower() == esp
            ]
        if query.categoria:
            resultado = [p for p in resultado if p.categoria == query.categoria]
        if query.busca_texto:
            termo = query.busca_texto.lower()
            resultado = [p for p in resultado if termo in p.texto.lower()]

        return resultado

    def buscar_por_id(self, id: UUID) -> Pergunta | None:
        for p in self._perguntas:
            if p.id == id:
                return p
        return None

    def criar(
        self,
        texto: str,
        segmento: str,
        categoria: str,
        especialidade: str | None = None,
        rodada: str | RodadaEnum | None = None,
    ) -> Pergunta:
        rodada_enum: RodadaEnum | None = None
        if rodada is not None:
            rodada_enum = rodada if isinstance(rodada, RodadaEnum) else RodadaEnum(rodada)
        pergunta = Pergunta(
            texto=texto,
            segmento=segmento,
            especialidade=especialidade,
            categoria=CategoriaEnum(categoria),
            rodada=rodada_enum,
        )
        self._perguntas.append(pergunta)
        self.salvar()
        return pergunta

    def atualizar(self, id: UUID, dados: dict) -> Pergunta:
        pergunta = self.buscar_por_id(id)
        if pergunta is None:
            raise KeyError(f"Pergunta {id} não encontrada")

        permitidos = {"texto", "segmento", "categoria", "especialidade", "ativa", "rodada"}
        update = {k: v for k, v in dados.items() if k in permitidos and v is not None}
        if "categoria" in update and isinstance(update["categoria"], str):
            update["categoria"] = CategoriaEnum(update["categoria"])
        if "rodada" in update and isinstance(update["rodada"], str):
            update["rodada"] = RodadaEnum(update["rodada"])
        # Permite limpar rodada enviando null via exclude_unset=False path
        if "rodada" in dados and dados["rodada"] is None:
            update["rodada"] = None

        atualizada = pergunta.model_copy(update=update)
        self._perguntas = [atualizada if p.id == id else p for p in self._perguntas]
        self.salvar()
        return atualizada

    def desativar(self, id: UUID) -> None:
        self.atualizar(id, {"ativa": False})

    def deletar(self, id: UUID) -> None:
        antes = len(self._perguntas)
        self._perguntas = [p for p in self._perguntas if p.id != id]
        if len(self._perguntas) == antes:
            raise KeyError(f"Pergunta {id} não encontrada")
        self.salvar()

    def sugerir_para_diagnostico(
        self,
        segmento: str,
        especialidade: str,
        incluir_genericas: bool = True,
        limite: int = 10,
    ) -> list[Pergunta]:
        ativas = [p for p in self._perguntas if p.ativa]
        da_especialidade = [
            p for p in ativas
            if p.segmento.lower() == segmento.lower()
            and p.especialidade
            and p.especialidade.lower() == especialidade.lower()
        ]
        do_segmento = [
            p for p in ativas
            if p.segmento.lower() == segmento.lower()
            and p not in da_especialidade
        ]
        genericas = [
            p for p in ativas
            if p.segmento.lower() == "geral" or p.categoria == CategoriaEnum.generica
        ] if incluir_genericas else []

        pool = da_especialidade + do_segmento + genericas

        # Prioriza conjunto completo por rodada (Bloco 1) quando disponível
        por_rodada = self._sugerir_por_rodada(pool, limite)
        if por_rodada:
            return por_rodada

        selecionadas: list[Pergunta] = []
        usados: set[UUID] = set()

        for cat, qtd in CATEGORIAS_DISTRIBUICAO:
            da_cat = [
                p for p in pool
                if p.categoria.value == cat and p.id not in usados
            ]
            for p in da_cat[:qtd]:
                selecionadas.append(p)
                usados.add(p.id)
                if len(selecionadas) >= limite:
                    return selecionadas[:limite]

        for p in pool:
            if p.id not in usados:
                selecionadas.append(p)
                usados.add(p.id)
            if len(selecionadas) >= limite:
                break

        return selecionadas[:limite]

    def _sugerir_por_rodada(self, pool: list[Pergunta], limite: int) -> list[Pergunta]:
        """Monta sugestão cobrindo R1–R5 (uma pergunta por rodada, depois extras)."""
        com_rodada = [p for p in pool if p.rodada is not None]
        if not com_rodada:
            return []

        por_r: dict[RodadaEnum, list[Pergunta]] = {r: [] for r in RODADAS_ORDEM}
        for p in com_rodada:
            assert p.rodada is not None
            por_r[p.rodada].append(p)

        # Exige pelo menos uma pergunta em cada rodada para ativar o modo Bloco 1
        if not all(por_r[r] for r in RODADAS_ORDEM):
            return []

        selecionadas: list[Pergunta] = []
        usados: set[UUID] = set()

        # 1ª passagem: 1 de cada rodada
        for r in RODADAS_ORDEM:
            p = por_r[r][0]
            selecionadas.append(p)
            usados.add(p.id)

        # 2ª passagem: preenche restantes por ordem de rodada
        while len(selecionadas) < limite:
            adicionou = False
            for r in RODADAS_ORDEM:
                for p in por_r[r]:
                    if p.id not in usados:
                        selecionadas.append(p)
                        usados.add(p.id)
                        adicionou = True
                        break
                if len(selecionadas) >= limite:
                    break
            if not adicionou:
                break

        return selecionadas[:limite]

    def listar_segmentos_especialidades(self) -> dict[str, list[str]]:
        mapa: dict[str, set[str]] = {}
        for p in self._perguntas:
            if not p.ativa:
                continue
            mapa.setdefault(p.segmento, set())
            if p.especialidade:
                mapa[p.segmento].add(p.especialidade)
        return {k: sorted(v) for k, v in sorted(mapa.items())}
