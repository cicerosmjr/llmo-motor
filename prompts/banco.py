"""Banco de perguntas LLMO — JSON local ou Supabase."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from models.schemas import BancoPerguntasQuery, CategoriaEnum, Pergunta, RodadaEnum
from services.supabase_rest import SupabaseRest, supabase_configurado

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

    def __init__(self, *, supabase: SupabaseRest | None = None) -> None:
        self._perguntas: list[Pergunta] = []
        self._sb: SupabaseRest | None = None
        if supabase is not None or supabase_configurado():
            self._sb = supabase or SupabaseRest()
            logger.info("BancoPerguntas: backend Supabase")
        self.carregar()

    def carregar(self) -> None:
        if self._sb is not None:
            self._carregar_supabase()
            return

        if self.CAMINHO_BANCO.exists():
            raw = json.loads(self.CAMINHO_BANCO.read_text(encoding="utf-8"))
        elif self.CAMINHO_SEED.exists():
            raw = json.loads(self.CAMINHO_SEED.read_text(encoding="utf-8"))
            perguntas = []
            for item in raw:
                dados = dict(item)
                dados.setdefault("id", str(uuid4()))
                perguntas.append(Pergunta.model_validate(dados))
            self._perguntas = perguntas
            try:
                self.salvar()
            except OSError as e:
                # Vercel/read-only: opera só em memória a partir do seed
                logger.warning(
                    "Banco em memória (FS read-only): %s. "
                    "Configure Supabase para persistir edições.",
                    e,
                )
            logger.info(
                "Banco inicializado a partir do seed (%s perguntas)",
                len(self._perguntas),
            )
            return
        else:
            self._perguntas = []
            return

        self._perguntas = [Pergunta.model_validate(item) for item in raw]
        logger.info("Banco carregado: %s perguntas", len(self._perguntas))

    def _carregar_supabase(self) -> None:
        assert self._sb is not None
        rows = self._sb.select(
            "llmo_perguntas",
            params={"select": "id,dados", "order": "updated_at.asc"},
        )
        if not rows and self.CAMINHO_SEED.exists():
            raw = json.loads(self.CAMINHO_SEED.read_text(encoding="utf-8"))
            perguntas: list[Pergunta] = []
            for item in raw:
                dados = dict(item)
                dados.setdefault("id", str(uuid4()))
                perguntas.append(Pergunta.model_validate(dados))
            self._perguntas = perguntas
            self.salvar()
            logger.info(
                "Banco Supabase inicializado do seed (%s perguntas)",
                len(self._perguntas),
            )
            return

        self._perguntas = [
            Pergunta.model_validate(row["dados"]) for row in rows if row.get("dados")
        ]
        logger.info("Banco Supabase carregado: %s perguntas", len(self._perguntas))

    def salvar(self) -> None:
        if self._sb is not None:
            agora = datetime.utcnow().isoformat()
            rows = [
                {
                    "id": str(p.id),
                    "dados": p.model_dump(mode="json"),
                    "updated_at": agora,
                }
                for p in self._perguntas
            ]
            # Upsert em lotes para não estourar payload
            lote = 100
            for i in range(0, len(rows), lote):
                self._sb.upsert(
                    "llmo_perguntas",
                    rows[i : i + lote],
                    on_conflict="id",
                )
            return

        self.CAMINHO_BANCO.parent.mkdir(parents=True, exist_ok=True)
        payload = [p.model_dump(mode="json") for p in self._perguntas]
        self.CAMINHO_BANCO.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _persistir_uma(self, pergunta: Pergunta) -> None:
        if self._sb is None:
            self.salvar()
            return
        self._sb.upsert(
            "llmo_perguntas",
            {
                "id": str(pergunta.id),
                "dados": pergunta.model_dump(mode="json"),
                "updated_at": datetime.utcnow().isoformat(),
            },
            on_conflict="id",
        )

    def _remover_uma(self, id: UUID) -> None:
        if self._sb is None:
            self.salvar()
            return
        self._sb.delete("llmo_perguntas", params={"id": f"eq.{id}"})

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
        self._persistir_uma(pergunta)
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
        if "rodada" in dados and dados["rodada"] is None:
            update["rodada"] = None

        atualizada = pergunta.model_copy(update=update)
        self._perguntas = [atualizada if p.id == id else p for p in self._perguntas]
        self._persistir_uma(atualizada)
        return atualizada

    def desativar(self, id: UUID) -> None:
        self.atualizar(id, {"ativa": False})

    def deletar(self, id: UUID) -> None:
        antes = len(self._perguntas)
        self._perguntas = [p for p in self._perguntas if p.id != id]
        if len(self._perguntas) == antes:
            raise KeyError(f"Pergunta {id} não encontrada")
        self._remover_uma(id)

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

        if not all(por_r[r] for r in RODADAS_ORDEM):
            return []

        selecionadas: list[Pergunta] = []
        usados: set[UUID] = set()

        for r in RODADAS_ORDEM:
            p = por_r[r][0]
            selecionadas.append(p)
            usados.add(p.id)

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
