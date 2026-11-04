import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate_cop_coverage import signature_review_issues, validate
from check_report import check_report
from survey_io import unwrap

class SignatureReviewTests(unittest.TestCase):
    def matrix(self, status='未签署', relevant=None, signed=None):
        return {'signatory': {'status': status, 'sections': signed or []},
                'relevant_sections': ['Section 1'] if relevant is None else relevant}

    def paragraph(self, section='Section 1', status='未签署'):
        if status == '不确定':
            text = f'签署状态不确定，请核实；若尚未签署{section}，建议评估是否签署。'
        elif status == '计划签署':
            text = f'原记录为计划签署，当前尚未签署{section}，建议评估是否签署并核对计划完成情况。'
        else:
            text = f'当前{status}，{section}未覆盖，建议评估是否补充签署。'
        return text + f'\n<!-- cop:signature-review section="{section}" -->\n'

    def report(self, body):
        return '## 五、落地建议\n\n' + body + '\n## 六、效力核验记录\n'

    def test_unsigned_missing_advice_is_detected(self):
        self.assertTrue(signature_review_issues(self.matrix(), self.report('没有建议。')))

    def test_unsigned_complete_advice_passes(self):
        self.assertEqual(signature_review_issues(self.matrix(), self.report(self.paragraph())), [])

    def test_both_sections_need_their_own_advice(self):
        matrix = self.matrix(relevant=['Section 1', 'Section 2'])
        report = self.report(self.paragraph())
        self.assertEqual(len(signature_review_issues(matrix, report)), 1)
        self.assertEqual(signature_review_issues(matrix, self.report(self.paragraph()+'\n'+self.paragraph('Section 2'))), [])

    def test_partial_signature_checks_only_missing_section(self):
        matrix = self.matrix('已签署', ['Section 1', 'Section 2'], ['Section 1'])
        self.assertEqual(signature_review_issues(matrix, self.report(self.paragraph('Section 2', '已签署'))), [])

    def test_fully_signed_and_no_relevant_section_need_no_advice(self):
        self.assertEqual(signature_review_issues(self.matrix('已签署', signed=['Section 1']), ''), [])
        self.assertEqual(signature_review_issues(self.matrix(relevant=[]), ''), [])

    def test_unknown_needs_conditional_fact_check(self):
        self.assertEqual(signature_review_issues(self.matrix('不确定'), self.report(self.paragraph(status='不确定'))), [])
        bad = self.paragraph().replace('未签署', '不确定')
        self.assertTrue(signature_review_issues(self.matrix('不确定'), self.report(bad)))

    def test_planned_sections_do_not_count_as_actual_signature(self):
        matrix = self.matrix('计划签署', signed=['Section 1'])
        original = json.loads(json.dumps(matrix))
        self.assertTrue(signature_review_issues(matrix, ''))
        self.assertEqual(signature_review_issues(matrix, self.report(self.paragraph(status='计划签署'))), [])
        self.assertEqual(matrix, original)

    def test_marker_alone_and_comments_cannot_pass(self):
        self.assertTrue(signature_review_issues(self.matrix(), self.report('<!-- cop:signature-review section="Section 1" -->')))
        self.assertTrue(signature_review_issues(self.matrix(), self.report('<!-- 未签署Section 1，评估签署 -->\n<!-- cop:signature-review section="Section 1" -->')))

    def test_fenced_or_annotation_advice_cannot_pass(self):
        self.assertTrue(signature_review_issues(self.matrix(), self.report('```md\n'+self.paragraph()+'```\n')))
        text = '## 五、落地建议\n\n无。\n## 七、批注\n\n'+self.paragraph()
        self.assertTrue(signature_review_issues(self.matrix(), text))

    def test_old_plan_audit_stays_readable_and_unchanged(self):
        original = {'status': '计划签署', 'sections': ['Section 1']}
        bundle = unwrap({'schema': 'survey_audit/3', 'answers': {
            'A2': '混合模式', 'A3': ['文本'], 'A6': ['欧盟'], 'B11_cop': original}})
        self.assertEqual(bundle['B11_cop'], original)

    def test_w27_executes_on_real_report_and_matrix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root/'case.md'
            (root/'.audit').mkdir()
            (root/'.audit'/'case.cop_case_matrix.json').write_text(json.dumps(self.matrix()), encoding='utf-8')
            report.write_text(self.report('缺建议。'), encoding='utf-8')
            self.assertTrue(any(f.code=='W-27' for f in check_report(report, {'EU'}, 'zh', 'A', ROOT)))
            report.write_text(self.report(self.paragraph()), encoding='utf-8')
            self.assertFalse(any(f.code=='W-27' for f in check_report(report, {'EU'}, 'zh', 'A', ROOT)))

    def test_coverage_validator_also_reports_signature_gap(self):
        matrix = self.matrix()
        _, warnings = validate(ROOT, matrix, self.report('缺建议。'))
        self.assertTrue(any('COV-22' in issue for issue in warnings))
        _, warnings = validate(ROOT, matrix, self.report(self.paragraph()))
        self.assertFalse(any('COV-22' in issue for issue in warnings))

if __name__ == '__main__':
    unittest.main()
