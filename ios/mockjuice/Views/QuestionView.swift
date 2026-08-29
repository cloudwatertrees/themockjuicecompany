import SwiftUI

struct QuestionView: View {
    let sessionKind: QuizSessionKind
    @Bindable var progress: UserProgress
    @Environment(\.dismiss) private var dismiss
    @State private var viewModel: QuizViewModel

    init(sessionKind: QuizSessionKind, progress: UserProgress) {
        self.sessionKind = sessionKind
        self.progress = progress
        self._viewModel = State(initialValue: QuizViewModel(sessionKind: sessionKind, progress: progress))
    }

    var body: some View {
        ZStack {
            MJTheme.cartonCream.ignoresSafeArea()

            if viewModel.isComplete {
                ResultsView(
                    viewModel: viewModel,
                    progress: progress,
                    onDismiss: { dismiss() },
                    onRetry: {
                        if case .category(_, let mode) = sessionKind {
                            viewModel.restartSession(mode: mode)
                        }
                    }
                )
            } else {
                questionContent
            }
        }
    }

    private var questionContent: some View {
        VStack(spacing: 0) {
            headerBar

            ScrollView(.vertical, showsIndicators: false) {
                VStack(spacing: 24) {
                    questionCard
                    optionsSection
                    if viewModel.isAnswerRevealed && viewModel.showsExplanationDuringFlow {
                        explanationCard
                    }
                }
                .padding(.horizontal, 20)
                .padding(.top, 16)
                .padding(.bottom, 120)
            }

            bottomAction
        }
        .task(id: viewModel.currentIndex) {
            viewModel.onQuestionAppear()
        }
    }

    private var headerBar: some View {
        VStack(spacing: 10) {
            HStack {
                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(MJTheme.deepForest)
                        .frame(width: 44, height: 44)
                }

                Spacer()

                if case .mockTest = sessionKind {
                    Text(viewModel.formattedTimeRemaining)
                        .font(.mjRounded(.caption, weight: .black))
                        .foregroundStyle(MJTheme.deepForest)
                        .frame(minWidth: 52)
                } else {
                    Text("\(min(viewModel.currentIndex + 1, viewModel.questions.count))/\(viewModel.questions.count)")
                        .font(.mjRounded(.subheadline, weight: .black))
                        .tracking(-0.2)
                        .foregroundStyle(MJTheme.deepForest)
                }
            }
            .padding(.horizontal, 20)

            solidProgressBar
                .padding(.horizontal, 20)
        }
        .padding(.top, 12)
        .padding(.bottom, 16)
        .frame(maxWidth: .infinity)
        .background(MJTheme.innocentWhite)
    }

    /// A flat, solid-fill bar — deliberately not the wavy `LiquidProgressBar`
    /// used elsewhere, per the design call for this header to read as a plain,
    /// sturdy progress indicator. Sits on the light header surface.
    private var solidProgressBar: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Capsule()
                    .fill(MJTheme.locked.opacity(0.45))

                Capsule()
                    .fill(MJTheme.cardinal)
                    .frame(width: max(geo.size.width * min(max(viewModel.progressValue, 0), 1), 12))
                    .animation(.easeOut(duration: 0.3), value: viewModel.progressValue)
            }
        }
        .frame(height: 12)
    }

    private var topicBadge: some View {
        HStack(spacing: 6) {
            if let iconAsset = topicIconAsset {
                TheoryIconGlyph(iconAsset: iconAsset, size: 18)
            } else {
                Image(systemName: "checklist.checked")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundStyle(MJTheme.spring)
            }

            Text(topicTitle)
                .font(.mjRounded(.subheadline, weight: .heavy))
                .tracking(-0.2)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.spring)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(
            Capsule()
                .fill(MJTheme.spring.opacity(0.15))
                .overlay(
                    Capsule()
                        .stroke(MJTheme.spring, lineWidth: 1)
                )
        )
    }

    @ViewBuilder
    private var flagButton: some View {
        if let question = viewModel.currentQuestion {
            Button {
                viewModel.toggleFlag()
            } label: {
                Image(systemName: viewModel.isQuestionFlagged(question) ? "flag.fill" : "flag")
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(viewModel.isQuestionFlagged(question) ? MJTheme.bee : MJTheme.deepForest.opacity(0.3))
                    .frame(width: 44, height: 44)
            }
            .buttonStyle(.plain)
            .sensoryFeedback(.selection, trigger: viewModel.isQuestionFlagged(question))
        }
    }

    /// Resolves to the same icon asset used on the theory list, so the
    /// category shown here always matches the app's iconography system.
    /// Driven by the *current question's* own subcategory rather than the
    /// session, so mixed sessions ("all categories", "videos", mock tests)
    /// still label each question accurately.
    private var topicIconAsset: String? {
        viewModel.currentQuestion?.subcategory.lineArtIconAsset
    }

    private var topicTitle: String {
        viewModel.currentQuestion?.subcategory.rawValue ?? viewModel.titleText
    }

    private var questionCard: some View {
        VStack(alignment: .leading, spacing: 16) {
            Color.clear.frame(height: 4)

            if let question = viewModel.currentQuestion {
                // Video questions lead with the clip, since the stem refers to it.
                if let videoFileName = question.videoFileName {
                    QuestionVideoPlayerView(fileName: videoFileName)
                }

                Text(question.text)
                    .font(.mjRounded(.title3, weight: .black))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest)
                    .multilineTextAlignment(.leading)
                    .lineSpacing(6)
                    .frame(maxWidth: .infinity, alignment: .leading)

                // Only rendered when the question actually references an image.
                // There is deliberately no placeholder for the 555 questions
                // that have none — the image slot stays completely absent.
                if let stemImageName = question.stemImageName {
                    QuestionImageView(fileName: stemImageName)
                }
            }
        }
        .padding(20)
        .padding(.top, 12)
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(MJTheme.innocentWhite)
                .overlay(
                    RoundedRectangle(cornerRadius: 24, style: .continuous)
                        .stroke(MJTheme.deepForest.opacity(0.08), lineWidth: 1)
                )
        )
        .overlay(alignment: .topLeading) {
            topicBadge
                .padding(.top, 12)
                .padding(.leading, 16)
        }
        .overlay(alignment: .topTrailing) {
            flagButton
                .padding(.top, 4)
                .padding(.trailing, 8)
        }
        .shadow(color: MJTheme.deepForest.opacity(0.06), radius: 10, x: 0, y: 4)
    }

    private var optionsSection: some View {
        VStack(spacing: 12) {
            if let question = viewModel.currentQuestion {
                ForEach(Array(question.options.enumerated()), id: \.offset) { index, option in
                    optionButton(index: index, option: option, question: question)
                }
            }
        }
    }

    private func optionButton(index: Int, option: QuestionOption, question: Question) -> some View {
        let isSelected = viewModel.selectedAnswer == index
        let isCorrectAnswer = index == question.correctIndex
        let showResult = viewModel.isAnswerRevealed

        let bgColor: Color = {
            if !showResult { return MJTheme.innocentWhite }
            if isCorrectAnswer { return MJTheme.spring.opacity(0.18) }
            if isSelected && !isCorrectAnswer { return MJTheme.cardinal.opacity(0.15) }
            return MJTheme.innocentWhite.opacity(0.6)
        }()

        let borderColor: Color = {
            if !showResult { return isSelected ? MJTheme.spring : MJTheme.spring.opacity(0.3) }
            if isCorrectAnswer { return MJTheme.spring }
            if isSelected && !isCorrectAnswer { return MJTheme.cardinal }
            return MJTheme.locked.opacity(0.4)
        }()

        return Button {
            viewModel.selectAnswer(index)
        } label: {
            HStack(spacing: 14) {
                ZStack {
                    if showResult {
                        Circle()
                            .stroke(borderColor, lineWidth: 2.5)
                            .frame(width: 32, height: 32)
                    } else {
                        Circle()
                            .fill(MJTheme.deepForest)
                            .frame(width: 32, height: 32)
                    }

                    if showResult && isCorrectAnswer {
                        Image(systemName: "checkmark")
                            .font(.system(size: 14, weight: .black))
                            .foregroundStyle(MJTheme.spring)
                    } else if showResult && isSelected && !isCorrectAnswer {
                        Image(systemName: "xmark")
                            .font(.system(size: 14, weight: .black))
                            .foregroundStyle(MJTheme.cardinal)
                    } else {
                        // Sits on the solid `deepForest` circle above, so the
                        // white letter is the correct on-dark-surface token.
                        Text(String(Character(UnicodeScalar(65 + index)!)))
                            .font(.mjRounded(.subheadline, weight: .black))
                            .foregroundStyle(MJTheme.innocentWhite)
                    }
                }

                // Some answers are a sign/diagram rather than words, so the
                // image sits in the same slot the label would occupy.
                if let imageName = option.imageName {
                    QuestionOptionImageView(fileName: imageName)
                }

                if !option.text.isEmpty {
                    Text(option.text)
                        .font(.mjRounded(.body, weight: .heavy))
                        .tracking(-0.2)
                        .textCase(.lowercase)
                        .foregroundStyle(MJTheme.deepForest)
                        .multilineTextAlignment(.leading)
                }

                Spacer()
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 16)
            .background(
                RoundedRectangle(cornerRadius: 24, style: .continuous)
                    .fill(bgColor)
                    .overlay(
                        RoundedRectangle(cornerRadius: 24, style: .continuous)
                            .stroke(borderColor, lineWidth: 2)
                    )
            )
            .shadow(color: MJTheme.deepForest.opacity(0.06), radius: 8, x: 0, y: 4)
        }
        .buttonStyle(.plain)
        .disabled(viewModel.isAnswerRevealed)
        .sensoryFeedback(.impact(weight: .medium), trigger: viewModel.selectedAnswer)
    }

    private var explanationCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: isCurrentAnswerCorrect ? "checkmark.circle.fill" : "info.circle.fill")
                    .font(.system(size: 18, weight: .bold))
                    .foregroundStyle(isCurrentAnswerCorrect ? MJTheme.spring : MJTheme.cardinal)

                Text(isCurrentAnswerCorrect ? "correct!" : "not quite")
                    .font(.mjRounded(.headline, weight: .black))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(isCurrentAnswerCorrect ? MJTheme.spring : MJTheme.cardinal)
            }

            if let question = viewModel.currentQuestion {
                Text(question.explanation)
                    .font(.mjRounded(.subheadline, weight: .semibold))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest.opacity(0.8))
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(isCurrentAnswerCorrect ? MJTheme.spring.opacity(0.1) : MJTheme.cardinal.opacity(0.08))
        )
        .transition(.move(edge: .bottom).combined(with: .opacity))
        .animation(.spring(response: 0.4), value: viewModel.isAnswerRevealed)
    }

    private var bottomAction: some View {
        Group {
            if case .mockTest = sessionKind, !viewModel.isAnswerRevealed {
                Button {
                    viewModel.submitMockTest()
                } label: {
                    Text("submit test")
                        .font(.mjRounded(.headline, weight: .black))
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
                .padding(.horizontal, 20)
                .padding(.bottom, 36)
            } else if viewModel.isAnswerRevealed {
                Button {
                    withAnimation(.spring(response: 0.4)) {
                        viewModel.nextQuestion()
                    }
                } label: {
                    Text(nextButtonTitle)
                        .font(.mjRounded(.title3, weight: .black))
                        .tracking(-0.2)
                        .textCase(.lowercase)
                        .foregroundStyle(MJTheme.innocentWhite)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 18)
                        .background(
                            RoundedRectangle(cornerRadius: 20, style: .continuous)
                                .fill(isCurrentAnswerCorrect ? MJTheme.spring : MJTheme.cardinal)
                        )
                        .shadow(color: (isCurrentAnswerCorrect ? MJTheme.spring : MJTheme.cardinal).opacity(0.3), radius: 12, y: 6)
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 36)
                .sensoryFeedback(.impact(weight: .heavy), trigger: viewModel.currentIndex)
            }
        }
    }

    private var isCurrentAnswerCorrect: Bool {
        guard let selectedAnswer = viewModel.selectedAnswer, let question = viewModel.currentQuestion else { return false }
        return selectedAnswer == question.correctIndex
    }

    private var nextButtonTitle: String {
        viewModel.currentIndex + 1 == viewModel.questions.count ? "finish" : "continue"
    }
}
