# AI Research Ideas

这是一个开放的 **AI + Idea 科研库**：人负责提出关键原创科研 Idea 和核心提示词，AI 可以辅助完成文献检索、代码、数据整理、实验、分析、结果、图片、论文草稿以及 GitHub 内容整理等工作。

## 最低投稿要求

**一个 `.md` Markdown 文字文件就够了。**

例如：

```markdown
# 我的科研 Idea

我认为……

核心想法：……

给 AI 的提示词：……
```

代码、数据、图片、PDF、Notebook 等都可以上传，但全部是可选项。

投稿者应当真诚地认为自己的核心 Idea 是原创的，并且没有发现学术界已经公开披露相同的核心 Idea。

## 投稿流程

```text
Fork 仓库
   ↓
submissions/<自己的GitHub用户名>/<任意短名称>/
   ↓
至少放一个 .md 文件
   ↓
Pull Request
   ↓
合并后系统分配序号和 GMT+3 时间
   ↓
ideas/000001_YYYYMMDD_HHMMSS_GMTp3/
```

不再强制要求 `metadata.yml`、摘要表、关键词、代码、数据或文献检索表格。

## 所有权

系统会在内部 `registry/ideas.json` 中自动记录 Idea 所有者。用户以后可以添加、修改或删除自己 Idea 文件夹中的内容，也可以删除自己的整个 Idea；普通用户不能修改其他人的 Idea，也不能修改平台核心文件。

## 浏览

[ideas/README.md](ideas/README.md) 会自动从每个 Idea 的第一个 Markdown 文件提取标题和简要预览，让读者在进入文件夹之前大致了解 Idea 内容。
