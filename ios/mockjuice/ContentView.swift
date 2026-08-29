import SwiftUI

struct ContentView: View {
    @State private var progress = UserProgress()
    @State private var selectedTab: AppTab = .home
    @State private var homeResetTrigger: Int = 0
    @State private var showOnboarding: Bool = true // Always show onboarding initially

    var body: some View {
        ZStack(alignment: .bottom) {
            Group {
                switch selectedTab {
                case .home:
                    JourneyPathView(progress: progress, homeResetTrigger: homeResetTrigger)
                case .progress:
                    ProgressTabView(progress: progress)
                }
            }

            FloatingTabBar(selectedTab: $selectedTab) {
                homeResetTrigger += 1
            }
            .padding(.bottom, 8)

            if showOnboarding {
                OnboardingView {
                    withAnimation(.easeOut(duration: 0.3)) {
                        showOnboarding = false
                    }
                }
                .zIndex(100)
                .transition(.move(edge: .bottom))
            }
        }
        .ignoresSafeArea(.keyboard)
    }
}
