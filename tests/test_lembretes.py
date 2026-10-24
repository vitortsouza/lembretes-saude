# -*- coding: utf-8 -*-
import unittest

from lembretes import (
    Lembrete,
    escapar_xml,
    formato_intervalo,
    iniciar_agenda,
    montar_script_toast,
    processar_tick,
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
            [lembrete], 10, False, lambda item, atrasado: entregas.append(
                (item, atrasado)
            )
        )

        self.assertEqual(adiados, [])
        self.assertEqual(entregas, [(lembrete, False)])
        self.assertEqual(lembrete.proximo, 70)
        self.assertFalse(lembrete.pendente)

    def test_nao_entrega_antes_do_horario(self):
        lembrete = criar_lembrete()
        entregas = []

        adiados = processar_tick(
            [lembrete], 9, False, lambda item, atrasado: entregas.append(
                (item, atrasado)
            )
        )

        self.assertEqual(adiados, [])
        self.assertEqual(entregas, [])
        self.assertEqual(lembrete.proximo, 10)

    def test_adia_em_tela_cheia_sem_som_nem_notificacao(self):
        lembrete = criar_lembrete()
        entregas = []

        adiados = processar_tick(
            [lembrete], 10, True, lambda item, atrasado: entregas.append(
                (item, atrasado)
            )
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
            [lembrete], 15, False, lambda item, atrasado: entregas.append(
                (item, atrasado)
            )
        )

        self.assertEqual(entregas, [(lembrete, True)])
        self.assertFalse(lembrete.pendente)
        self.assertEqual(lembrete.proximo, 70)

    def test_evita_rajada_quando_o_proximo_horario_ja_passou(self):
        lembrete = criar_lembrete(proximo=30, pendente=True)
        entregas = []

        processar_tick(
            [lembrete], 100, False, lambda item, atrasado: entregas.append(
                (item, atrasado)
            )
        )
        processar_tick(
            [lembrete], 100, False, lambda item, atrasado: entregas.append(
                (item, atrasado)
            )
        )

        self.assertEqual(entregas, [(lembrete, True)])
        self.assertEqual(lembrete.proximo, 160)

    def test_ciclo_completo_adia_e_retoma_a_agenda(self):
        lembrete = criar_lembrete(intervalo=60, atraso_inicial=10, proximo=10)
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
