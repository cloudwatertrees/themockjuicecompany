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
        .padding(.top, 12)
        .padding(.bottom, 4) // Add a tiny bit of extra breathing room above the safe area
        .background(
            MJTheme.cartonCream
                .overlay(alignment: .top) {
                    Rectangle()
                        .fill(MJTheme.deepForest.opacity(0.1))
                        .frame(height: 1)
                }
                .ignoresSafeArea(edges: .bottom)
        )
    }
}
