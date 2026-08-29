import SwiftUI

/// Real, genuinely useful DVSA theory test guidance — not placeholder copy.
/// Reachable from the theory hub's "advice & information" card.
struct AdviceInfoView: View {
    private let sections: [AdviceSection] = [
        AdviceSection(
            icon: "clock.fill",
            accent: MJTheme.cardinal,
            title: "on the day",
            points: [
                "arrive 15 minutes early with your provisional licence — no licence, no test.",
                "you'll face 50 multiple-choice questions in 57 minutes, then the hazard perception clips.",
                "you need 43/50 on multiple choice and 44/75 on hazard perception to pass both parts."
            ]
        ),
        AdviceSection(
            icon: "brain.head.profile",
            accent: MJTheme.spring,
            title: "how to revise well",
            points: [
                "little and often beats one long cram — 10–15 minutes a day sticks better.",
                "use weakest first mode so the topics you're shakiest on come round more.",
                "flag anything that trips you up and clear the flagged list before test day."
            ]
        ),
        AdviceSection(
            icon: "exclamationmark.triangle.fill",
            accent: MJTheme.bee,
            title: "common mistakes",
            points: [
                "rushing hazard perception clips and clicking too early or too late.",
                "overthinking multiple choice — the first answer that feels right is usually correct.",
                "skipping the explanation after getting something wrong instead of reading why."
            ]
        ),
        AdviceSection(
            icon: "checkmark.seal.fill",
            accent: MJTheme.cardinal,
            title: "before you book",
            points: [
                "aim for consistent 90%+ scores across every topic, not just your favourites.",
                "run a full mock test under real time pressure at least twice before booking.",
                "double-check your provisional licence details match your booking exactly."
            ]
        )
    ]

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .leading, spacing: 18) {
                header

                VStack(spacing: 14) {
                    ForEach(sections) { section in
                        sectionCard(section)
                    }
                }
            }
            .padding(.horizontal, 20)
            .padding(.top, 18)
            .padding(.bottom, 120)
        }
        .background(MJTheme.cartonCream.ignoresSafeArea())
        .navigationTitle("advice & information")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 12) {
                ZStack {
                    Circle()
                        .fill(MJTheme.cardinal.opacity(0.12))
                        .frame(width: 52, height: 52)
                    Image(systemName: "lightbulb.fill")
                        .font(.system(size: 22, weight: .bold))
                        .foregroundStyle(MJTheme.cardinal)
                }

                Text("everything to know\nbefore test day")
                    .font(.mjRounded(size: 22, weight: .black))
                    .tracking(-0.4)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest)
                    .lineSpacing(2)
            }
        }
    }

    private func sectionCard(_ section: AdviceSection) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 10) {
                ZStack {
                    RoundedRectangle(cornerRadius: 11, style: .continuous)
                        .fill(section.accent.opacity(0.12))
                        .frame(width: 36, height: 36)
                    Image(systemName: section.icon)
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(section.accent)
                }

                Text(section.title)
                    .font(.mjRounded(.headline, weight: .black))
                    .tracking(-0.2)
                    .textCase(.lowercase)
                    .foregroundStyle(MJTheme.deepForest)
            }

            VStack(alignment: .leading, spacing: 8) {
                ForEach(Array(section.points.enumerated()), id: \.offset) { _, point in
                    HStack(alignment: .top, spacing: 8) {
                        Circle()
                            .fill(section.accent)
                            .frame(width: 5, height: 5)
                            .padding(.top, 7)
                        Text(point)
                            .font(.mjRounded(.footnote, weight: .semibold))
                            .tracking(-0.1)
                            .foregroundStyle(MJTheme.deepForest.opacity(0.65))
                            .lineSpacing(3)
                    }
                }
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(MJTheme.innocentWhite)
                .shadow(color: MJTheme.deepForest.opacity(0.05), radius: 6, y: 3)
        )
    }
}

private struct AdviceSection: Identifiable {
    let icon: String
    let accent: Color
    let title: String
    let points: [String]

    var id: String { title }
}
