import SwiftUI

struct TheorySubcategorySelectionView: View {
    @Bindable var progress: UserProgress
    let onSelect: (QuizCategory) -> Void
    @Environment(\.dismiss) private var dismiss

    /// Weakest first, mirroring the Progress tab's category mastery ordering.
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

    /// "all categories" and "videos" first, mirroring the Progress tab, then the
    /// 14 real subcategories sorted weakest-first. All 16 rows are playable and
    /// share the same progress records.
    private var rows: [TheoryRowItem] {
        let pinned: [QuizCategory] = [.all, .videos]
        let categories = pinned + sortedSubcategories.map { QuizCategory.standard($0) }

        return categories.map { category in
            let stats = progress.progress(for: category)
            return TheoryRowItem(
                id: category.id,
                iconAsset: category.iconAsset,
                title: category.title,
                mastery: progress.masteryScore(for: category),
                answered: stats.answeredCount,
                total: category.questionCount,
                category: category
            )
        }
    }

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .leading, spacing: 10) {
                header
                list
            }
            .padding(.horizontal, 20)
            .padding(.top, 8)
            .padding(.bottom, 150)
        }
        .background(MJTheme.cartonCream.ignoresSafeArea())
        .navigationBarHidden(true)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 0) {
            Button {
                dismiss()
            } label: {
                Image(systemName: "chevron.left")
                    .font(.system(size: 16, weight: .black))
                    .foregroundStyle(MJTheme.deepForest)
                    .frame(width: 36, height: 36)
                    .background(MJTheme.innocentWhite, in: Circle())
                    .overlay {
                        Circle()
                            .stroke(MJTheme.deepForest.opacity(0.08), lineWidth: 1)
                    }
            }
            .buttonStyle(.plain)
            .contentShape(Circle())

            Text("theory")
                .font(.mjRounded(size: 32, weight: .black))
                .tracking(-0.5)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest)
                .padding(.top, 16)

            Text("weakest first")
                .font(.mjRounded(.footnote, weight: .semibold))
                .tracking(-0.2)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest.opacity(0.45))
                .padding(.top, 4)
        }
    }

    private var list: some View {
        VStack(spacing: 6) {
            ForEach(Array(rows.enumerated()), id: \.element.id) { index, row in
                TheoryCategoryRow(item: row, cascadeIndex: index) {
                    onSelect(row.category)
                }
            }
        }
    }
}

private struct TheoryRowItem {
    let id: String
    let iconAsset: String
    let title: String
    let mastery: Double
    let answered: Int
    let total: Int
    let category: QuizCategory
}

/// A single "menu item" row: a large solid-color icon circle on the left, the
/// category name next to it, and the mastery percentage plus a small chevron
/// on the far right. No card, no colored background — just the cream screen.
private struct TheoryCategoryRow: View {
    let item: TheoryRowItem
    let cascadeIndex: Int
    let action: () -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var isPressed: Bool = false
    @State private var hasAppeared: Bool = false

    private var isComplete: Bool { item.mastery >= 0.999 }

    var body: some View {
        Button {
            press()
        } label: {
            HStack(spacing: 14) {
                iconGlyph

                VStack(alignment: .leading, spacing: 2) {
                    Text(item.title)
                        .font(.mjRounded(size: 16, weight: .heavy))
                        .tracking(-0.3)
                        .textCase(.lowercase)
                        .foregroundStyle(isComplete ? MJTheme.deepForest.opacity(0.4) : MJTheme.deepForest)
                        .lineLimit(2)
                        .minimumScaleFactor(0.8)
                        .multilineTextAlignment(.leading)

                    Text("\(item.answered)/\(item.total)")
                        .font(.mjRounded(size: 12, weight: .bold))
                        .tracking(-0.2)
                        .foregroundStyle(MJTheme.deepForest.opacity(0.35))
                }
                .frame(maxWidth: .infinity, alignment: .leading)

                Text("\(Int((item.mastery * 100).rounded()))%")
                    .font(.mjRounded(size: 14, weight: .black))
                    .foregroundStyle(MJTheme.deepForest.opacity(0.4))

                Image(systemName: "chevron.right")
                    .font(.system(size: 12, weight: .black))
                    .foregroundStyle(MJTheme.deepForest.opacity(0.25))
            }
            .padding(.vertical, 10)
            .contentShape(.rect)
        }
        .buttonStyle(.plain)
        .scaleEffect(isPressed ? 0.97 : 1)
        .animation(.spring(response: 0.24, dampingFraction: 0.6), value: isPressed)
        .opacity(hasAppeared ? 1 : 0)
        .offset(y: hasAppeared ? 0 : 6)
        .onAppear {
            guard !hasAppeared else { return }
            if reduceMotion {
                hasAppeared = true
                return
            }
            withAnimation(.easeOut(duration: 0.28).delay(Double(cascadeIndex) * 0.02)) {
                hasAppeared = true
            }
        }
        .sensoryFeedback(.impact(weight: .light), trigger: isPressed)
        .accessibilityLabel("\(item.title), \(item.answered) of \(item.total) answered, \(Int((item.mastery * 100).rounded())) percent mastery")
    }

    /// The icon itself: dark forest green outline, fully transparent
    /// background, no circle/badge behind it. Resolved through the shared
    /// `TheoryIconGlyph` so this list and the quiz screen never disagree on
    /// what a category looks like.
    private var iconGlyph: some View {
        TheoryIconGlyph(iconAsset: item.iconAsset)
            .opacity(isComplete ? 0.45 : 1)
    }

    private func press() {
        guard item.total > 0 else { return }
        isPressed = true
        Task { @MainActor in
            try? await Task.sleep(for: .milliseconds(80))
            isPressed = false
            action()
        }
    }
}

