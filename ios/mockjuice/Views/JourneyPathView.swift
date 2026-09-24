import SwiftUI

nonisolated enum JourneyRoute: Hashable, Sendable {
    /// The 16-category list shown right after entering theory.
    case theoryStudy
    case flaggedQuestions
    case adviceInfo
    case highwayCode
    case roadSigns
    case mockTest
    case explore
}

struct JourneyPathView: View {
    @Bindable var progress: UserProgress
    let homeResetTrigger: Int
    @State private var path = NavigationPath()
    @State private var activeSession: QuizSessionKind? = nil
    /// Drives the full-screen practice mode picker.
    @State private var selectedCategory: QuizCategory? = nil
    /// Held until the picker has finished dismissing, so the two full-screen
    /// presentations never overlap and cancel each other out.
    @State private var pendingSession: QuizSessionKind? = nil
    @State private var appeared: Bool = false
    @State private var showSettings: Bool = false
    /// One-time hazard-clip download intro, shown before the very first topic
    /// selection. `pendingCategoryAfterIntro` holds the tapped topic until the
    /// intro screen finishes dismissing, so it never overlaps the picker.
    @State private var showVideoDownloadIntro: Bool = false
    @State private var pendingCategoryAfterIntro: QuizCategory? = nil
    /// One-time theory category intro modal, shown the first time the learner
    /// navigates into the theory section.
    @State private var showTheoryIntro: Bool = false

    private let nodes = JourneyNode.allCases

    var body: some View {
        NavigationStack(path: $path) {
            ZStack {
                SceneryBackgroundView()

                ScrollView(.vertical, showsIndicators: false) {
                    VStack(spacing: 0) {
                        readinessCard
                            .padding(.horizontal, 20)
                            .padding(.top, 16)
                            .padding(.bottom, 24)

                        sectionHeader
                            .padding(.horizontal, 20)
                            .padding(.bottom, 20)

                        journeyContent
                            .padding(.bottom, 180)
                    }
                }
            }
            .overlay(alignment: .topTrailing) {
                settingsButton
                    .padding(.trailing, 20)
                    .padding(.top, 4)
            }
            .navigationBarHidden(true)
            .navigationDestination(for: JourneyRoute.self) { route in
                switch route {
                case .theoryStudy:
                    TheorySubcategorySelectionView(progress: progress) { category in
                        let showIntro = !progress.seenCategoryIntros.contains(category.id)

                        if progress.hasSeenVideoDownloadIntro {
                            if showIntro {
                                selectedCategory = category
                            } else {
                                // Jump straight to weakest-first if we've seen the modal
                                activeSession = .category(category, .weakestFirst)
                            }
                        } else {
                            // If we need the video intro, we stash the category.
                            // The logic below will handle showing the modal or quiz after the intro.
                            pendingCategoryAfterIntro = category
                            showVideoDownloadIntro = true
                        }
                    }
                    .fullScreenCover(item: $selectedCategory) { category in
                        CategoryInfoModalView(category: category) {
                            progress.markCategoryIntroSeen(category.id)
                            pendingSession = .category(category, .weakestFirst)
                            selectedCategory = nil
                        }
                    }
                case .flaggedQuestions:
                    ScrollView(.vertical, showsIndicators: false) {
                        FlaggedQuestionsIntroView(progress: progress) {
                            activeSession = .flaggedReview
                        }
                        .padding(.horizontal, 20)
                        .padding(.top, 18)
                        .padding(.bottom, 120)
                    }
                    .background(MJTheme.cartonCream.ignoresSafeArea())
                    .navigationTitle("flagged questions")
                    .navigationBarTitleDisplayMode(.inline)
                case .adviceInfo:
                    AdviceInfoView()
                case .highwayCode:
                    educationalPlaceholder(
                        title: "highway code",
                        description: "reading lessons and quick quizzes land here next. the journey node stays in place so the roadmap is ready for the content drop."
                    )
                case .roadSigns:
                    educationalPlaceholder(
                        title: "road signs",
                        description: "sign guides and quizzes will live here. the node remains connected so navigation already matches the new journey structure."
                    )
                case .mockTest:
                    educationalPlaceholder(
                        title: "hazard perception",
                        description: "video clips are coming next. this placeholder keeps the node in the correct position without changing the visual journey design."
                    )
                case .explore:
                    ScrollView(.vertical, showsIndicators: false) {
                        MockTestIntroView(progress: progress) {
                            activeSession = .mockTest
                        }
                        .padding(.horizontal, 20)
                        .padding(.top, 18)
                        .padding(.bottom, 120)
                    }
                    .background(MJTheme.cartonCream.ignoresSafeArea())
                    .navigationTitle("mock test")
                    .navigationBarTitleDisplayMode(.inline)
                }
            }
        }
        .fullScreenCover(item: $activeSession) { session in
            QuestionView(sessionKind: session, progress: progress)
        }
        // The picker sets `pendingSession` and closes; the quiz opens only once
        // that dismissal has actually completed.
        .onChange(of: selectedCategory) { _, newValue in
            guard newValue == nil, let session = pendingSession else { return }
            pendingSession = nil
            activeSession = session
        }
        .fullScreenCover(isPresented: $showVideoDownloadIntro) {
            VideoDownloadIntroView(
                onContinue: {
                    progress.markVideoDownloadIntroSeen()
                    showVideoDownloadIntro = false
                },
                onNeutralExit: {
                    pendingCategoryAfterIntro = nil
                    showVideoDownloadIntro = false
                }
            )
        }
        // Mirrors the picker/session sequencing above: the topic tap is only
        // acted on once the intro screen has actually finished dismissing.
        .onChange(of: showVideoDownloadIntro) { _, newValue in
            guard !newValue, let category = pendingCategoryAfterIntro else { return }
            pendingCategoryAfterIntro = nil

            if !progress.seenCategoryIntros.contains(category.id) {
                selectedCategory = category
            } else {
                activeSession = .category(category, .weakestFirst)
            }
        }
        .sheet(isPresented: $showTheoryIntro) {
            TheoryIntroView {
                showTheoryIntro = false
                path.append(JourneyRoute.theoryStudy)
            } onDontShowAgain: {
                progress.markTheoryIntroSeen()
                showTheoryIntro = false
                path.append(JourneyRoute.theoryStudy)
            }
        }
        .sheet(isPresented: $showSettings) {
            SettingsView(progress: progress)
        }
    }

    private var settingsButton: some View {
        Button {
            showSettings = true
        } label: {
            Image(systemName: "gearshape.fill")
                .font(.system(size: 17, weight: .bold))
                .foregroundStyle(MJTheme.deepForest)
                .frame(width: 44, height: 44)
                .background(
                    Circle()
                        .fill(MJTheme.innocentWhite)
                        .shadow(color: MJTheme.deepForest.opacity(0.18), radius: 8, y: 4)
                )
                .contentShape(Circle())
        }
        .buttonStyle(MJPressScaleButtonStyle())
        .accessibilityLabel("settings")
    }

    private var readinessCard: some View {
        VStack(spacing: 12) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("test readiness")
                        .font(.mjRounded(.caption, weight: .heavy))
                        .tracking(-0.2)
                        .textCase(.lowercase)
                        .foregroundStyle(MJTheme.deepForest.opacity(0.6))

                    Text("\(Int(progress.overallReadiness * 100))% ready")
                        .font(.mjRounded(.title2, weight: .black))
                        .tracking(-0.3)
                        .textCase(.lowercase)
                        .foregroundStyle(MJTheme.deepForest)
                }

                Spacer()
            }

            LiquidProgressBar(
                progress: progress.overallReadiness,
                height: 14,
                foregroundColor: MJTheme.cardinal,
                backgroundColor: MJTheme.locked.opacity(0.45)
            )
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(MJTheme.spring)
        )
        .shadow(color: MJTheme.deepForest.opacity(0.12), radius: 14, y: 6)
    }

    private var sectionHeader: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text("section 1")
                    .font(.mjRounded(.caption, weight: .heavy))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest.opacity(0.55))
                Text("learn to drive")
                    .font(.mjRounded(.title3, weight: .black))
                    .tracking(-0.3)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest)
            }

            Spacer()

            Image(systemName: "road.lanes")
                .font(.system(size: 22, weight: .bold))
                .foregroundStyle(MJTheme.deepForest.opacity(0.5))
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 14)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(MJTheme.innocentWhite)
        )
        .shadow(color: MJTheme.deepForest.opacity(0.1), radius: 10, y: 5)
    }

    private var journeyContent: some View {
        GeometryReader { geo in
            let width = geo.size.width
            let positions = nodePositions(in: width)
            let contentHeight = CGFloat(nodes.count) * 165 + 40

            ZStack {
                TreeSceneryView(width: width, contentHeight: contentHeight)

                RoadPathView(nodePositions: positions)

                ForEach(Array(nodes.enumerated()), id: \.element.id) { index, node in
                    let position = positions[index]
                    let unlocked = progress.isUnlocked(node)
                    let isNext = unlocked && !progress.completedNodes.contains(node.id)

                    VStack(spacing: 6) {
                        JourneyNodeView(
                            node: node,
                            isUnlocked: unlocked,
                            score: progress.score(for: node),
                            isActive: isNext
                        ) {
                            handleNodeTap(node)
                        }

                        JourneyNodeLabel(text: node.shortName, isUnlocked: unlocked)
                    }
                    .position(x: position.x, y: position.y)
                    .opacity(appeared ? 1 : 0)
                    .offset(y: appeared ? 0 : 20)
                    .animation(.spring(response: 0.5).delay(Double(index) * 0.1), value: appeared)
                }
            }
        }
        .frame(height: CGFloat(nodes.count) * 165 + 40)
        .onAppear {
            guard !appeared else { return }
            withAnimation {
                appeared = true
            }
        }
        .onChange(of: homeResetTrigger) { _, _ in
            guard !path.isEmpty else { return }
            path.removeLast(path.count)
        }
    }

    private func nodePositions(in width: CGFloat) -> [CGPoint] {
        let centerX = width / 2
        let amplitude = width * 0.22
        let startY: CGFloat = 80
        let spacing: CGFloat = 165

        return nodes.enumerated().map { index, _ in
            let y = startY + CGFloat(index) * spacing
            let xOffset: CGFloat
            switch index % 5 {
            case 0:
                xOffset = 0
            case 1:
                xOffset = amplitude
            case 2:
                xOffset = amplitude * 0.5
            case 3:
                xOffset = -amplitude
            case 4:
                xOffset = -amplitude * 0.3
            default:
                xOffset = 0
            }
            return CGPoint(x: centerX + xOffset, y: y)
        }
    }

    private func handleNodeTap(_ node: JourneyNode) {
        switch node {
        case .theory:
            if !progress.hasSeenTheoryIntro {
                showTheoryIntro = true
            } else {
                path.append(JourneyRoute.theoryStudy)
            }
        case .highwayCode:
            progress.completeNode(.highwayCode, score: max(progress.score(for: .highwayCode), 10))
            path.append(JourneyRoute.highwayCode)
        case .roadSigns:
            progress.completeNode(.roadSigns, score: max(progress.score(for: .roadSigns), 10))
            path.append(JourneyRoute.roadSigns)
        case .mockTest:
            progress.completeNode(.mockTest, score: max(progress.score(for: .mockTest), 10))
            path.append(JourneyRoute.mockTest)
        case .explore:
            path.append(JourneyRoute.explore)
        }
    }

    private func educationalPlaceholder(title: String, description: String) -> some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .leading, spacing: 18) {
                AppLogoView(width: 74, height: 74)
                    .frame(maxWidth: .infinity)
                    .padding(.top, 12)

                Text(title)
                    .font(.mjRounded(.largeTitle, weight: .black))
                    .tracking(-0.5)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest)

                Text(description)
                    .font(.mjRounded(.body, weight: .bold))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest.opacity(0.6))

                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .fill(MJTheme.innocentWhite)
                    .frame(height: 220)
                    .overlay {
                        VStack(spacing: 10) {
                            Image(systemName: "sparkles.rectangle.stack.fill")
                                .font(.system(size: 34, weight: .bold))
                                .foregroundStyle(MJTheme.cardinal)
                            Text("content placeholder")
                                .font(.mjRounded(.headline, weight: .black))
                                .textCase(.lowercase)
                                .foregroundStyle(MJTheme.deepForest)
                            Text("ready for licensed content and richer reading flows")
                                .font(.mjRounded(.caption, weight: .bold))
                                .tracking(-0.2)
                                .multilineTextAlignment(.center)
                                .foregroundStyle(MJTheme.deepForest.opacity(0.5))
                        }
                        .padding(20)
                    }
                    .shadow(color: MJTheme.deepForest.opacity(0.06), radius: 8, y: 4)
            }
            .padding(.horizontal, 20)
            .padding(.top, 18)
            .padding(.bottom, 120)
        }
        .background(MJTheme.cartonCream.ignoresSafeArea())
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
    }
}
