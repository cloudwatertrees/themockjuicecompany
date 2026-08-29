import SwiftUI

/// Settings, tucked behind the gear icon on the home screen.
struct SettingsView: View {
    @Bindable var progress: UserProgress
    @Environment(\.dismiss) private var dismiss

    @State private var showResetConfirmation: Bool = false
    @State private var didReset: Bool = false

    var body: some View {
        NavigationStack {
            ScrollView(.vertical, showsIndicators: false) {
                VStack(alignment: .leading, spacing: 14) {
                    settingsRow(icon: "calendar", label: "test countdown", value: "\(progress.daysUntilTest()) days", color: MJTheme.cardinal)
                    settingsRow(icon: "bell.fill", label: "notifications", value: "on", color: MJTheme.bee)
                    settingsRow(icon: "paintbrush.fill", label: "appearance", value: "light", color: MJTheme.cardinal)
                    settingsRow(icon: "questionmark.circle.fill", label: "help & support", value: "faq", color: MJTheme.spring)

                    resetSection
                        .padding(.top, 10)
                }
                .padding(.horizontal, 20)
                .padding(.top, 12)
                .padding(.bottom, 40)
            }
            .background(MJTheme.cartonCream.ignoresSafeArea())
            .navigationTitle("settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("done") {
                        dismiss()
                    }
                    .font(.mjRounded(.body, weight: .black))
                    .foregroundStyle(MJTheme.cardinal)
                }
            }
            .confirmationDialog(
                "reset all progress?",
                isPresented: $showResetConfirmation,
                titleVisibility: .visible
            ) {
                Button("reset everything", role: .destructive) {
                    progress.resetAll()
                    withAnimation(.easeOut(duration: 0.3)) {
                        didReset = true
                    }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                        withAnimation(.easeOut(duration: 0.3)) {
                            didReset = false
                        }
                    }
                }
                Button("cancel", role: .cancel) {}
            } message: {
                Text("this wipes every question record, streak, mock-test score, and downloaded hazard clip. it can't be undone.")
            }
        }
    }

    // MARK: - Rows

    private func settingsRow(icon: String, label: String, value: String, color: Color) -> some View {
        HStack(spacing: 14) {
            ZStack {
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(color.opacity(0.12))
                    .frame(width: 36, height: 36)
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(color)
            }

            Text(label)
                .font(.mjRounded(.body, weight: .bold))
                .tracking(-0.2)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest)

            Spacer()

            Text(value)
                .font(.mjRounded(.caption, weight: .black))
                .foregroundStyle(MJTheme.deepForest.opacity(0.4))
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(MJTheme.innocentWhite)
                .shadow(color: MJTheme.deepForest.opacity(0.05), radius: 4, y: 2)
        )
    }

    // MARK: - Reset section

    private var resetSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("danger zone")
                .font(.mjRounded(.caption, weight: .black))
                .tracking(-0.1)
                .textCase(.lowercase)
                .foregroundStyle(MJTheme.deepForest.opacity(0.4))
                .padding(.leading, 4)

            Button {
                showResetConfirmation = true
            } label: {
                HStack(spacing: 14) {
                    ZStack {
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .fill(MJTheme.cardinal.opacity(0.12))
                            .frame(width: 36, height: 36)
                        Image(systemName: didReset ? "checkmark.circle.fill" : "trash.fill")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundStyle(didReset ? MJTheme.spring : MJTheme.cardinal)
                    }

                    VStack(alignment: .leading, spacing: 2) {
                        Text(didReset ? "all progress cleared" : "reset all data")
                            .font(.mjRounded(.body, weight: .bold))
                            .tracking(-0.2)
                            .textCase(.lowercase)
                            .foregroundStyle(didReset ? MJTheme.spring : MJTheme.cardinal)

                        if !didReset {
                            Text("wipe progress, streaks & clips")
                                .font(.mjRounded(.caption2, weight: .bold))
                                .tracking(-0.1)
                                .textCase(.lowercase)
                                .foregroundStyle(MJTheme.deepForest.opacity(0.4))
                        }
                    }

                    Spacer()

                    if !didReset {
                        Image(systemName: "chevron.right")
                            .font(.system(size: 13, weight: .bold))
                            .foregroundStyle(MJTheme.deepForest.opacity(0.3))
                    }
                }
                .padding(14)
                .background(
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .fill(MJTheme.innocentWhite)
                        .shadow(color: MJTheme.deepForest.opacity(0.05), radius: 4, y: 2)
                )
            }
            .buttonStyle(MJPressScaleButtonStyle())
            .disabled(didReset)
        }
    }
}
