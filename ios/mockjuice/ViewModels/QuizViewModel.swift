import Foundation

@Observable
@MainActor
final class QuizViewModel {
    let sessionKind: QuizSessionKind
    let progress: UserProgress

    var questions: [Question]
    var currentIndex: Int
    var selectedAnswer: Int? = nil
    var isAnswerRevealed: Bool = false
    var isComplete: Bool = false
    var showExplanation: Bool = false
    var timeRemaining: TimeInterval = 57 * 60

    /// Results for *this* session only, keyed by item code. Kept separate from
    /// the persisted lifetime record so the score shown at the end reflects what
    /// the user just did, not their whole history with those questions.
    private var sessionResults: [String: Bool] = [:]
    /// Indices already counted as shown, so re-rendering never double-counts.
    private var markedShownIndices: Set<Int> = []
    nonisolated(unsafe) private var timer: Timer?

    var correctCount: Int { sessionResults.values.filter { $0 }.count }

    var answeredCount: Int { sessionResults.count }

    var currentQuestion: Question? {
        guard currentIndex >= 0, currentIndex < questions.count else { return nil }
        return questions[currentIndex]
    }

    var category: QuizCategory? {
        switch sessionKind {
        case .category(let category, _):
            return category
        case .mockTest, .flaggedReview:
            return nil
        }
    }

    var selectionMode: QuizSelectionMode? {
        switch sessionKind {
        case .category(_, let mode):
            return mode
        case .mockTest, .flaggedReview:
            return nil
        }
    }

    var progressValue: Double {
        guard !questions.isEmpty else { return 0 }
        return Double(min(answeredCount, questions.count)) / Double(questions.count)
    }

    var scorePercentage: Int {
        let total = max(questions.count, 1)
        return Int((Double(correctCount) / Double(total)) * 100)
    }

    var passMark: Int {
        switch sessionKind {
        case .category, .flaggedReview:
            return max(1, Int(Double(questions.count) * 0.5))
        case .mockTest:
            return 43
        }
    }

    var passed: Bool {
        switch sessionKind {
        case .category, .flaggedReview:
            return scorePercentage >= 50
        case .mockTest:
            return correctCount >= passMark
        }
    }

    var titleText: String {
        switch sessionKind {
        case .category(let category, _):
            return category.title
        case .mockTest:
            return "mock test"
        case .flaggedReview:
            return "flagged questions"
        }
    }

    var showsExplanationDuringFlow: Bool {
        switch sessionKind {
        case .category, .flaggedReview:
            return true
        case .mockTest:
            return false
        }
    }

    var formattedTimeRemaining: String {
        let minutes = Int(timeRemaining) / 60
        let seconds = Int(timeRemaining) % 60
        return String(format: "%02d:%02d", minutes, seconds)
    }

    /// True when this session picked up an in-progress sequence rather than
    /// generating a new one.
    private(set) var didResume: Bool = false

    init(sessionKind: QuizSessionKind, progress: UserProgress) {
        self.sessionKind = sessionKind
        self.progress = progress

        switch sessionKind {
        case .category(let category, let mode):
            let prepared = QuizViewModel.prepare(category: category, mode: mode, progress: progress)
            self.questions = prepared.questions
            self.currentIndex = prepared.startIndex
            self.sessionResults = prepared.results
            self.didResume = prepared.didResume
        case .mockTest:
            self.questions = QuestionSequencer.mockTestQuestions()
            self.currentIndex = 0
            startMockTimer()
        case .flaggedReview:
            self.questions = progress.flaggedQuestions().shuffled()
            self.currentIndex = 0
        }
    }

    deinit {
        timer?.invalidate()
    }

    // MARK: - Question lifecycle

    /// Called by the view when a question lands on screen. Records the "shown"
    /// tally that the minimum-spacing rule is measured against.
    func onQuestionAppear() {
        guard let question = currentQuestion, !markedShownIndices.contains(currentIndex) else { return }
        markedShownIndices.insert(currentIndex)
        progress.markShown(item: question.item)
    }

    func isQuestionFlagged(_ question: Question) -> Bool {
        progress.isFlagged(item: question.item)
    }

    func toggleFlag() {
        guard let question = currentQuestion else { return }
        progress.toggleFlag(item: question.item)
    }

    func selectAnswer(_ index: Int) {
        guard selectedAnswer == nil, let question = currentQuestion else { return }
        selectedAnswer = index
        isAnswerRevealed = true
        showExplanation = true

        let isCorrect = index == question.correctIndex
        sessionResults[question.item] = isCorrect
        progress.recordAnswer(item: question.item, selectedIndex: index, isCorrect: isCorrect)
    }

    func nextQuestion() {
        selectedAnswer = nil
        isAnswerRevealed = false
        showExplanation = false

        if currentIndex + 1 < questions.count {
            currentIndex += 1
            persistSessionState()
        } else {
            finishSession()
        }
    }

    func submitMockTest() {
        finishSession()
    }

    /// Starts the category over with a (possibly different) mode. Switching
    /// mode discards the stored sequence and builds a fresh one.
    func restartSession(mode: QuizSelectionMode) {
        guard case .category(let category, _) = sessionKind else { return }
        progress.clearSession(for: category)

        let prepared = QuizViewModel.prepare(category: category, mode: mode, progress: progress, allowResume: false)
        questions = prepared.questions
        currentIndex = prepared.startIndex
        sessionResults = [:]
        markedShownIndices = []
        didResume = false
        selectedAnswer = nil
        isAnswerRevealed = false
        isComplete = false
        showExplanation = false
    }

    func mockTestBreakdown() -> [MockTestBreakdown] {
        let grouped = Dictionary(grouping: questions, by: \.subcategory)
        return grouped.keys.sorted { $0.rawValue < $1.rawValue }.map { subcategory in
            let items = grouped[subcategory] ?? []
            let correct = items.filter { sessionResults[$0.item] == true }.count
            return MockTestBreakdown(subcategory: subcategory, total: items.count, correct: correct)
        }
    }

    // MARK: - Session completion

    private func finishSession() {
        guard !isComplete else { return }
        timer?.invalidate()
        timer = nil
        isComplete = true

        switch sessionKind {
        case .category(let category, _):
            // Finished sequences are cleared so the next visit starts fresh.
            progress.clearSession(for: category)
            let mastery = Int(progress.masteryScore(for: category) * 100)
            progress.completeNode(.theory, score: max(progress.score(for: .theory), mastery))
            progress.incrementDailyCompleted()
        case .mockTest:
            let score = Int((Double(correctCount) / Double(max(questions.count, 1))) * 100)
            progress.completeNode(.mockTest, score: max(progress.score(for: .mockTest), score))
            progress.mockTestHistory.append(correctCount)
            progress.incrementDailyCompleted()
        case .flaggedReview:
            progress.incrementDailyCompleted()
        }

        progress.saveNow()
    }

    private func startMockTimer() {
        timer = Timer.scheduledTimer(withTimeInterval: 1, repeats: true) { [weak self] _ in
            Task { @MainActor in
                guard let self else { return }
                if self.timeRemaining > 0 {
                    self.timeRemaining -= 1
                } else {
                    self.finishSession()
                }
            }
        }
    }

    /// Persists the exact sequence plus the cursor, so a resume replays the same
    /// order rather than reshuffling.
    private func persistSessionState() {
        guard case .category(let category, let mode) = sessionKind else { return }
        // Flagged review and mock test sessions never resume mid-way — no
        // sequence to persist for them.
        progress.saveSession(
            items: questions.map(\.item),
            nextIndex: currentIndex,
            mode: mode,
            for: category
        )
    }

    // MARK: - Sequence preparation

    private struct PreparedSession {
        let questions: [Question]
        let startIndex: Int
        let results: [String: Bool]
        let didResume: Bool
    }

    private static func prepare(
        category: QuizCategory,
        mode: QuizSelectionMode,
        progress: UserProgress,
        allowResume: Bool = true
    ) -> PreparedSession {
        // Resume only when the stored sequence was built for this same mode.
        if allowResume,
           let state = progress.sessionState(for: category),
           state.mode == mode,
           state.isResumable {
            let restored = state.orderedItems.compactMap { TheoryQuestionBank.question(item: $0) }
            if !restored.isEmpty {
                let startIndex = min(state.nextIndex, restored.count - 1)
                // Re-derive what was already answered from the persisted records
                // so the in-session score picks up where it left off.
                var results: [String: Bool] = [:]
                for question in restored.prefix(startIndex) {
                    let record = progress.record(for: question.item)
                    if record.answered {
                        results[question.item] = record.answeredCorrectly
                    }
                }
                return PreparedSession(
                    questions: restored,
                    startIndex: startIndex,
                    results: results,
                    didResume: true
                )
            }
        }

        let pool = category.questions
        let sequence = QuestionSequencer.sequence(
            questions: pool,
            mode: mode,
            accuracyForItem: { progress.accuracy(forItem: $0) },
            recentlyShown: progress.recentlyShownItems
        )
        return PreparedSession(questions: sequence, startIndex: 0, results: [:], didResume: false)
    }
}
