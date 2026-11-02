"""Tests M1 : parseur Fountain vers JSON de plan, sur un script de 2 pages."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "engine", "script"))
import fountain  # noqa: E402
import schema  # noqa: E402
import json  # noqa: E402
import tempfile  # noqa: E402

SCRIPT = os.path.join(HERE, "donnees", "script_2p.fountain")


class TestFountain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(SCRIPT, encoding="utf-8") as f:
            cls.plan = fountain.parser(f.read())

    def test_titre(self):
        self.assertEqual(self.plan["titre"], "Éclipse Royale - Épisode test")

    def test_deux_scenes(self):
        self.assertEqual(len(self.plan["scenes"]), 2)

    def test_entete_scene(self):
        s1 = self.plan["scenes"][0]
        self.assertEqual(s1["type"], "EXT")
        self.assertEqual(s1["lieu"], "COL DE PIERRE")
        self.assertEqual(s1["moment"], "AUBE")

    def test_personnages(self):
        self.assertEqual(fountain.personnages(self.plan),
                         ["KAEL", "AIKO SORYU", "ALARIC", "DARIUS VALEN"])

    def test_dialogue_et_parenthese(self):
        dial = [e for s in self.plan["scenes"] for e in s["elements"] if e["type"] == "dialogue"]
        premier = dial[0]
        self.assertEqual(premier["personnage"], "KAEL")
        self.assertEqual(premier["parentheses"], ["bas"])
        self.assertEqual(premier["texte"], "La nuit n'a pas encore fini.")

    def test_action_et_transition(self):
        elements = [e for s in self.plan["scenes"] for e in s["elements"]]
        self.assertTrue(any(e["type"] == "action" and "Vorthaz" in e["texte"] for e in elements))
        self.assertTrue(any(e["type"] == "transition" and e["texte"] == "CUT TO:" for e in elements))

    def test_nombre_de_dialogues(self):
        dial = [e for s in self.plan["scenes"] for e in s["elements"] if e["type"] == "dialogue"]
        self.assertEqual(len(dial), 5)

    def test_transition_d_ouverture(self):
        self.assertEqual([e["texte"] for e in self.plan["transitions_debut"]], ["FADE IN:"])

    def test_json_genere_et_valide(self):
        with tempfile.TemporaryDirectory() as d:
            sortie = os.path.join(d, "plan.json")
            import subprocess
            subprocess.run([sys.executable, os.path.join(HERE, "..", "engine", "script", "fountain.py"),
                            SCRIPT, sortie], check=True, capture_output=True)
            with open(sortie, encoding="utf-8") as f:
                plan = json.load(f)
        self.assertEqual(schema.valider(plan), [])

    def test_validateur_refuse_plan_casse(self):
        casse = {"format": "monteur/plan/1", "titre": "x", "transitions_debut": [],
                 "scenes": [{"id": "s01", "lieu": "A", "elements": [
                     {"type": "dialogue", "personnage": "", "parentheses": [], "texte": "oui"}]}]}
        self.assertTrue(any("sans personnage" in e for e in schema.valider(casse)))


if __name__ == "__main__":
    unittest.main()
