import Foundation

/// The one and only progress record, stored per question item code. Every
/// category view — including "all categories" and "videos" — aggregates these
/// on read, so there are no per-category counters to keep in sync and nothing
/// that can drift.
nonisolated struct QuestionRecord: Codable, Sendable, Hashable {
    var timesShown: Int = 0
    var timesCorrect: Int = 0
    var timesIncorrect: Int = 0
    /// Result of the most recent attempt; `nil` until first answered.
    var lastResult: Bool? = nil
    var lastSeenAt: Date? = nil
    var flagged: Bool = false
    /// Option index chosen on the most recent attempt, for review screens.
    var selectedIndex: Int? = nil

    /// Total attempts across all sessions.
    var attempts: Int { timesCorrect + timesIncorrect }

    var answered: Bool { attempts > 0 }

    /// Whether the *latest* attempt was correct.
    var answeredCorrectly: Bool { lastResult == true }

    /// Historical accuracy for this question. Never-attempted questions
    /// report 0, which deliberately sorts them to the front of Weakest First.
    var accuracy: Double {
        guard attempts > 0 else { return 0 }
        return Double(timesCorrect) / Double(attempts)
    }
}

/// Persisted session for a category. Keyed by category id; the mode is stored
/// inside so switching mode is detected and forces a fresh sequence.
nonisolated struct CategorySessionState: Codable, Sendable, Hashable {
    var orderedItems: [String] = []
    var nextIndex: Int = 0
    var mode: QuizSelectionMode = .freshRandom

    var isResumable: Bool {
        nextIndex > 0 && nextIndex < orderedItems.count
    }
}

/// Everything that must survive an app relaunch, in one Codable blob.
nonisolated struct ProgressSnapshot: Codable, Sendable {
    var questionRecords: [String: QuestionRecord] = [:]
    var sessionStates: [String: CategorySessionState] = [:]
    /// Rolling list of the most recently shown item codes, used to enforce the
    /// minimum-spacing rule across sessions as well as within one.
    var recentlyShownItems: [String] = []
    var completedNodes: [String] = []
    var nodeScores: [String: Int] = [:]
    var currentStreak: Int = 0
    /// Day of the last recorded answer, used to advance or reset the streak.
    var lastActivityDate: Date? = nil
    var dailyGoal: Int = 5
    var dailyCompleted: Int = 0
    /// Day `dailyCompleted` refers to, so the daily counter self-resets.
    var dailyCompletedDate: Date? = nil
    var hasCompletedOnboarding: Bool = false
    var mockTestHistory: [Int] = []
    var targetTestDate: Date? = nil
    /// Whether the learner has already seen the one-time "let's grab your
    /// hazard clips" download screen. Shown once, the first time any of the
    /// 16 theory topics is tapped.
    var hasSeenVideoDownloadIntro: Bool = false
    /// Whether the learner has seen the one-time theory category intro.
    var hasSeenTheoryIntro: Bool = false
    /// Which specific category info modals have been seen and dismissed.
    var seenCategoryIntros: [String] = []
}
