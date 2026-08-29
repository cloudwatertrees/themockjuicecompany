import Foundation

/// Builds the ordered question sequence for a session.
nonisolated enum QuestionSequencer {
    /// Minimum number of other questions that must be answered before a
    /// question the user has recently seen is allowed to come round again.
    static let minimumSpacing = 8

    /// Orders questions for the requested mode, then enforces spacing.
    ///
    /// - Parameters:
    ///   - questions: the full candidate pool for the category.
    ///   - mode: fresh-random or weakest-first.
    ///   - accuracyForItem: historical accuracy per item code (0 for unseen,
    ///     which intentionally sorts unseen questions to the front).
    ///   - recentlyShown: item codes most recently shown, oldest → newest, so
    ///     spacing carries across sessions and not just within one.
    static func sequence(
        questions: [Question],
        mode: QuizSelectionMode,
        accuracyForItem: (String) -> Double,
        recentlyShown: [String]
    ) -> [Question] {
        let ordered: [Question]

        switch mode {
        case .freshRandom:
            ordered = questions.shuffled()
        case .weakestFirst:
            // Random tie-break so equally-weak questions don't come back in the
            // same order every time.
            ordered = questions
                .map { (question: $0, accuracy: accuracyForItem($0.item), tieBreak: Double.random(in: 0..<1)) }
                .sorted { lhs, rhs in
                    if lhs.accuracy == rhs.accuracy {
                        return lhs.tieBreak < rhs.tieBreak
                    }
                    return lhs.accuracy < rhs.accuracy
                }
                .map(\.question)
        }

        return applySpacing(to: ordered, recentlyShown: recentlyShown)
    }

    /// Walks the ordered list and pulls forward the first candidate that isn't
    /// inside the trailing `minimumSpacing` window. If every remaining
    /// candidate is too recent it takes the next one anyway — the sequence must
    /// never stall or drop questions.
    static func applySpacing(
        to ordered: [Question],
        recentlyShown: [String],
        spacing: Int = minimumSpacing
    ) -> [Question] {
        guard spacing > 0, ordered.count > 1 else { return ordered }

        var window: [String] = Array(recentlyShown.suffix(spacing))
        var remaining = ordered
        var result: [Question] = []
        result.reserveCapacity(ordered.count)

        while !remaining.isEmpty {
            let index = remaining.firstIndex { !window.contains($0.item) } ?? 0
            let question = remaining.remove(at: index)
            result.append(question)

            window.append(question.item)
            if window.count > spacing {
                window.removeFirst(window.count - spacing)
            }
        }

        return result
    }

    /// Picks a 50-question mock test proportionally weighted by how many
    /// questions each category actually contains in the bank.
    static func mockTestQuestions(count: Int = 50) -> [Question] {
        let all = TheoryQuestionBank.allQuestions
        guard all.count > count else { return all.shuffled() }

        let weights = TheorySubcategory.allCases.map { ($0, TheoryQuestionBank.questions(for: $0).count) }
        let totalWeight = weights.reduce(0) { $0 + $1.1 }
        guard totalWeight > 0 else { return Array(all.shuffled().prefix(count)) }

        var picked: [Question] = []
        var usedItems: Set<String> = []

        for (subcategory, weight) in weights {
            let share = (Double(weight) / Double(totalWeight)) * Double(count)
            let take = max(1, Int(share.rounded(.down)))
            for question in TheoryQuestionBank.questions(for: subcategory).shuffled().prefix(take)
            where !usedItems.contains(question.item) {
                picked.append(question)
                usedItems.insert(question.item)
            }
        }

        // Rounding down leaves a shortfall; top up at random from the bank.
        if picked.count < count {
            for question in all.shuffled() where !usedItems.contains(question.item) {
                picked.append(question)
                usedItems.insert(question.item)
                if picked.count == count { break }
            }
        }

        return Array(picked.prefix(count)).shuffled()
    }
}
