import SwiftUI

/// Unified data screen: readiness, learner stats, streak, daily goal,
/// category mastery, review queues, achievements and test day tips.
struct ProgressTabView: View {
    @Bindable var progress: UserProgress

    private var flaggedBySubcategory: [(TheorySubcategory, [Question])] {
        TheorySubcategory.allCases.compactMap { subcategory in
            let items = progress.flaggedQuestions(for: subcategory)
            return items.isEmpty ? nil : (subcategory, items)
        }
    }

    private var incorrectBySubcategory: [(TheorySubcategory, [Question])] {
        TheorySubcategory.allCases.compactMap { subcategory in
            let items = progress.incorrectQuestions(for: subcategory)
            return items.isEmpty ? nil : (subcategory, items)
        }
    }

    private var sortedSubcategories: [TheorySubcategory] {
        TheorySubcategory.allCases.sorted { lhs, rhs in
            let left = progress.masteryScore(for: lhs)
            let right = progress.masteryScore(for: rhs)
            if left == right {
                return lhs.rawValue < rhs.rawValue
            }
            return left < right
        }
    }

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(spacing: 14) {
                headerSection
                masterySection
                reviewQueueSection
                achievementsSection
            }
            .padding(.horizontal, 20)
            .padding(.top, 16)
            .padding(.bottom, 150)
        }
        .background(MJTheme.cartonCream.ignoresSafeArea())
    }

    // MARK: - Header

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("progress")
                .font(.mjRounded(.largeTitle, weight: .black))
                .tracking(-0.5)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest)

            Text("readiness, mastery and test day prep")
                .font(.mjRounded(.subheadline, weight: .bold))
                .tracking(-0.2)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest.opacity(0.5))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    // MARK: - Category mastery

    private var masterySection: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .firstTextBaseline) {
                Text("category mastery")
                    .font(.mjRounded(.headline, weight: .black))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest)

                Spacer()

                Text("weakest first")
                    .font(.mjRounded(.caption2, weight: .bold))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest.opacity(0.45))
            }

            genericMasteryRow(
                icon: "square.grid.2x2.fill",
                title: QuizCategory.all.title,
                score: progress.masteryScore(for: .all),
                answered: progress.progress(for: .all).answeredCount,
                total: QuizCategory.all.questionCount
            )

            genericMasteryRow(
                icon: "play.rectangle.fill",
                title: QuizCategory.videos.title,
                score: progress.masteryScore(for: .videos),
                answered: progress.progress(for: .videos).answeredCount,
                total: QuizCategory.videos.questionCount
            )

            ForEach(sortedSubcategories) { subcategory in
                masteryRow(subcategory)
            }
        }
    }

    private func masteryRow(_ subcategory: TheorySubcategory) -> some View {
        genericMasteryRow(
            icon: subcategory.icon,
            title: subcategory.rawValue,
            score: progress.masteryScore(for: subcategory),
            answered: progress.progress(for: subcategory).answeredCount,
            total: subcategory.questionCount
        )
    }

    private func genericMasteryRow(icon: String, title: String, score: Double, answered: Int, total: Int) -> some View {
        HStack(spacing: 14) {
            ZStack {
                Circle()
                    .fill(MJTheme.spring.opacity(0.15))
                    .frame(width: 40, height: 40)
                Image(systemName: icon)
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(MJTheme.spring)
            }

            VStack(alignment: .leading, spacing: 6) {
                HStack(alignment: .firstTextBaseline, spacing: 6) {
                    Text(title)
                        .font(.mjRounded(.subheadline, weight: .heavy))
                        .tracking(-0.2)
                        .textCase(.lowercase)
                        .foregroundStyle(MJTheme.deepForest)
                        .lineLimit(2)

                    Spacer(minLength: 0)

                    Text("\(answered)/\(total)")
                        .font(.mjRounded(.caption2, weight: .bold))
                        .foregroundStyle(MJTheme.deepForest.opacity(0.4))
                }

                LiquidProgressBar(
                    progress: score,
                    height: 8,
                    foregroundColor: masteryStatusColor(score: score, answered: answered),
                    backgroundColor: MJTheme.deepForest.opacity(0.12)
                )
            }

            Text("\(Int(score * 100))%")
                .font(.mjRounded(.caption, weight: .black))
                .foregroundStyle(MJTheme.deepForest.opacity(0.6))
                .frame(width: 42, alignment: .trailing)
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(MJTheme.innocentWhite)
                .shadow(color: MJTheme.deepForest.opacity(0.05), radius: 4, y: 2)
        )
    }

    /// Mastery is expressed with existing palette roles rather than an
    /// orphaned standard color: strong = `spring`, developing = `macaw`,
    /// needs work = `cardinal`, untouched = a faded neutral.
    private func masteryStatusColor(score: Double, answered: Int) -> Color {
        if answered == 0 {
            return MJTheme.deepForest.opacity(0.25)
        }
        if score >= 0.7 {
            return MJTheme.spring
        }
        if score >= 0.4 {
            return MJTheme.bee
        }
        return MJTheme.cardinal
    }

    // MARK: - Review queues

    @ViewBuilder
    private var reviewQueueSection: some View {
        if !flaggedBySubcategory.isEmpty || !incorrectBySubcategory.isEmpty {
            VStack(spacing: 14) {
                if !flaggedBySubcategory.isEmpty {
                    groupedSection(title: "flagged questions", groups: flaggedBySubcategory, accent: MJTheme.bee)
                }
                if !incorrectBySubcategory.isEmpty {
                    groupedSection(title: "incorrect answers", groups: incorrectBySubcategory, accent: MJTheme.cardinal)
                }
            }
        }
    }

    private func groupedSection(title: String, groups: [(TheorySubcategory, [Question])], accent: Color) -> some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(title)
                .font(.mjRounded(.headline, weight: .black))
                .tracking(-0.2)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest)

            ForEach(groups, id: \.0.id) { group in
                VStack(alignment: .leading, spacing: 10) {
                    HStack {
                        Label {
                            Text(group.0.rawValue)
                                .font(.mjRounded(.subheadline, weight: .black))
                                .tracking(-0.2)
                                .textCase(.lowercase)
                        } icon: {
                            Image(systemName: group.0.icon)
                        }
                        .foregroundStyle(MJTheme.deepForest)

                        Spacer()

                        Text("\(group.1.count)")
                            .font(.mjRounded(.caption, weight: .black))
                            .foregroundStyle(accent)
                    }

                    ForEach(group.1.prefix(3)) { question in
                        Text(question.text)
                            .font(.mjRounded(.caption, weight: .bold))
                            .tracking(-0.2)
                            .textCase(.lowercase)
                            .foregroundStyle(MJTheme.deepForest.opacity(0.7))
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.horizontal, 12)
                            .padding(.vertical, 10)
                            .background(RoundedRectangle(cornerRadius: 14, style: .continuous).fill(accent.opacity(0.08)))
                    }
                }
                .padding(14)
                .background(
                    RoundedRectangle(cornerRadius: 18, style: .continuous)
                        .fill(MJTheme.innocentWhite)
                        .shadow(color: MJTheme.deepForest.opacity(0.05), radius: 4, y: 2)
                )
            }
        }
    }

    // MARK: - Achievements

    private var achievementsSection: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("achievements")
                .font(.mjRounded(.headline, weight: .black))
                .tracking(-0.2)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest)

            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 14) {
                achievementBadge(icon: "flame.fill", label: "hot streak", earned: progress.currentStreak >= 3, color: MJTheme.bee)
                achievementBadge(icon: "bookmark.fill", label: "flagged finder", earned: !progress.flaggedQuestionIDs.isEmpty, color: MJTheme.cardinal)
                achievementBadge(icon: "trophy.fill", label: "halfway", earned: progress.completedNodes.count >= 3, color: MJTheme.spring)
                achievementBadge(icon: "brain.fill", label: "sharp mind", earned: progress.accuracy >= 0.8, color: MJTheme.cardinal)
                achievementBadge(icon: "checkmark.seal.fill", label: "mock ready", earned: (progress.nodeScores[JourneyNode.explore.id] ?? 0) >= 86, color: MJTheme.spring)
                achievementBadge(icon: "crown.fill", label: "ace driver", earned: progress.overallReadiness >= 0.85, color: MJTheme.bee)
            }
        }
    }

    private func achievementBadge(icon: String, label: String, earned: Bool, color: Color) -> some View {
        VStack(spacing: 8) {
            ZStack {
                Circle()
                    .fill(earned ? color.opacity(0.15) : MJTheme.locked.opacity(0.25))
                    .frame(width: 52, height: 52)

                Image(systemName: earned ? icon : "lock.fill")
                    .font(.system(size: 22, weight: .bold))
                    .foregroundStyle(earned ? color : MJTheme.deepForest.opacity(0.3))
            }

            Text(label)
                .font(.mjRounded(.caption2, weight: .heavy))
                .tracking(-0.2)
                .textCase(.lowercase)
                .foregroundStyle(earned ? MJTheme.deepForest : MJTheme.deepForest.opacity(0.35))
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(MJTheme.innocentWhite)
                .shadow(color: MJTheme.deepForest.opacity(0.05), radius: 4, y: 2)
        )
    }

}
