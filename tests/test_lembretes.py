# -*- coding: utf-8 -*-
import argparse
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

from lembretes import (
    ACOES_TOAST,
    DIAS_SEMANA,
    Agendador,
    Historico,
    Lembrete,
    aplicar_cli,
    aplicar_modo_teste,
    caminho_historico,
    carregar_config,
    config_padrao,
    criar_historico,
    criar_lembretes,
    criar_parser,
    em_horario_silencio,
    escapar_xml,
    formato_intervalo,
    iniciar_agenda,
    mesclar_config,
    montar_script_toast,
    mostrar_estatisticas,
    normalizar_acao,
    processar_tick,
    validar_config,
)


def criar_lembrete(**alteracoes) -> Lembrete:
    dados = {
        "nome": "Teste",
        "titulo": "Título",
        "mensagem": "Mensagem",
        "notas": [(1000, 10)],
        "intervalo": 60,
        "atraso_inicial": 10,
        "proximo": 10,
        "pendente": False,
    }
    dados.update(alteracoes)
    return Lembrete(**dados)


class TestProcessarTick(unittest.TestCase):
    def test_entrega_quando_chega_o_horario(self):
        lembrete = criar_lembrete()
        entregas = []

        adiados = processar_tick(
            [lembrete],
            10,
            False,
            lambda item, atrasado: entregas.append((item, atrasado)),
        )

        self.assertEqual(adiados, [])
        self.assertEqual(entregas, [(lembrete, False)])
        self.assertEqual(lembrete.proximo, 70)
        self.assertFalse(lembrete.pendente)

    def test_nao_entrega_antes_do_horario(self):
        lembrete = criar_lembrete()
        entregas = []

        adiados = processar_tick(
            [lembrete],
            9,
            False,
            lambda item, atrasado: entregas.append((item, atrasado)),
        )

        self.assertEqual(adiados, [])
        self.assertEqual(entregas, [])
        self.assertEqual(lembrete.proximo, 10)

    def test_adia_em_tela_cheia_sem_som_nem_notificacao(self):
        lembrete = criar_lembrete()
        entregas = []

        adiados = processar_tick(
            [lembrete],
            10,
            True,
            lambda item, atrasado: entregas.append((item, atrasado)),
        )

        self.assertEqual(adiados, [lembrete])
        self.assertEqual(entregas, [])
        self.assertTrue(lembrete.pendente)
        self.assertEqual(lembrete.proximo, 70)

    def test_nao_registra_o_mesmo_adiamento_duas_vezes(self):
        lembrete = criar_lembrete()
        entregas = []

        def entregar(item, atrasado):
            entregas.append((item, atrasado))

        processar_tick([lembrete], 10, True, entregar)
        adiados = processar_tick([lembrete], 20, True, entregar)

        self.assertEqual(entregas, [])
        self.assertEqual(adiados, [])
        self.assertTrue(lembrete.pendente)
        self.assertEqual(lembrete.proximo, 70)

    def test_entrega_adiada_assim_que_sai_da_tela_cheia(self):
        lembrete = criar_lembrete(proximo=70, pendente=True)
        entregas = []

        processar_tick(
            [lembrete],
            15,
            False,
            lambda item, atrasado: entregas.append((item, atrasado)),
        )

        self.assertEqual(entregas, [(lembrete, True)])
        self.assertFalse(lembrete.pendente)
        self.assertEqual(lembrete.proximo, 70)

    def test_evita_rajada_quando_o_proximo_horario_ja_passou(self):
        lembrete = criar_lembrete(proximo=30, pendente=True)
        entregas = []

        processar_tick(
            [lembrete],
            100,
            False,
            lambda item, atrasado: entregas.append((item, atrasado)),
        )
        processar_tick(
            [lembrete],
            100,
            False,
            lambda item, atrasado: entregas.append((item, atrasado)),
        )

        self.assertEqual(entregas, [(lembrete, True)])
        self.assertEqual(lembrete.proximo, 160)

    def test_ciclo_completo_adia_e_retoma_a_agenda(self):
        lembrete = criar_lembrete(
            intervalo=60, atraso_inicial=10, proximo=10
        )
        entregas = []

        for segundo in range(130):
            processar_tick(
                [lembrete],
                segundo,
                8 <= segundo < 50,
                lambda item, atrasado: entregas.append((item, atrasado)),
            )

        self.assertEqual(entregas, [(lembrete, True), (lembrete, False)])
        self.assertEqual(lembrete.proximo, 130)

    def test_iniciar_agenda_define_atraso_e_limpa_pendencia(self):
        lembrete = criar_lembrete(pendente=True)

        iniciar_agenda([lembrete], agora=100)

        self.assertEqual(lembrete.proximo, 110)
        self.assertFalse(lembrete.pendente)


class TestAgendador(unittest.TestCase):
    def criar_agendador(self, lembrete=None):
        if lembrete is None:
            lembrete = criar_lembrete()
        estado = {"agora": 0.0}
        entregas = []

        agendador = Agendador(
            [lembrete],
            relogio=lambda: estado["agora"],
            obter_tela_cheia=lambda: False,
            entregar=lambda item, atrasado: entregas.append(
                (item, atrasado)
            ),
            registrar=lambda mensagem: None,
        )

        return agendador, lembrete, estado, entregas

    def test_pausa_adia_a_agenda_sem_rajada(self):
        agendador, lembrete, estado, entregas = self.criar_agendador()

        estado["agora"] = 5
        agendador.pausar()
        estado["agora"] = 25
        agendador.tick()

        self.assertEqual(entregas, [])
        self.assertEqual(lembrete.proximo, 10)

        agendador.retomar()
        self.assertEqual(lembrete.proximo, 30)

        estado["agora"] = 29
        agendador.tick()
        self.assertEqual(entregas, [])

        estado["agora"] = 30
        agendador.tick()
        self.assertEqual(entregas, [(lembrete, False)])

    def test_soneca_suprime_avisos_e_shift_a_agenda(self):
        agendador, lembrete, estado, entregas = self.criar_agendador()

        estado["agora"] = 5
        agendador.sonecar(30)
        self.assertTrue(agendador.sonecando)

        estado["agora"] = 34
        agendador.tick()
        self.assertEqual(entregas, [])

        estado["agora"] = 35
        agendador.tick()
        self.assertFalse(agendador.sonecando)
        self.assertEqual(entregas, [])
        self.assertEqual(lembrete.proximo, 40)

        estado["agora"] = 40
        agendador.tick()
        self.assertEqual(entregas, [(lembrete, False)])

    def test_cancelar_soneca_volta_a_agenda(self):
        agendador, lembrete, estado, entregas = self.criar_agendador()

        estado["agora"] = 5
        agendador.sonecar(30)
        estado["agora"] = 10
        agendador.cancelar_soneca()

        self.assertEqual(lembrete.proximo, 15)
        self.assertFalse(agendador.sonecando)

        estado["agora"] = 15
        agendador.tick()
        self.assertEqual(entregas, [(lembrete, False)])

    def test_texto_status(self):
        agendador, _, _, _ = self.criar_agendador()

        self.assertEqual(
            agendador.texto_status(), "Lembretes de Saúde — ativo"
        )

        agendador.pausar()
        self.assertEqual(
            agendador.texto_status(), "Lembretes de Saúde — pausado"
        )

        agendador.sonecar(60)
        self.assertIn("soneca até", agendador.texto_status())


class TestHorarioSilencio(unittest.TestCase):
    def criar_horario(self, **alteracoes):
        horario = {
            "ativo": True,
            "inicio": "22:00",
            "fim": "07:00",
            "dias_semana": list(DIAS_SEMANA),
        }
        horario.update(alteracoes)
        return horario

    def test_desativado_nunca_esta_em_silencio(self):
        horario = self.criar_horario(ativo=False)

        self.assertFalse(
            em_horario_silencio(
                horario, datetime(2026, 10, 26, 23, 0)
            )
        )

    def test_janela_durante_o_dia(self):
        horario = self.criar_horario(inicio="12:00", fim="14:00")

        self.assertFalse(
            em_horario_silencio(
                horario, datetime(2026, 10, 24, 11, 59)
            )
        )
        self.assertTrue(
            em_horario_silencio(
                horario, datetime(2026, 10, 24, 13, 0)
            )
        )
        self.assertFalse(
            em_horario_silencio(
                horario, datetime(2026, 10, 24, 14, 0)
            )
        )

    def test_janela_noturna_avanca_para_a_madrugada(self):
        horario = self.criar_horario()

        self.assertFalse(
            em_horario_silencio(
                horario, datetime(2026, 10, 26, 21, 59)
            )
        )
        self.assertTrue(
            em_horario_silencio(
                horario, datetime(2026, 10, 26, 22, 0)
            )
        )
        self.assertTrue(
            em_horario_silencio(
                horario, datetime(2026, 10, 27, 3, 0)
            )
        )
        self.assertFalse(
            em_horario_silencio(
                horario, datetime(2026, 10, 27, 7, 0)
            )
        )

    def test_madrugada_pertence_ao_dia_em_que_comecou(self):
        horario = self.criar_horario(dias_semana=["seg"])

        self.assertTrue(
            em_horario_silencio(
                horario, datetime(2026, 10, 26, 23, 0)
            )
        )
        self.assertTrue(
            em_horario_silencio(
                horario, datetime(2026, 10, 27, 3, 0)
            )
        )
        self.assertFalse(
            em_horario_silencio(
                horario, datetime(2026, 10, 28, 3, 0)
            )
        )

    def test_silencio_desloca_a_agenda(self):
        lembrete = criar_lembrete()
        estado = {"agora": 0.0, "silencio": False}
        entregas = []

        agendador = Agendador(
            [lembrete],
            relogio=lambda: estado["agora"],
            obter_tela_cheia=lambda: False,
            entregar=lambda item, atrasado: entregas.append(
                (item, atrasado)
            ),
            registrar=lambda mensagem: None,
            em_silencio=lambda: estado["silencio"],
        )

        estado["agora"] = 5
        estado["silencio"] = True
        agendador.tick()

        self.assertEqual(entregas, [])
        self.assertEqual(lembrete.proximo, 10)
        self.assertEqual(
            agendador.texto_status(), "Lembretes de Saúde — silêncio"
        )

        estado["agora"] = 25
        estado["silencio"] = False
        agendador.tick()

        self.assertEqual(entregas, [])
        self.assertEqual(lembrete.proximo, 30)

        estado["agora"] = 30
        agendador.tick()

        self.assertEqual(entregas, [(lembrete, False)])

    def test_pausa_durante_silencio_nao_desloca_duas_vezes(self):
        lembrete = criar_lembrete()
        estado = {"agora": 0.0, "silencio": False}
        entregas = []

        agendador = Agendador(
            [lembrete],
            relogio=lambda: estado["agora"],
            obter_tela_cheia=lambda: False,
            entregar=lambda item, atrasado: entregas.append(
                (item, atrasado)
            ),
            registrar=lambda mensagem: None,
            em_silencio=lambda: estado["silencio"],
        )

        estado["agora"] = 5
        estado["silencio"] = True
        agendador.tick()
        agendador.pausar()

        estado["agora"] = 10
        agendador.retomar()
        self.assertEqual(lembrete.proximo, 10)

        estado["agora"] = 15
        estado["silencio"] = False
        agendador.tick()
        self.assertEqual(lembrete.proximo, 20)

        estado["agora"] = 20
        agendador.tick()
        self.assertEqual(entregas, [(lembrete, False)])


class TestHistorico(unittest.TestCase):
    def test_grava_eventos_em_json_lines(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "dados" / "historico.jsonl"
            historico = Historico(caminho)

            self.assertTrue(
                historico.registrar(
                    "lembrete_entregue",
                    nome="Olhos",
                    atrasado=False,
                )
            )

            registros = [
                json.loads(linha)
                for linha in caminho.read_text(
                    encoding="utf-8"
                ).splitlines()
            ]

        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0]["evento"], "lembrete_entregue")
        self.assertEqual(registros[0]["nome"], "Olhos")
        self.assertFalse(registros[0]["atrasado"])
        self.assertIn("quando", registros[0])

    def test_estatisticas_resumem_os_eventos(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "historico.jsonl"
            historico = Historico(caminho)

            historico.registrar(
                "lembrete_entregue", nome="Olhos", atrasado=False
            )
            historico.registrar(
                "lembrete_entregue", nome="Água", atrasado=True
            )
            historico.registrar("pausa_iniciada")
            historico.registrar(
                "pausa_encerrada", duracao_segundos=120
            )
            historico.registrar(
                "soneca_iniciada", duracao_segundos=900
            )
            historico.registrar(
                "soneca_encerrada", duracao_segundos=900
            )
            historico.registrar("silencio_iniciado")
            historico.registrar(
                "silencio_encerrado", duracao_segundos=3600
            )
            historico.registrar("lembrete_confirmado", nome="Água")

            saida = io.StringIO()
            with redirect_stdout(saida):
                resultado = mostrar_estatisticas(caminho)

        texto = saida.getvalue()
        self.assertEqual(resultado, 0)
        self.assertIn("Lembretes entregues: 2 (1 adiados)", texto)
        self.assertIn('Confirmados com "Feito": 1', texto)
        self.assertIn("Pausas: 1 (2 min)", texto)
        self.assertIn("Sonecas: 1 (15 min)", texto)
        self.assertIn("Silêncio: 1 (1h)", texto)
        self.assertIn(" - Olhos: 1", texto)
        self.assertIn(" - Água: 1", texto)

    def test_estatisticas_sem_arquivo(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "nada.jsonl"
            saida = io.StringIO()

            with redirect_stdout(saida):
                resultado = mostrar_estatisticas(caminho)

        self.assertEqual(resultado, 0)
        self.assertIn("Nenhum histórico encontrado", saida.getvalue())

    def test_criar_historico_respeita_a_configuracao(self):
        config = config_padrao()
        self.assertIsNotNone(criar_historico(config))

        config["historico"]["ativo"] = False
        self.assertIsNone(criar_historico(config))

    def test_caminho_absoluto_do_historico_e_preservado(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "eventos.jsonl"
            config = config_padrao()
            config["historico"]["arquivo"] = str(caminho)

            self.assertEqual(caminho_historico(config), caminho)

    def test_agendador_registra_eventos_de_uso(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "historico.jsonl"
            lembrete = criar_lembrete()
            estado = {"agora": 0.0}
            entregas = []

            agendador = Agendador(
                [lembrete],
                relogio=lambda: estado["agora"],
                obter_tela_cheia=lambda: False,
                entregar=lambda item, atrasado: entregas.append(
                    (item, atrasado)
                ),
                registrar=lambda mensagem: None,
                historico=Historico(caminho),
            )

            estado["agora"] = 5
            agendador.pausar()
            estado["agora"] = 15
            agendador.retomar()
            estado["agora"] = 20
            agendador.sonecar(60)
            estado["agora"] = 30
            agendador.cancelar_soneca()
            estado["agora"] = 30
            agendador.tick()
            agendador.confirmar_lembrete()

            registros = [
                json.loads(linha)
                for linha in caminho.read_text(
                    encoding="utf-8"
                ).splitlines()
            ]

        eventos = [item["evento"] for item in registros]
        self.assertEqual(
            eventos,
            [
                "pausa_iniciada",
                "pausa_encerrada",
                "soneca_iniciada",
                "soneca_cancelada",
                "lembrete_entregue",
                "lembrete_confirmado",
            ],
        )
        self.assertEqual(registros[1]["duracao_segundos"], 10)
        self.assertEqual(registros[3]["duracao_segundos"], 10)
        self.assertTrue(registros[4]["atrasado"] is False)
        self.assertEqual(registros[5]["nome"], "Teste")
        self.assertEqual(entregas, [(lembrete, False)])


class TestConfiguracao(unittest.TestCase):
    def test_config_padrao_e_valida(self):
        config = config_padrao()
        validar_config(config)

        lembretes = criar_lembretes(config)
        self.assertEqual(
            [lembrete.nome for lembrete in lembretes],
            ["Olhos", "Água", "Alongamento"],
        )
        self.assertEqual(
            [lembrete.intervalo for lembrete in lembretes],
            [1200, 3600, 5400],
        )

    def test_modo_teste_encurta_intervalos(self):
        config = config_padrao()
        aplicar_modo_teste(config)

        lembretes = criar_lembretes(config)
        self.assertEqual(
            [lembrete.intervalo for lembrete in lembretes],
            [5, 12, 18],
        )
        self.assertEqual(
            [lembrete.atraso_inicial for lembrete in lembretes],
            [5, 7, 11],
        )

    def test_mescla_recursiva_preserva_o_restante(self):
        config = config_padrao()
        alterada = mesclar_config(
            config,
            {"lembretes": {"olhos": {"intervalo_segundos": 60}}},
        )

        self.assertEqual(
            alterada["lembretes"]["olhos"]["intervalo_segundos"], 60
        )
        self.assertEqual(
            alterada["lembretes"]["agua"]["intervalo_segundos"], 3600
        )

    def test_rejeita_chave_desconhecida(self):
        with self.assertRaises(ValueError):
            mesclar_config(
                config_padrao(), {"lembretes": {"olhos": {"foo": 1}}}
            )

    def test_rejeita_intervalo_invalido(self):
        config = config_padrao()
        config["lembretes"]["olhos"]["intervalo_segundos"] = 0

        with self.assertRaises(ValueError):
            validar_config(config)

    def test_rejeita_frequencia_invalida(self):
        config = config_padrao()
        config["lembretes"]["olhos"]["notas"] = [[10, 200]]

        with self.assertRaises(ValueError):
            validar_config(config)

    def test_rejeita_horario_de_silencio_invalido(self):
        config = config_padrao()
        config["horario_silencio"]["inicio"] = "25:00"

        with self.assertRaises(ValueError):
            validar_config(config)

    def test_rejeita_inicio_e_fim_iguais(self):
        config = config_padrao()
        config["horario_silencio"]["inicio"] = "22:00"
        config["horario_silencio"]["fim"] = "22:00"

        with self.assertRaises(ValueError):
            validar_config(config)

    def test_rejeita_dia_da_semana_desconhecido(self):
        config = config_padrao()
        config["horario_silencio"]["dias_semana"] = ["seg", "feriado"]

        with self.assertRaises(ValueError):
            validar_config(config)

    def test_rejeita_dias_da_semana_repetidos(self):
        config = config_padrao()
        config["horario_silencio"]["dias_semana"] = ["seg", "seg"]

        with self.assertRaises(ValueError):
            validar_config(config)

    def test_rejeita_lista_de_dias_vazia(self):
        config = config_padrao()
        config["horario_silencio"]["dias_semana"] = []

        with self.assertRaises(ValueError):
            validar_config(config)

    def test_rejeita_arquivo_de_historico_vazio(self):
        config = config_padrao()
        config["historico"]["arquivo"] = " "

        with self.assertRaises(ValueError):
            validar_config(config)

    def test_lembrete_inativo_nao_e_criado(self):
        config = config_padrao()
        config["lembretes"]["agua"]["ativo"] = False

        lembretes = criar_lembretes(config)

        self.assertNotIn("Água", [item.nome for item in lembretes])

    def test_cli_sobrepoe_configuracao(self):
        config = config_padrao()
        args = argparse.Namespace(
            sem_som=True,
            sem_bandeja=True,
            olhos=30,
            agua=None,
            alongamento=None,
        )

        aplicar_cli(config, args)

        self.assertFalse(config["som_ativo"])
        self.assertFalse(config["usar_bandeja"])
        self.assertEqual(
            config["lembretes"]["olhos"]["intervalo_segundos"], 1800
        )
        self.assertEqual(
            config["lembretes"]["agua"]["intervalo_segundos"], 3600
        )

    def test_carrega_arquivo_json(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
        ) as arquivo:
            json.dump(
                {"lembretes": {"agua": {"intervalo_segundos": 120}}},
                arquivo,
            )
            caminho = arquivo.name

        try:
            config = carregar_config(caminho)
        finally:
            os.unlink(caminho)

        self.assertEqual(
            config["lembretes"]["agua"]["intervalo_segundos"], 120
        )
        self.assertEqual(
            config["lembretes"]["olhos"]["intervalo_segundos"], 1200
        )

    def test_arquivo_inexistente_gera_erro(self):
        with self.assertRaises(FileNotFoundError):
            carregar_config("arquivo-que-nao-existe.json")

    def test_parser_aceita_intervalos(self):
        args = criar_parser().parse_args(
            ["--sem-som", "--sem-bandeja", "--olhos", "30"]
        )

        self.assertTrue(args.sem_som)
        self.assertTrue(args.sem_bandeja)
        self.assertEqual(args.olhos, 30)

    def test_parser_aceita_estatisticas_e_acao(self):
        args = criar_parser().parse_args(
            ["--estatisticas", "--acao", "lembretes-saude:feito"]
        )

        self.assertTrue(args.estatisticas)
        self.assertEqual(args.acao, "lembretes-saude:feito")


class TestAcoesToast(unittest.TestCase):
    def test_normaliza_uri_de_acao(self):
        self.assertEqual(
            normalizar_acao("lembretes-saude:feito"), "feito"
        )
        self.assertEqual(
            normalizar_acao("lembretes-saude://soneca15"), "soneca15"
        )
        self.assertEqual(
            normalizar_acao('"LEMBRETES-SAUDE:Feito"'), "feito"
        )
        self.assertEqual(normalizar_acao("nada"), "nada")
        self.assertEqual(normalizar_acao(None), "")

    def test_script_inclui_botoes_de_protocolo(self):
        script = montar_script_toast(
            "Título", "Mensagem", ACOES_TOAST
        )

        self.assertIn("<actions>", script)
        self.assertIn('activationType="protocol"', script)
        self.assertIn(
            'arguments="lembretes-saude:feito"', script
        )
        self.assertIn(
            'arguments="lembretes-saude:soneca15"', script
        )
        self.assertIn("Feito ✅", script)
        self.assertIn("Soneca 15 min", script)

    def test_script_sem_acoes_nao_tem_botoes(self):
        script = montar_script_toast("Título", "Mensagem")

        self.assertNotIn("<actions>", script)


class TestFormatacao(unittest.TestCase):
    def test_formato_intervalo(self):
        self.assertEqual(formato_intervalo(45), "45 s")
        self.assertEqual(formato_intervalo(60), "1 min")
        self.assertEqual(formato_intervalo(3600), "1h")
        self.assertEqual(formato_intervalo(5400), "1h30min")
        self.assertEqual(formato_intervalo(7200), "2h")


class TestNotificacao(unittest.TestCase):
    def test_escapa_caracteres_xml(self):
        self.assertEqual(
            escapar_xml("a&b<c>d\"e'f"),
            "a&amp;b&lt;c&gt;d&quot;e&apos;f",
        )

    def test_script_nao_quebra_o_xml_e_nao_duplica_som(self):
        script = montar_script_toast("<olhos> & água", '"aspas"')

        self.assertIn("&lt;olhos&gt; &amp; água", script)
        self.assertIn("&quot;aspas&quot;", script)
        self.assertIn('<audio silent="true"/>', script)


if __name__ == "__main__":
    unittest.main()
