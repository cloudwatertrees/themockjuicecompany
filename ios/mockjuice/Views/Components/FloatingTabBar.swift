import SwiftUI

nonisolated enum AppTab: Int, CaseIterable, Identifiable, Sendable {
    case home = 0
    case progress

    nonisolated var id: Int { rawValue }

    var icon: String {
        switch self {
        case .home:
            return "house.fill"
        case .progress:
            return "chart.bar.fill"
        }
    }

    var label: String {
        switch self {
        case .home:
            return "home"
        case .progress:
            return "progress"
        }
    }
}

struct FloatingTabBar: View {
    @Binding var selectedTab: AppTab
    var onHomeReselected: () -> Void = {}

    var body: some View {
        HStack(spacing: 10) {
            ForEach(AppTab.allCases) { tab in
                Button {
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                        if tab == .home && selectedTab == .home {
                            onHomeReselected()
                        } else {
                            selectedTab = tab
                        }
                    }
                } label: {
                    VStack(spacing: 5) {
                        Image(systemName: tab.icon)
                            .font(.system(size: 20, weight: .bold))
                            .foregroundStyle(selectedTab == tab ? MJTheme.cardinal : MJTheme.deepForest.opacity(0.45))

                        Text(tab.label)
                            .font(.mjRounded(.caption2, weight: .heavy))
                            .tracking(-0.2)
                            .textCase(.lowercase)
                            .foregroundStyle(selectedTab == tab ? MJTheme.cardinal : MJTheme.deepForest.opacity(0.45))
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .contentShape(Rectangle())
                }
                .buttonStyle(MJPressScaleButtonStyle())
                .sensoryFeedback(.selection, trigger: selectedTab)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background {
            RoundedRectangle(cornerRadius: 28, style: .continuous)
                .fill(MJTheme.spring)
                .shadow(color: MJTheme.deepForest.opacity(0.14), radius: 18, y: 6)
                .overlay {
                    RoundedRectangle(cornerRadius: 28, style: .continuous)
                        .stroke(MJTheme.deepForest.opacity(0.06), lineWidth: 0.5)
                }
        }
        .padding(.horizontal, 16)
    }
}
