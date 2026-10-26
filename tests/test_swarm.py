import asyncio
import os
import tempfile
import unittest

from research_swarm.agents import ResearcherAgent, extract_citations
from research_swarm.config import SwarmConfig
from research_swarm.orchestrator import run_swarm
from research_swarm.providers import MockProvider
from research_swarm.report import save_markdown
from research_swarm.tools import calc, offline_search, web_search


class TestTools(unittest.TestCase):
    def test_offline_search(self):
        out = offline_search("fusion", k=3)
        self.assertIn("offline demo", out)
        self.assertIn("https://", out)

    def test_web_search_offline_flag(self):
        out = web_search("anything", k=2, offline=True)
        self.assertIn("offline demo", out)

    def test_calc(self):
        self.assertIn("= 7.0", calc("3+4"))
        self.assertIn("= 2.0", calc("(1200*0.02)/12"))


class TestAgents(unittest.TestCase):
    def test_researcher_mock(self):
        async def go():
            a = ResearcherAgent(angle="skeptic", lens="you are a skeptic",
                                provider=MockProvider(), offline=True, max_rounds=2)
            return await a.research("are LLMs conscious?")
        rep = asyncio.run(go())
        self.assertEqual(rep.angle, "skeptic")
        self.assertGreaterEqual(rep.tool_calls, 1)
        self.assertTrue(rep.citations)
        self.assertIn("skeptic", rep.findings.lower())

    def test_citations(self):
        urls = extract_citations("see [a](https://example.com/x) and https://example.com/y.")
        self.assertEqual(len(urls), 2)


class TestOrchestrator(unittest.TestCase):
    def test_swarm_quick_mock(self):
        async def go():
            cfg = SwarmConfig(query="is fusion close?", angles=2,
                              depth="quick", provider="mock", offline=True)
            return await run_swarm(cfg)
        res = asyncio.run(go())
        self.assertEqual(len(res.reports), 2)
        self.assertIn("fusion", res.final_markdown.lower())
        self.assertTrue(res.total_tool_calls >= 2)
        self.assertGreater(res.elapsed_s, 0)

    def test_save(self):
        with tempfile.TemporaryDirectory() as d:
            p = save_markdown("# hi\n", query="test query", out_dir=d)
            self.assertTrue(os.path.exists(p))
            self.assertIn("test-query", os.path.basename(p))


if __name__ == "__main__":
    unittest.main()
