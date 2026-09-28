# DOCX兼容性回退

## 读取条件

仅在以下一项成立时读取：

- 当前环境无法可靠创建、编辑或验证DOCX；或
- 原生DOCX产出连续两次未通过`docx-delivery.md`所定义的结构验收。

不得因为存在现成脚本就跳过原生DOCX尝试。不得在同一份DOCX上混用原生路径和本回退路径。

## 回退序列

1. 以内容层Markdown为输入，使用`scripts/md_to_docx.py`生成初始DOCX，命令必须带`--confirm-fallback`。
2. 如需将批注章节转为Word批注，再明确执行`scripts/annotations_to_docx_comments.py`，同样必须带`--confirm-fallback`。不得依赖初始转换器自动串联。
3. 运行与原生路径相同的DOCX结构和逐页视觉验收。

```bash
python scripts/md_to_docx.py <报告.md> <报告.docx> --confirm-fallback
python scripts/annotations_to_docx_comments.py <报告.docx> --confirm-fallback
```

## OOXML结构验收（与原生路径同一标准）

回退产出同样须过 `docx-delivery.md` 的结构与视觉验收，另加下列 OOXML 级检查：

- `word/document.xml` 正文**不得出现 `w:numPr`／`numId`**，也不得使用 `List Number` 自动编号样式；
- 有序列表项须为**普通段落＋显式编号文本**（`scripts/md_to_docx.py` 已按此实现，编号字面原样取自源 Markdown，缩进层级以段前缩进表达）；
- 章节、法域、主体与义务分组的编号**各自重新起算**，无跨节连续序列；
- 中英双语续行不产生新编号项。

```bash
python - <<'PY'
import zipfile
xml = zipfile.ZipFile("<报告>.docx").read("word/document.xml").decode("utf-8")
print("numPr:", xml.count("numPr"), "| ListNumber:", xml.count("ListNumber"))
PY
```

## 脚本保护契约

- 缺少`--confirm-fallback`时，脚本只输出“需要明确回退确认”的错误，不创建、覆盖或重新保存DOCX。
- 批注后处理器在处理前应当检查已有`comments.xml`、批注ID和文末待转换章节。已存在原生批注时默认拒绝重复注入。
- 没有批注章节、章节为空或已转换完成时，以无变更方式退出，不调用`doc.save()`重新序列化文件。
- 只有在确实有待转换内容、且显式确认回退时才允许覆盖原DOCX。

回退脚本是兼容性工具，不是DOCX的唯一或默认生成路径。
