import Foundation

nonisolated struct QuestionOption: Identifiable, Sendable, Hashable {
    /// "A" | "B" | "C" | "D" as supplied by the DVSA bank.
    let id: String
    let text: String
    /// Optional image filename living in `mockjuice_images/`. Most options
    /// have none — that is the normal case, not an error state.
    let imageName: String?
}

nonisolated struct Question: Identifiable, Sendable, Hashable {
    /// DVSA item code (e.g. `AB2001`, `vm2016-1`). This is the single key
    /// every progress record is stored against.
    let item: String
    let subcategory: TheorySubcategory
    let text: String
    /// Optional image filename living in `mockjuice_images/`.
    let stemImageName: String?
    let options: [QuestionOption]
    let correctIndex: Int
    let explanation: String
    /// Only the 27 `vm`-prefixed questions carry a video. Groups of 3
    /// questions share one filename (e.g. `vm2016.mp4`) that `VideoDownloadManager`
    /// resolves to a cached local file or a remote URL — clips are fetched
    /// on demand, not bundled with the app.
    let videoFileName: String?

    nonisolated var id: String { item }

    /// Convenience for call sites that only need the answer strings.
    var optionTexts: [String] { options.map(\.text) }

    var isVideoQuestion: Bool { videoFileName != nil }
}

nonisolated enum QuizSelectionMode: String, CaseIterable, Identifiable, Sendable, Codable {
    case freshRandom = "fresh random"
    case weakestFirst = "weakest first"

    nonisolated var id: String { rawValue }
}

/// Every playable grouping in the app: the 14 standard DVSA categories plus
/// the two special-purpose ones. Each is a filtered *view* over the single
/// question bank — none of them own their own copy of the data.
nonisolated enum QuizCategory: Hashable, Identifiable, Sendable, CaseIterable {
    case all
    case videos
    case standard(TheorySubcategory)

    nonisolated static var allCases: [QuizCategory] {
        [.all, .videos] + TheorySubcategory.allCases.map { .standard($0) }
    }

    nonisolated var id: String {
        switch self {
        case .all:
            return "all-categories"
        case .videos:
            return "videos"
        case .standard(let subcategory):
            return subcategory.id
        }
    }

    var title: String {
        switch self {
        case .all:
            return "all categories"
        case .videos:
            return "videos"
        case .standard(let subcategory):
            return subcategory.rawValue
        }
    }

    var iconAsset: String {
        switch self {
        case .all:
            return "four_circles_grid"
        case .videos:
            return "film_reel_sticker"
        case .standard(let subcategory):
            return subcategory.lineArtIconAsset
        }
    }

    /// The questions belonging to this category, resolved live from the bank.
    var questions: [Question] {
        switch self {
        case .all:
            return TheoryQuestionBank.allQuestions
        case .videos:
            return TheoryQuestionBank.videoQuestions
        case .standard(let subcategory):
            return TheoryQuestionBank.questions(for: subcategory)
        }
    }

    var questionCount: Int { questions.count }
}

nonisolated enum QuizSessionKind: Hashable, Identifiable, Sendable {
    case category(QuizCategory, QuizSelectionMode)
    case mockTest
    /// A fresh-shuffled run through every question the learner has flagged.
    case flaggedReview

    nonisolated var id: String {
        switch self {
        case .category(let category, let mode):
            return "category-\(category.id)-\(mode.id)"
        case .mockTest:
            return "mock-test"
        case .flaggedReview:
            return "flagged-review"
        }
    }
}

nonisolated struct SubcategoryProgress: Sendable {
    let answeredCount: Int
    let correctCount: Int
    let incorrectCount: Int
    let flaggedCount: Int
    /// Total individual attempts, which can exceed `answeredCount` because a
    /// question may be answered more than once across sessions.
    let attemptCount: Int
    let totalCorrectAttempts: Int
}

nonisolated struct MockTestBreakdown: Identifiable, Sendable {
    let subcategory: TheorySubcategory
    let total: Int
    let correct: Int

    nonisolated var id: String { subcategory.id }

    var accuracy: Double {
        guard total > 0 else { return 0 }
        return Double(correct) / Double(total)
    }
}
