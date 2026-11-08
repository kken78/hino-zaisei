# DESIGN.md

hino-budget（当初予算 主な事業）の画面の設計の決定を記録する。ポータル全体の決まりは hino-portal の DESIGN.md による。

## 設計の決定

### ADR-1 共通の部品を hino-portal の正本から写す

決定 2026-11-07。hino-portal DESIGN.md 9.2 の段階1による。

- 共通の部品（見出し・分野のナビ・ページの一覧・フッター）は、hino-portal の `shared/` の正本（shell.css・header.html・siblings-plan.html・footer.html）を `index.html` に写す。写したものは `<!-- portal-shared:〈名前〉 start -->` と `<!-- portal-shared:〈名前〉 end -->` で囲む。
- 写したものは手で変えない。変えるときは、hino-portal の正本を先に変えてから写し直す。
- CI（`.github/workflows/check.yml`）で、hino-portal を浅く取ってきて `shared/check.py` を走らせ、写したものが正本と同じかを確かめる。
- ページの構造（共通の見出し、ページの見出し、分野の中のページの一覧、本文、フッター）は hino-portal DESIGN.md 2章による。このページの分野は「計画と予算」、ページの題は「当初予算 主な事業（令和3〜8年度）」。
- 段階1では、ページの色・文字の大きさ・グラフは変えない（段階2以降）。
