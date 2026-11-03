from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("report_lint_regressions", ROOT / "scripts" / "check_report.py")
assert spec and spec.loader
check_report = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = check_report
spec.loader.exec_module(check_report)


class ReportLintRegressions(unittest.TestCase):
    def _report(self, overview_rows=(), detail="", screening=None, titles=()):
        lines = [
            "# 测试报告",
            "",
            "适用范围：本报告检查AI透明度义务。",
            "",
            "## 二、适用义务总览",
            "",
            "| 活动 | 法域 | 状态 | 摘要 | 节点 | 优先级 |",
            "|---|---|---|---|---|---|",
            *overview_rows,
            "",
            "## 三、分法域义务详述",
            "",
            detail,
            "",
        ]
        if screening is not None:
            lines.extend(["### 已核验但未触发事项", "", screening, ""])
        if titles:
            lines.extend(["## 五、落地建议", "", *titles, ""])
        lines.extend([
            "## 六、效力核验记录",
            "",
            "| 法规 | 效力状态 | 核验日期 | 核验来源 |",
            "|---|---|---|---|",
            "| 示例法规 | 现行有效 | 2026-11-04 | 官方来源 |",
            "",
        ])
        return "\n".join(lines)

    def _check(self, report, mode="A"):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.md"
            path.write_text(report, encoding="utf-8")
            return check_report.check_report(path, {"CN", "EU", "CA"}, "zh", mode, ROOT)

    @staticmethod
    def _w06(found):
        return [item for item in found if item.code == "W-06"]

    def test_mode_b_ignores_screening_table_structure(self):
        malformed = "| 法规／事项 | 筛查状态 |\n|---|---|\n| SB 896 | 不适用 |"
        report = self._report(screening=malformed, titles=["### Recommendations"])
        self.assertEqual(self._w06(self._check(report, mode="B")), [])

    def test_zero_obligation_count_ignores_invalid_overview_status(self):
        report = self._report(overview_rows=["| 活动 | 加州 | 未定 | X | Y | P1 |"])
        messages = [item.message for item in self._w06(self._check(report))]
        self.assertTrue(any("无正向行且筛查表无实质结论" in message for message in messages))

    def test_screening_row_with_empty_item_does_not_count_as_substantive(self):
        screening = (
            "| 法域 | 法规／事项 | 筛查状态 | 简要理由 |\n"
            "|---|---|---|---|\n"
            "| 加州 |  | 不适用 | 非州机构 |"
        )
        report = self._report(
            overview_rows=["| 活动 | 加州 | {待填：…} | X | Y | P1 |"],
            screening=screening,
        )
        messages = [item.message for item in self._w06(self._check(report))]
        self.assertTrue(any("法规／事项」为空或占位" in message for message in messages))
        self.assertTrue(any("无正向行且筛查表无实质结论" in message for message in messages))

    def test_pending_status_accepts_only_canonical_value_or_valid_date(self):
        for status in (
            "已适用、义务待生效",
            "已适用、义务待生效（2027-01-01）",
            "已适用、义务待生效(2027-01-01)",
        ):
            with self.subTest(status=status):
                row = f"| 活动 | 加州 | {status} | X | Y | P1 |"
                self.assertFalse(self._w06(self._check(self._report([row]))))

    def test_pending_status_rejects_shorthand_suffix_and_invalid_date(self):
        for status in (
            "已适用",
            "已适用、义务待生效待确认",
            "已适用、义务待生效（2027-99-99）",
        ):
            with self.subTest(status=status):
                row = f"| 活动 | 加州 | {status} | X | Y | P1 |"
                self.assertTrue(self._w06(self._check(self._report([row]))))

    def test_numbered_and_plain_english_titles_are_flagged(self):
        for title in (
            "### 主题：machine-readable-marking",
            "### 主题一：Recommendation for deployment",
            "### 主题一：cop:recommendation",
            "### Recommendations for deployment",
        ):
            with self.subTest(title=title):
                found = self._check(self._report(titles=[title]))
                self.assertTrue(any("标题应为中文" in item.message for item in self._w06(found)))

    def test_chinese_title_may_include_english_parenthetical(self):
        found = self._check(self._report(titles=["### 主题一：机器可读标记（Machine-readable marking）"]))
        self.assertFalse(any("标题应为中文" in item.message for item in self._w06(found)))

    def test_w29_does_not_treat_chinese_heading_prefix_as_jurisdiction(self):
        duty = "### 加州业务观察\n\n**(1) 一般分析**\n\n根据规则，应当完成核查。\n"
        overview = ["| 活动 | 欧盟 | 适用 | Art.50(1) | 当前 | P1 |"]
        found = self._check(self._report(overview_rows=overview, detail=duty))
        self.assertFalse(any(item.code == "W-29" for item in found))

    def test_w29_still_matches_a_delimited_jurisdiction_heading(self):
        duty = "### 加州（California）\n\n**(1) 一般分析**\n\n根据规则，应当完成核查。\n"
        overview = ["| 活动 | 欧盟 | 适用 | Art.50(1) | 当前 | P1 |"]
        found = self._check(self._report(overview_rows=overview, detail=duty))
        self.assertTrue(any(item.code == "W-29" for item in found))


if __name__ == "__main__":
    unittest.main(verbosity=2)
