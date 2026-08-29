import Foundation

/// The single source of truth for all question content, decoded once from the
/// bundled `questions.json`. There is deliberately no placeholder/sample data
/// here and no in-code fallback bank — if the JSON is missing the app has a
/// real problem that should be visible, not silently papered over.
nonisolated enum TheoryQuestionBank {
    /// Raw shape of one entry in `questions.json`.
    private struct RawQuestion: Decodable {
        struct RawOption: Decodable {
            let id: String
            let text: String
            let image: String?
        }

        let item: String
        let topic: String
        let stem: String
        let stem_image: String?
        let options: [RawOption]
        let correct_answer: String
        let explanation: String
        /// A bundled filename (e.g. `vm2016.mp4`) for the 27 video questions, not
        /// a remote URL — every clip ships inside the app.
        let video: String?
    }

    /// All 784 questions, in the order supplied by the bank.
    static let allQuestions: [Question] = loadQuestions()

    /// Fast lookup by DVSA item code, used when replaying a persisted session
    /// sequence back into real question objects.
    static let questionsByItem: [String: Question] = Dictionary(
        allQuestions.map { ($0.item, $0) },
        uniquingKeysWith: { first, _ in first }
    )

    private static let questionsBySubcategory: [TheorySubcategory: [Question]] =
        Dictionary(grouping: allQuestions, by: \.subcategory)

    /// Exactly the 27 `vm`-prefixed video questions.
    static let videoQuestions: [Question] = allQuestions.filter { $0.isVideoQuestion }

    static func questions(for subcategory: TheorySubcategory) -> [Question] {
        questionsBySubcategory[subcategory] ?? []
    }

    static func question(item: String) -> Question? {
        questionsByItem[item]
    }

    private static func loadQuestions() -> [Question] {
        guard let url = Bundle.main.url(forResource: "questions", withExtension: "json") else {
            NSLog("[TheoryQuestionBank] questions.json missing from app bundle — question bank is empty")
            return []
        }

        do {
            let data = try Data(contentsOf: url)
            let raw = try JSONDecoder().decode([RawQuestion].self, from: data)
            let mapped = raw.compactMap(map(raw:))
            if mapped.count != raw.count {
                NSLog("[TheoryQuestionBank] decoded \(raw.count) entries but mapped only \(mapped.count)")
            }
            return mapped
        } catch {
            NSLog("[TheoryQuestionBank] failed to decode questions.json: \(error.localizedDescription)")
            return []
        }
    }

    private static func map(raw: RawQuestion) -> Question? {
        guard let subcategory = TheorySubcategory(topicName: raw.topic) else {
            NSLog("[TheoryQuestionBank] unmapped topic '\(raw.topic)' on item \(raw.item)")
            return nil
        }

        let options = raw.options.map {
            QuestionOption(id: $0.id, text: $0.text, imageName: normalized($0.image))
        }

        guard let correctIndex = options.firstIndex(where: { $0.id == raw.correct_answer }) else {
            NSLog("[TheoryQuestionBank] correct answer '\(raw.correct_answer)' not found on item \(raw.item)")
            return nil
        }

        return Question(
            item: raw.item,
            subcategory: subcategory,
            text: raw.stem,
            stemImageName: normalized(raw.stem_image),
            options: options,
            correctIndex: correctIndex,
            explanation: raw.explanation,
            videoFileName: normalized(raw.video)
        )
    }

    /// Treats empty/whitespace-only strings the same as `null`, so a blank
    /// image field never becomes a doomed bundle lookup.
    private static func normalized(_ value: String?) -> String? {
        guard let trimmed = value?.trimmingCharacters(in: .whitespacesAndNewlines), !trimmed.isEmpty else {
            return nil
        }
        return trimmed
    }
}
