import Foundation

/// The app's progress store.
///
/// Everything is derived from one dictionary of `QuestionRecord` keyed by DVSA
/// item code. Categories — including "all categories" and "videos" — are read
/// models over that dictionary, never separate counters, so a question answered
/// inside "all categories" is immediately reflected in its own category and
/// vice versa. State is persisted to disk on every mutation.
@Observable
@MainActor
final class UserProgress {
    var completedNodes: Set<String> = []
    var nodeScores: [String: Int] = [:]
    var currentStreak: Int = 0
    var dailyGoal: Int = 5 {
        didSet { scheduleSave() }
    }
    var dailyCompleted: Int = 0
    /// Written through a `@Binding` by onboarding, so it persists via `didSet`
    /// rather than relying on a call site remembering to save.
    var hasCompletedOnboarding: Bool = false {
        didSet { scheduleSave() }
    }
    var questionRecords: [String: QuestionRecord] = [:]
    var sessionStates: [String: CategorySessionState] = [:]
    var recentlyShownItems: [String] = []
    var mockTestHistory: [Int] = []
    var targetTestDate: Date {
        didSet { scheduleSave() }
    }
    /// Gates the one-time hazard-clip download intro screen.
    var hasSeenVideoDownloadIntro: Bool = false {
        didSet { scheduleSave() }
    }
    /// Gates the one-time theory category intro modal.
    var hasSeenTheoryIntro: Bool = false {
        didSet { scheduleSave() }
    }
    /// Tracks which specific category info modals have been seen.
    var seenCategoryIntros: Set<String> = [] {
        didSet { scheduleSave() }
    }

    private var lastActivityDate: Date?
    private var dailyCompletedDate: Date?
    private var saveTask: Task<Void, Never>?
    /// Guards against writing to disk while the initial load is still applying.
    private var isLoading: Bool = false

    /// How many recently-shown item codes to remember for the spacing rule.
    /// A little more than the spacing window so it stays effective across
    /// back-to-back sessions.
    private static let recentHistoryLimit = 40

    init() {
        self.targetTestDate = Calendar.current.date(byAdding: .day, value: 21, to: Date()) ?? Date()
        load()
    }

    // MARK: - Persistence

    private func load() {
        isLoading = true
        let snapshot = ProgressStore.load()

        questionRecords = snapshot.questionRecords
        sessionStates = snapshot.sessionStates
        recentlyShownItems = snapshot.recentlyShownItems
        completedNodes = Set(snapshot.completedNodes)
        nodeScores = snapshot.nodeScores
        currentStreak = snapshot.currentStreak
        lastActivityDate = snapshot.lastActivityDate
        dailyGoal = snapshot.dailyGoal
        dailyCompleted = snapshot.dailyCompleted
        dailyCompletedDate = snapshot.dailyCompletedDate
        hasCompletedOnboarding = snapshot.hasCompletedOnboarding
        mockTestHistory = snapshot.mockTestHistory
        hasSeenVideoDownloadIntro = snapshot.hasSeenVideoDownloadIntro
        hasSeenTheoryIntro = snapshot.hasSeenTheoryIntro
        seenCategoryIntros = Set(snapshot.seenCategoryIntros)
        if let stored = snapshot.targetTestDate {
            targetTestDate = stored
        }

        normalizeDailyCounters()
        isLoading = false
    }

    /// Coalesces rapid mutations into a single write. Detached on purpose:
    /// encoding ~800 records and touching the filesystem has no business
    /// running on the main actor while the user is mid-question.
    private func scheduleSave() {
        guard !isLoading else { return }
        saveTask?.cancel()
        let snapshot = makeSnapshot()
        saveTask = Task.detached(priority: .utility) {
            try? await Task.sleep(for: .milliseconds(400))
            guard !Task.isCancelled else { return }
            ProgressStore.save(snapshot)
        }
    }

    /// Writes immediately — used when a session ends, so progress survives even
    /// if the app is killed straight after.
    func saveNow() {
        guard !isLoading else { return }
        saveTask?.cancel()
        ProgressStore.save(makeSnapshot())
    }

    private func makeSnapshot() -> ProgressSnapshot {
        ProgressSnapshot(
            questionRecords: questionRecords,
            sessionStates: sessionStates,
            recentlyShownItems: recentlyShownItems,
            completedNodes: Array(completedNodes),
            nodeScores: nodeScores,
            currentStreak: currentStreak,
            lastActivityDate: lastActivityDate,
            dailyGoal: dailyGoal,
            dailyCompleted: dailyCompleted,
            dailyCompletedDate: dailyCompletedDate,
            hasCompletedOnboarding: hasCompletedOnboarding,
            mockTestHistory: mockTestHistory,
            targetTestDate: targetTestDate,
            hasSeenVideoDownloadIntro: hasSeenVideoDownloadIntro,
            hasSeenTheoryIntro: hasSeenTheoryIntro,
            seenCategoryIntros: Array(seenCategoryIntros)
        )
    }

    /// Clears all learner progress — question records, streaks, mock-test
    /// history, journey nodes, everything — and wipes the on-device hazard
    /// clip cache so the download intro shows again on next topic tap.
    func resetAll() {
        questionRecords = [:]
        sessionStates = [:]
        recentlyShownItems = []
        completedNodes = []
        nodeScores = [:]
        currentStreak = 0
        lastActivityDate = nil
        dailyCompleted = 0
        dailyCompletedDate = nil
        mockTestHistory = []
        hasSeenVideoDownloadIntro = false
        hasSeenTheoryIntro = false
        seenCategoryIntros = []
        saveNow()

        // Wipe cached hazard clips so storage is reclaimed and the download
        // intro reappears after a reset, matching the fresh-slate intent.
        Task.detached(priority: .utility) {
            let dir = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("HazardClips", isDirectory: true)
            try? FileManager.default.removeItem(at: dir)
        }
    }

    // MARK: - Derived totals

    /// Total attempts ever made. Derived, so it can't drift from the records.
    var totalAttempted: Int {
        questionRecords.values.reduce(0) { $0 + $1.attempts }
    }

    var totalCorrect: Int {
        questionRecords.values.reduce(0) { $0 + $1.timesCorrect }
    }

    var accuracy: Double {
        let attempted = totalAttempted
        guard attempted > 0 else { return 0 }
        return Double(totalCorrect) / Double(attempted)
    }

    /// Distinct questions answered at least once.
    var answeredQuestionCount: Int {
        questionRecords.values.filter(\.answered).count
    }

    var overallProgress: Double {
        let total = JourneyNode.allCases.count
        guard total > 0 else { return 0 }
        return Double(completedNodes.count) / Double(total)
    }

    var overallReadiness: Double {
        let totalQuestions = TheoryQuestionBank.allQuestions.count
        guard totalQuestions > 0 else { return 0 }
        let coverage = Double(answeredQuestionCount) / Double(totalQuestions)
        return min(1, accuracy * 0.55 + coverage * 0.45)
    }

    var incorrectQuestionIDs: [String] {
        questionRecords.compactMap { key, record in
            record.answered && !record.answeredCorrectly ? key : nil
        }
    }

    var flaggedQuestionIDs: [String] {
        questionRecords.compactMap { key, record in record.flagged ? key : nil }
    }

    // MARK: - Journey nodes

    func isUnlocked(_ node: JourneyNode) -> Bool {
        guard let index = JourneyNode.allCases.firstIndex(of: node) else { return false }
        if index == 0 { return true }
        return completedNodes.contains(JourneyNode.allCases[index - 1].id)
    }

    func score(for node: JourneyNode) -> Int {
        nodeScores[node.id] ?? 0
    }

    func completeNode(_ node: JourneyNode, score: Int) {
        completedNodes.insert(node.id)
        nodeScores[node.id] = max(nodeScores[node.id] ?? 0, score)
        scheduleSave()
    }

    // MARK: - Recording answers

    func record(for item: String) -> QuestionRecord {
        questionRecords[item] ?? QuestionRecord()
    }

    /// Called when a question is put on screen, which is what the spacing rule
    /// is measured against.
    func markShown(item: String) {
        var record = record(for: item)
        record.timesShown += 1
        record.lastSeenAt = Date()
        questionRecords[item] = record

        recentlyShownItems.removeAll { $0 == item }
        recentlyShownItems.append(item)
        if recentlyShownItems.count > Self.recentHistoryLimit {
            recentlyShownItems.removeFirst(recentlyShownItems.count - Self.recentHistoryLimit)
        }
        scheduleSave()
    }

    /// Accumulates an attempt. Repeat attempts add to the tallies rather than
    /// overwriting them, so history is never lost.
    func recordAnswer(item: String, selectedIndex: Int, isCorrect: Bool) {
        var record = record(for: item)
        if isCorrect {
            record.timesCorrect += 1
        } else {
            record.timesIncorrect += 1
        }
        record.lastResult = isCorrect
        record.selectedIndex = selectedIndex
        record.lastSeenAt = Date()
        questionRecords[item] = record

        registerDailyActivity()
        scheduleSave()
    }

    func toggleFlag(item: String) {
        var record = record(for: item)
        record.flagged.toggle()
        questionRecords[item] = record
        scheduleSave()
    }

    func isFlagged(item: String) -> Bool {
        questionRecords[item]?.flagged ?? false
    }

    func accuracy(forItem item: String) -> Double {
        record(for: item).accuracy
    }

    // MARK: - Streak & daily goal

    /// Rolls the daily counter over and expires a stale streak on launch.
    private func normalizeDailyCounters() {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())

        if let dailyDate = dailyCompletedDate, !calendar.isDate(dailyDate, inSameDayAs: today) {
            dailyCompleted = 0
            dailyCompletedDate = today
        }

        if let lastActivity = lastActivityDate {
            let lastDay = calendar.startOfDay(for: lastActivity)
            if let gap = calendar.dateComponents([.day], from: lastDay, to: today).day, gap > 1 {
                currentStreak = 0
            }
        }
    }

    private func registerDailyActivity() {
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())

        if let dailyDate = dailyCompletedDate, !calendar.isDate(dailyDate, inSameDayAs: today) {
            dailyCompleted = 0
        }
        dailyCompletedDate = today

        guard let lastActivity = lastActivityDate else {
            currentStreak = 1
            lastActivityDate = today
            return
        }

        let lastDay = calendar.startOfDay(for: lastActivity)
        if calendar.isDate(lastDay, inSameDayAs: today) { return }

        let gap = calendar.dateComponents([.day], from: lastDay, to: today).day ?? 0
        currentStreak = gap == 1 ? currentStreak + 1 : 1
        lastActivityDate = today
    }

    func incrementDailyCompleted() {
        dailyCompleted += 1
        dailyCompletedDate = Calendar.current.startOfDay(for: Date())
        scheduleSave()
    }

    // MARK: - Category aggregates

    func progress(for category: QuizCategory) -> SubcategoryProgress {
        aggregate(items: category.questions.map(\.item))
    }

    func progress(for subcategory: TheorySubcategory) -> SubcategoryProgress {
        progress(for: .standard(subcategory))
    }

    private func aggregate(items: [String]) -> SubcategoryProgress {
        var answered = 0
        var correct = 0
        var incorrect = 0
        var flagged = 0
        var attempts = 0
        var correctAttempts = 0

        for item in items {
            guard let record = questionRecords[item] else { continue }
            if record.flagged { flagged += 1 }
            attempts += record.attempts
            correctAttempts += record.timesCorrect
            guard record.answered else { continue }
            answered += 1
            if record.answeredCorrectly {
                correct += 1
            } else {
                incorrect += 1
            }
        }

        return SubcategoryProgress(
            answeredCount: answered,
            correctCount: correct,
            incorrectCount: incorrect,
            flaggedCount: flagged,
            attemptCount: attempts,
            totalCorrectAttempts: correctAttempts
        )
    }

    /// Accuracy over all attempts in a category, not just latest results.
    func accuracy(for category: QuizCategory) -> Double {
        let stats = progress(for: category)
        guard stats.attemptCount > 0 else { return 0 }
        return Double(stats.totalCorrectAttempts) / Double(stats.attemptCount)
    }

    func accuracy(for subcategory: TheorySubcategory) -> Double {
        accuracy(for: .standard(subcategory))
    }

    /// Blend of how much of the category has been seen and how well it's
    /// answered, used for the weakest-first ordering in the UI.
    func masteryScore(for category: QuizCategory) -> Double {
        let total = category.questionCount
        guard total > 0 else { return 0 }
        let stats = progress(for: category)
        let coverage = Double(stats.answeredCount) / Double(total)
        return min(1, coverage * 0.45 + accuracy(for: category) * 0.55)
    }

    func masteryScore(for subcategory: TheorySubcategory) -> Double {
        masteryScore(for: .standard(subcategory))
    }

    func isComplete(_ category: QuizCategory) -> Bool {
        let total = category.questionCount
        guard total > 0 else { return false }
        return progress(for: category).answeredCount >= total
    }

    // MARK: - Review queues

    func flaggedQuestions(for subcategory: TheorySubcategory? = nil) -> [Question] {
        let all = TheoryQuestionBank.allQuestions.filter { isFlagged(item: $0.item) }
        guard let subcategory else { return all }
        return all.filter { $0.subcategory == subcategory }
    }

    func incorrectQuestions(for subcategory: TheorySubcategory? = nil) -> [Question] {
        let all = TheoryQuestionBank.allQuestions.filter {
            let record = questionRecords[$0.item]
            return record?.answered == true && record?.answeredCorrectly == false
        }
        guard let subcategory else { return all }
        return all.filter { $0.subcategory == subcategory }
    }

    func incorrectItems(for category: QuizCategory) -> [String] {
        category.questions.map(\.item).filter {
            let record = questionRecords[$0]
            return record?.answered == true && record?.answeredCorrectly == false
        }
    }

    // MARK: - Session state

    func sessionState(for category: QuizCategory) -> CategorySessionState? {
        sessionStates[category.id]
    }

    /// A resumable session only counts if it was recorded for the same mode —
    /// switching mode intentionally discards it.
    func hasSavedSession(for category: QuizCategory, mode: QuizSelectionMode? = nil) -> Bool {
        guard let state = sessionStates[category.id], state.isResumable else { return false }
        guard let mode else { return true }
        return state.mode == mode
    }

    func saveSession(items: [String], nextIndex: Int, mode: QuizSelectionMode, for category: QuizCategory) {
        sessionStates[category.id] = CategorySessionState(orderedItems: items, nextIndex: nextIndex, mode: mode)
        scheduleSave()
    }

    func clearSession(for category: QuizCategory) {
        sessionStates[category.id] = nil
        scheduleSave()
    }

    // MARK: - Test date

    func daysUntilTest() -> Int {
        let calendar = Calendar.current
        let components = calendar.dateComponents(
            [.day],
            from: calendar.startOfDay(for: Date()),
            to: calendar.startOfDay(for: targetTestDate)
        )
        return max(0, components.day ?? 0)
    }

    func updateTargetTestDate(_ date: Date) {
        targetTestDate = date
        scheduleSave()
    }

    func markOnboardingComplete() {
        // hasCompletedOnboarding = true // Commented out to make onboarding appear every time
        saveNow()
    }

    func markVideoDownloadIntroSeen() {
        hasSeenVideoDownloadIntro = true
        saveNow()
    }

    func markTheoryIntroSeen() {
        hasSeenTheoryIntro = true
        saveNow()
    }

    func markCategoryIntroSeen(_ categoryId: String) {
        seenCategoryIntros.insert(categoryId)
        saveNow()
    }
}
