import SwiftUI

/// Intro screen for the "flagged questions" hub option. Shows how many
/// questions are currently flagged and starts a fresh-shuffled review of just
/// that set. When nothing is flagged yet it explains how to build the list
/// instead of dropping into an empty quiz.
struct FlaggedQuestionsIntroView: View {
    @Bindable var progress: UserProgress
    let onStart: () -> Void

    private var flaggedCount: Int { progress.flaggedQuestionIDs.count }
    private var hasFlagged: Bool { flaggedCount > 0 }

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("flagged questions")
                        .font(.mjRounded(.largeTitle, weight: .black))
                        .tracking(-0.5)
                        .textCase(.lowercase)
                        .foregroundStyle(MJTheme.deepForest)

                    Text(hasFlagged ? "\(flaggedCount) question\(flaggedCount == 1 ? "" : "s") saved for revisit" : "nothing flagged yet")
                        .font(.mjRounded(.subheadline, weight: .bold))
                        .tracking(-0.2)
                        .foregroundStyle(MJTheme.deepForest.opacity(0.55))
                }

                Spacer()

                ZStack {
                    Circle()
                        .fill(MJTheme.bee.opacity(0.18))
                        .frame(width: 54, height: 54)
                    Image(systemName: "flag.fill")
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(MJTheme.bee)
                }
            }

            VStack(alignment: .leading, spacing: 12) {
                introRow(icon: "hand.tap.fill", title: "tap to flag", detail: "hit the flag icon on any question during practice to save it here")
                introRow(icon: "shuffle", title: "shuffled review", detail: "your flagged set is reshuffled fresh every time you start")
                introRow(icon: "checkmark.seal.fill", title: "unflag anytime", detail: "answer or tap the flag again during review to clear it off the list")
            }

            Button {
                onStart()
            } label: {
                Text(hasFlagged ? "review \(flaggedCount) flagged" : "no questions flagged")
                    .font(.mjRounded(.title3, weight: .black))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.innocentWhite)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 18)
                    .background(
                        RoundedRectangle(cornerRadius: 20, style: .continuous)
                            .fill(hasFlagged ? MJTheme.cardinal : MJTheme.locked)
                    )
                    .shadow(color: hasFlagged ? MJTheme.cardinal.opacity(0.3) : .clear, radius: 12, y: 6)
            }
            .buttonStyle(.plain)
            .disabled(!hasFlagged)
            .sensoryFeedback(.impact(weight: .heavy), trigger: hasFlagged)
        }
        .padding(20)
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(MJTheme.innocentWhite)
                .shadow(color: MJTheme.deepForest.opacity(0.06), radius: 8, y: 4)
        )
    }

    private func introRow(icon: String, title: String, detail: String) -> some View {
        HStack(spacing: 12) {
            ZStack {
                RoundedRectangle(cornerRadius: 12, style: .continuous)
                    .fill(MJTheme.bee.opacity(0.16))
                    .frame(width: 40, height: 40)
                Image(systemName: icon)
                    .font(.system(size: 17, weight: .bold))
                    .foregroundStyle(MJTheme.bee)
            }

            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.mjRounded(.subheadline, weight: .black))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest)
                Text(detail)
                    .font(.mjRounded(.caption, weight: .bold))
                    .tracking(-0.2)
                    .foregroundStyle(MJTheme.deepForest.opacity(0.55))
            }

            Spacer()
        }
    }
}
