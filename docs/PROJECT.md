# mockjuice: project scope and status

The app in one line: a UK driving theory test prep app. Product feel is in `VISION.md`;
how the code is laid out is in the section below.

## The skeleton
1. **Onboarding**: shown on first launch only, then into the home screen.
2. **Home screen**: a vertically scrolling forest map with 5 nodes, one per major category.
3. **Category screen**: opened from a node, lists that category's subcategories.
4. **Subcategories and below**: the question flow.
5. **Everything else** (progress, settings and so on) is added later and is miscellaneous.

## The five major categories
Working names: theory, highway code, road signs, mock test, explore. The contents of the last four are not defined
yet; they are self-explanatory and will be specified when built.

**Theory** has 16 subcategories:
- 14 topics from the question bank: alertness, attitude, essential documents, hazard awareness, road and traffic signs,
  incidents/accidents/emergencies, other types of vehicle, vehicle handling, motorway rules, rules of the road,
  safety margins, safety and your vehicle, vulnerable road users, vehicle loading.
- 2 combined views over the same bank: "all categories" (all questions) and "videos" (the questions with a video).

## Content (non-negotiable, kept)
- `questions.json`: 784 questions in 14 topics; 203 have an image, 27 have a video.
- `mockjuice_images/`: 223 question images, found by `BundledImageResolver`.
- Videos are not in the repo: each question names a file (for example `vm2016.mp4`) and `VideoDownloadManager`
  downloads it from Cloudinary.

## Status
| Piece | Status |
|---|---|
| Home screen art (forest, 17 layers, CPU-rendered) | Done, live |
| Home screen map extension (one more screen of art, scrolling) | Not started. Prompt written; build session stopped in Stage 1, see `tools/forest-extension/` |
| 5 nodes on the home screen | Not started |
| Onboarding | Not started |
| Category screen and subcategories | Not started |
| Question flow and results | Not started |
| Progress and settings | Not started (later) |
| Mascot (animation, accessories, sandbox) | Kept; not wired into any screen yet |

## Code layout
One Xcode target, `ios/mockjuice/`; everything in that folder is compiled into the app.
```text
mockjuiceApp.swift, ContentView.swift   entry; ContentView shows HomeSceneView
Models/        Category, Question, TheoryQuestionBank   (question bank types and loading)
Utilities/     BundledImageResolver, FontRegistrar, Theme, VideoDownloadManager
Views/         HomeSceneView, Mascot*  (new features get their own folder here: Onboarding/, Category/, Quiz/ ...)
  Components/  ForestPathIllustration (art + renderer), HomeSceneRoad (used by the mascot)
Resources/Fonts, questions.json, mockjuice_images/, Assets.xcassets/
```
Rules: one folder per feature under `Views/`; nothing dead stays in the tree (archive it with a git tag and list it in
`ARCHIVE.md`); update the status table above when a piece changes.

## Tooling (not part of the app)
`tools/forest-regrade` (how the forest art was made and measured, with scripts), `tools/forest-v2` (second forest
redo, paused), `tools/forest-extension` (extension work in progress), `tools/image2swiftui` (generic image tracer),
`tools/mascot`.
