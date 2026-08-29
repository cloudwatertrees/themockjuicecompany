import SwiftUI

struct ResultsView: View {
    let viewModel: QuizViewModel
    @Bindable var progress: UserProgress
    let onDismiss: () -> Void
    let onRetry: () -> Void

    @State private var gaugeProgress: Double = 0
    @State private var showContent: Bool = false
    @State private var celebrationTrigger: Int = 0

    private var passed: Bool { viewModel.passed }

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(spacing: 28) {
                Spacer(minLength: 40)
                mascotSection
                gaugeSection
                scoreBreakdown
                if case .mockTest = viewModel.sessionKind {
                    mockTestBreakdownSection
                }
                actionButtons
                Spacer(minLength: 60)
            }
            .padding(.horizontal, 24)
        }
        .background(MJTheme.cartonCream.ignoresSafeArea())
        .onAppear {
            withAnimation(.spring(response: 1.0, dampingFraction: 0.7).delay(0.3)) {
                gaugeProgress = Double(viewModel.scorePercentage) / 100.0
            }
            withAnimation(.spring(response: 0.5).delay(0.2)) {
                showContent = true
            }
            celebrationTrigger += 1
        }
    }

    private var mascotSection: some View {
        VStack(spacing: 12) {
            AppLogoView(width: 100, height: 100)

            Text(passed ? "well done!" : "keep going!")
                .font(.mjRounded(.largeTitle, weight: .black))
                .tracking(-0.5)
                .textCase(.lowercase)
                .foregroundStyle(passed ? MJTheme.spring : MJTheme.cardinal)

            Text(subtitleText)
                .font(.mjRounded(.body, weight: .bold))
                .tracking(-0.2)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest.opacity(0.6))
        }
        .opacity(showContent ? 1 : 0)
        .offset(y: showContent ? 0 : 20)
    }

    private var subtitleText: String {
        switch viewModel.sessionKind {
        case .category:
            return passed ? "you smashed that category" : "practice makes perfect"
        case .mockTest:
            return passed ? "you reached the theory pass mark" : "review your weak areas and try again"
        case .flaggedReview:
            return passed ? "your flagged set is looking sharp" : "keep chipping away at these"
        }
    }

    private var gaugeSection: some View {
        ZStack {
            Circle()
                .stroke(MJTheme.locked.opacity(0.4), lineWidth: 14)
                .frame(width: 180, height: 180)

            Circle()
                .trim(from: 0, to: gaugeProgress)
                .stroke(
                    passed
                    ? LinearGradient(colors: [MJTheme.spring, MJTheme.spring.opacity(0.7)], startPoint: .topLeading, endPoint: .bottomTrailing)
                    : LinearGradient(colors: [MJTheme.cardinal, MJTheme.cardinal.opacity(0.7)], startPoint: .topLeading, endPoint: .bottomTrailing),
                    style: StrokeStyle(lineWidth: 14, lineCap: .round)
                )
                .frame(width: 180, height: 180)
                .rotationEffect(.degrees(-90))

            VStack(spacing: 4) {
                Text("\(viewModel.scorePercentage)%")
                    .font(.mjRounded(size: 48, weight: .black))
                    .tracking(-1)
                    .foregroundStyle(passed ? MJTheme.spring : MJTheme.cardinal)

                Text(gaugeCaption)
                    .font(.mjRounded(.caption, weight: .heavy))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest.opacity(0.5))
            }
        }
        .padding(.vertical, 8)
    }

    private var gaugeCaption: String {
        switch viewModel.sessionKind {
        case .category, .flaggedReview:
            return "score"
        case .mockTest:
            return "\(viewModel.correctCount)/\(viewModel.questions.count)"
        }
    }

    private var scoreBreakdown: some View {
        VStack(spacing: 12) {
            HStack(spacing: 16) {
                scoreCard(icon: "checkmark.circle.fill", value: "\(viewModel.correctCount)", label: "correct", color: MJTheme.spring)
                scoreCard(icon: "xmark.circle.fill", value: "\(max(0, viewModel.answeredCount - viewModel.correctCount))", label: "wrong", color: MJTheme.cardinal)
            }

            HStack(spacing: 16) {
                scoreCard(icon: "checkmark.seal.fill", value: passStatusValue, label: passStatusLabel, color: passed ? MJTheme.spring : MJTheme.cardinal)
                scoreCard(icon: "flame.fill", value: "\(progress.currentStreak)", label: "streak", color: MJTheme.bee)
            }
        }
        .opacity(showContent ? 1 : 0)
        .offset(y: showContent ? 0 : 15)
    }

    private var passStatusValue: String {
        switch viewModel.sessionKind {
        case .category, .flaggedReview:
            return passed ? "pass" : "retry"
        case .mockTest:
            return "\(viewModel.passMark)"
        }
    }

    private var passStatusLabel: String {
        switch viewModel.sessionKind {
        case .category, .flaggedReview:
            return "status"
        case .mockTest:
            return "pass mark"
        }
    }

    private func scoreCard(icon: String, value: String, label: String, color: Color) -> some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 22, weight: .bold))
                .foregroundStyle(color)

            Text(value)
                .font(.mjRounded(.title2, weight: .black))
                .tracking(-0.3)
                .foregroundStyle(MJTheme.deepForest)

            Text(label)
                .font(.mjRounded(.caption, weight: .heavy))
                .tracking(-0.2)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest.opacity(0.5))
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 18)
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(MJTheme.innocentWhite)
                .shadow(color: MJTheme.deepForest.opacity(0.06), radius: 6, y: 3)
        )
    }

    private var mockTestBreakdownSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("subcategory breakdown")
                .font(.mjRounded(.headline, weight: .black))
                .tracking(-0.2)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest)
                .frame(maxWidth: .infinity, alignment: .leading)

            ForEach(viewModel.mockTestBreakdown()) { item in
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text(item.subcategory.rawValue)
                            .font(.mjRounded(.subheadline, weight: .black))
                            .tracking(-0.2)
                            .textCase(.lowercase)
                            .foregroundStyle(MJTheme.deepForest)
                        Spacer()
                        Text("\(item.correct)/\(item.total)")
                            .font(.mjRounded(.caption, weight: .black))
                            .foregroundStyle(item.accuracy >= 0.7 ? MJTheme.spring : MJTheme.cardinal)
                    }

                    LiquidProgressBar(progress: item.accuracy, height: 8, foregroundColor: item.accuracy >= 0.7 ? MJTheme.spring : MJTheme.cardinal)
                }
                .padding(14)
                .background(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .fill(MJTheme.innocentWhite)
                        .shadow(color: MJTheme.deepForest.opacity(0.06), radius: 6, y: 3)
                )
            }
        }
        .opacity(showContent ? 1 : 0)
    }

    private var actionButtons: some View {
        VStack(spacing: 12) {
            Button {
                onDismiss()
            } label: {
                Text(casePrimaryActionTitle)
                    .font(.mjRounded(.title3, weight: .black))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.innocentWhite)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 18)
                    .background(
                        RoundedRectangle(cornerRadius: 20, style: .continuous)
                            .fill(MJTheme.cardinal)
                    )
                    .shadow(color: MJTheme.cardinal.opacity(0.3), radius: 12, y: 6)
            }
            .sensoryFeedback(.impact(weight: .heavy), trigger: celebrationTrigger)

            if case .category = viewModel.sessionKind, !passed {
                Button {
                    onRetry()
                } label: {
                    Text("try again")
                        .font(.mjRounded(.title3, weight: .black))
                        .tracking(-0.2)
                        .textCase(.lowercase)
                        .foregroundStyle(MJTheme.cardinal)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 18)
                        .background(
                            RoundedRectangle(cornerRadius: 20, style: .continuous)
                                .stroke(MJTheme.cardinal, lineWidth: 2.5)
                        )
                }
            }
        }
        .opacity(showContent ? 1 : 0)
    }

    private var casePrimaryActionTitle: String {
        switch viewModel.sessionKind {
        case .category, .flaggedReview:
            return "continue"
        case .mockTest:
            return "review answers later"
        }
    }
}
