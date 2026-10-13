# ARCHIVE: what was removed in the clean-slate rebuild

Tag `archive/pre-rebuild-2026-10-13` (commit 72a49c0, pushed to origin) holds the whole app exactly as it was before
the purge: old onboarding, quiz flow, progress, old home scene and everything else below. Nothing is lost.

Restore one file:        git checkout archive/pre-rebuild-2026-10-13 -- <path>
Restore a whole group:   git checkout archive/pre-rebuild-2026-10-13 -- <path> <path> ...   (paths listed per group)
Read a file without restoring it:   git show archive/pre-rebuild-2026-10-13:<path>
Browse the old tree:     git ls-tree -r --name-only archive/pre-rebuild-2026-10-13 ios/mockjuice
Restore the entire old app into a separate folder:   git worktree add ../mockjuice-old archive/pre-rebuild-2026-10-13

All paths are relative to the repo root; the app lives in ios/mockjuice/.

## What stays (not archived)
questions.json (784 questions), mockjuice_images/, Assets.xcassets/ (cleanup left to the owner), Models/Question.swift,
Models/TheoryQuestionBank.swift, Models/Category.swift, Utilities/BundledImageResolver.swift,
Utilities/VideoDownloadManager.swift, Utilities/FontRegistrar.swift, Utilities/Theme.swift, the forest art
(Views/Components/ForestPathIllustration.swift, 17-layer v2) and Views/HomeSceneView.swift, the mascot
(Views/MascotAnimation.swift, MascotAccessories.swift, MascotSandbox.swift, plus Views/Components/HomeSceneRoad.swift
which the mascot references), mockjuiceApp.swift, ContentView.swift (now just HomeSceneView), tools/, docs.

## Removed, by group

### Onboarding (replaced by a full redo; was live)
- ios/mockjuice/Views/OnboardingView.swift
- ios/mockjuice/Views/Components/AppLogoView.swift (logo asset JuiceBoxLogo still exists)

### Quiz flow UI (to be redesigned)
- ios/mockjuice/Views/JourneyPathView.swift (the scrolling journey screen; entry to everything in this group; was commented out in ContentView)
- ios/mockjuice/Views/QuestionView.swift
- ios/mockjuice/Views/ResultsView.swift
- ios/mockjuice/Views/TheoryIntroView.swift
- ios/mockjuice/Views/TheorySubcategorySelectionView.swift
- ios/mockjuice/Views/MockTestIntroView.swift
- ios/mockjuice/Views/FlaggedQuestionsIntroView.swift
- ios/mockjuice/Views/AdviceInfoView.swift
- ios/mockjuice/Views/CategoryInfoModalView.swift
- ios/mockjuice/Views/SettingsView.swift
- ios/mockjuice/Views/VideoDownloadIntroView.swift
- ios/mockjuice/Views/Components/QuestionImageView.swift
- ios/mockjuice/Views/Components/QuestionVideoPlayerView.swift
- ios/mockjuice/Views/Components/JourneyNodeView.swift
- ios/mockjuice/Views/Components/TheoryIconGlyphs.swift
- ios/mockjuice/Views/Components/RoadPathShape.swift (road shape used by the journey screen)

### Quiz and progress logic (removed on purpose; to be rewritten)
- ios/mockjuice/ViewModels/QuizViewModel.swift (session state, timer, answer handling)
- ios/mockjuice/Utilities/QuestionSequencer.swift (question ordering, weakest-first)
- ios/mockjuice/Models/UserProgress.swift (per-question progress, aggregated on read, no per-category counters)
- ios/mockjuice/Models/ProgressModels.swift (QuestionRecord, CategorySessionState)
- ios/mockjuice/Utilities/ProgressStore.swift (persistence)

### Progress tab and navigation chrome
- ios/mockjuice/Views/ProgressTabView.swift (was unreachable at runtime)
- ios/mockjuice/Views/Components/FloatingTabBar.swift
- ios/mockjuice/Views/Components/LiquidProgressBar.swift

### Old home scene (replaced by the forest illustration)
- ios/mockjuice/Views/Components/HomeSceneArt.swift (78 KB of old scene data; nothing used it)
- ios/mockjuice/Views/Components/HomeSceneIllustration.swift
  (HomeSceneRoad.swift, the road centreline maths, was kept because the mascot references it; reusable for placing nodes)

### Orphans
- ios/mockjuice/Models/CategoryInfo.swift (referenced by nothing)
- ios/mockjuice/Config.swift (platform-generated stub with empty EXPO_PUBLIC_* keys, unused)

## Docs
- DESIGN.md (design system notes: palette, journey node colours; outdated, removed). Restore: git show archive/pre-rebuild-2026-10-13:DESIGN.md

## Older forest art (also in the tag)
The 14-layer Phase B version of the forest art is in git history before commit 72a49c0 (commit 1a3c35a) and in
tools/forest-v2/backup/ForestPathIllustration.phaseB.swift.

## Not touched in this purge
tools/ (forest-regrade, forest-v2, forest-extension, image2swiftui, mascot), the root venv/, Assets.xcassets contents.
