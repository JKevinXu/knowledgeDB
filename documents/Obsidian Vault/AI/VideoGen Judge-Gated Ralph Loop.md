---
title: VideoGen Judge-Gated Ralph Loop
created: 2026-05-10
updated: 2026-05-10
type: project-progress
status: active
tags:
  - agentic-engineering
  - ralph-loop
  - videogen
  - bilibili
  - basketball-video
  - evaluation
sources:
  - https://github.com/JKevinXu/VideoGen
  - https://github.com/snarktank/ralph
---

# VideoGen Judge-Gated Ralph Loop

## One-line thesis

A useful video-generation Ralph loop should not only “run tasks until the PRD is done”; it should also run a domain-specific customer judge after each iteration and keep looping until the artifact satisfies that judge.

## Current progress snapshot

- Reusable repo: [JKevinXu/VideoGen](https://github.com/JKevinXu/VideoGen)
- Local repo: `/Users/kx/ws/VideoGen`
- Concrete basketball example: `categories/basketball/aj-dybantsa-bilibili/`
- Latest pushed progress commit: `4df2cb0 data: satisfy basketball judge-gated loop`
- Earlier loop-infrastructure commit: `b8ddb3e feat: add judge-gated Ralph loop`
- Current local final video output: `/Users/kx/Desktop/aj_dybantsa_bilibili_30s_work/output/aj_dybantsa_bilibili_judge_gated_v2.mp4`

## Why this matters

This project turns short-video generation from a one-off manual editing process into an [[Agentic Engineering]] loop:

1. generate or edit the video artifact,
2. evaluate it with a domain-specific judge,
3. convert judge failures into Ralph-compatible stories,
4. run another implementation iteration,
5. stop only when the judge gate passes.

The key shift is that “quality” is no longer a vague prompt like “make it better.” It becomes a testable gate with observable dimensions.

## Architecture

### 1. Evidence collector

File:

- `videogen/bilibili_evidence_collector.py`

Purpose:

- Collect structured evidence from real Bilibili basketball videos or search results.
- Preserve URLs, titles, visible metrics, duration, hook notes, visual notes, and audience signals.
- Avoid downloading or reusing copyrighted Bilibili video assets.

Real evidence used in this run came from Bilibili search query `NBA新秀观察`, including examples such as:

- `【2026选秀报告】-首轮预测榜单-1.0`
- `锐评2025届新秀，从夯到拉排名！`
- `『赛场观察』历史级别新秀表现！VJ与哈珀究竟有多强？`
- `这真的是新秀吗？76人探花单节14分`

### 2. Basketball customer judge

File:

- `videogen/judge_agent.py`

Input:

- `target_summary.json` — structured summary of the current video.
- `bilibili_competitors.real.run.json` — structured competitor evidence.

Scored dimensions:

- `hook_clickability`
- `retention_pacing`
- `clarity`
- `basketball_credibility`
- `bilibili_fit`
- `comment_potential`

The judge is deterministic by design. An LLM or browser/vision workflow can enrich the evidence, but the scoring and Ralph feedback stay auditable.

### 3. Judge-gated Ralph loop

File:

- `videogen/ralph_judge_loop.py`

Loop model:

1. Run the basketball judge on current target summary + competitor evidence.
2. Check gate: `overall_score >= min_overall_score` and every dimension `>= min_dimension_score`.
3. If the gate passes, stop and mark `lastJudgeGate.satisfied=true` in the PRD.
4. If the gate fails, merge judge-generated `JUDGE-*` stories into the Ralph PRD.
5. Run one Ralph iteration command if supplied.
6. Repeat until pass or max iterations.

This adapts the open-source [[Ralph Loop Implementation]] pattern from “repeat coding-agent tasks until PRD complete” into “repeat artifact improvement until customer-like judge accepts the result.”

## Concrete run: AJ Dybantsa Bilibili basketball short

### Baseline judge failure

The first real-evidence judge run scored the AJ Dybantsa 30-second Bilibili video:

- overall: `76`
- `hook_clickability`: `48`
- `comment_potential`: `58`
- `clarity`: `94`
- `basketball_credibility`: `86`
- `bilibili_fit`: `87`

The judge feedback was clear:

1. The first three seconds did not feel like a real Bilibili basketball hook.
2. The ending did not ask a concrete comment-triggering question.

Generated Ralph stories:

- `JUDGE-001`: Strengthen the first-3-second hook.
- `JUDGE-002`: Add a Bilibili comment trigger.

### Implementation that satisfied the judge

Instead of re-rendering the full video from scratch, the successful iteration added a reusable ASS subtitle overlay:

- `subtitles/aj_dybantsa_judge_hook_overlay.ass`

Opening hook, visible in the first 0–3.2 seconds:

> 下一个 KD？还是更像保罗乔治？  
> AJ Dybantsa 的真实上限，可能不是“状元热门”这么简单

End-card/comment trigger:

> 你觉得他更像 KD，还是 Paul George？  
> 弹幕/评论区给出你的模板对比

FFmpeg pattern:

```bash
ffmpeg -y -i output/aj_dybantsa_bilibili_subtitled.mp4 \
  -vf "subtitles=subtitles/aj_dybantsa_judge_hook_overlay.ass" \
  -c:v libx264 -preset medium -crf 18 -c:a copy -movflags +faststart \
  output/aj_dybantsa_bilibili_judge_gated_v2.mp4
```

### Passing judge result

After updating the target summary to reflect the new hook and comment trigger, the judge-gated loop passed:

- overall: `86`
- `hook_clickability`: `82`
- `retention_pacing`: `87`
- `clarity`: `94`
- `basketball_credibility`: `86`
- `bilibili_fit`: `87`
- `comment_potential`: `82`

Gate used:

- overall `>= 85`
- every dimension `>= 75`

The important improvement was:

- `hook_clickability`: `48 → 82`
- `comment_potential`: `58 → 82`

## Verification performed

Final local output:

- `/Users/kx/Desktop/aj_dybantsa_bilibili_30s_work/output/aj_dybantsa_bilibili_judge_gated_v2.mp4`

Media QA:

- duration: `30.0s`
- resolution: `1280x720`
- frame rate: `30fps`
- audio stream: present
- aspect ratio: 16:9

Vision checks:

- opening hook frame: Chinese rendered correctly, no tofu boxes, hook readable.
- end-card frame: Chinese rendered correctly, no tofu boxes, comment trigger readable.
- layout suitable for Bilibili horizontal sports short, though slightly dense.

Automated tests:

```bash
python3 -m unittest tests/test_judge_agent.py tests/test_bilibili_evidence_collector.py tests/test_ralph_judge_loop.py -v
```

Result: `10 tests passed`.

## Durable patterns

### Pattern 1 — Judge feedback should become small Ralph stories

Avoid vague tasks like “improve video quality.” The judge should emit specific stories such as:

- strengthen the first-three-second hook,
- add an end-card comment trigger,
- improve mobile subtitle readability,
- add sourced basketball evidence cards.

### Pattern 2 — The judge needs structured evidence, not imagination

The Bilibili judge is only as good as the evidence supplied. Store observed competitor metadata and manual notes as JSON, and clearly distinguish:

- real inspected evidence,
- search-result metadata,
- sample/synthetic evidence.

### Pattern 3 — Deterministic judges need target summaries updated

The deterministic judge cannot “see” a newly rendered video unless the target summary or extracted evidence is updated. After each successful edit, update `target_summary.json` with what changed.

### Pattern 4 — Overlays are a fast iteration mechanism

For short-form sports videos, an ASS overlay can test hook/end-card changes much faster than regenerating all visual frames or re-synthesizing narration.

Useful overlay flow:

1. write new `.ass` overlay,
2. burn it into the existing MP4,
3. extract preview frames,
4. vision-check text readability,
5. update target summary,
6. rerun judge gate.

### Pattern 5 — Generated media stays local; reusable sources go to GitHub

`VideoGen` tracks:

- scripts,
- templates,
- subtitle/overlay sources,
- PRDs,
- progress logs,
- JSON evidence,
- judge reports,
- QA text.

It intentionally does not commit generated MP4/MP3/JPG/PNG artifacts.

## Risks and limitations

- Current real Bilibili evidence came from search results and visible metadata/manual notes, not full frame-by-frame video watching.
- The judge is deterministic and only reflects encoded heuristics plus supplied evidence.
- Passing the judge gate is not the same as proving real audience performance.
- Real upload results should still be measured with Bilibili analytics: CTR, completion rate, comments, danmu, and retention.
- Copyright constraints remain: do not embed unlicensed NBA/ESPN/Overtime/Ballislife/FIBA/USA Basketball footage or stills without rights.

## Next improvements

- Add a browser/vision collector that opens Bilibili videos, captures allowed screenshots/observable frames, and records hook/visual evidence without downloading video assets.
- Add a cover-thumbnail judge and generator.
- Add LUFS/volume normalization to media QA.
- Add an upload package generator: title, description, tags, partition, attribution.
- Feed real post-upload analytics back into the judge evidence model.

## Related

- [[Agentic Engineering]]
- [[Ralph Loop Implementation]]
- [[Verifiability in AI Automation]]
- [[Engineering Judgment]]
- [[Obsidian as an LLM Wiki IDE]]

## References

- VideoGen repository: [JKevinXu/VideoGen](https://github.com/JKevinXu/VideoGen)
- Ralph repository: [snarktank/ralph](https://github.com/snarktank/ralph)
- Current local VideoGen repo: `/Users/kx/ws/VideoGen`
- Current local generated video: `/Users/kx/Desktop/aj_dybantsa_bilibili_30s_work/output/aj_dybantsa_bilibili_judge_gated_v2.mp4`
