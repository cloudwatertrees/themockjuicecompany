import SwiftUI

/// Loads a bundled question image and hands it to the caller's layout.
///
/// Both the stem and answer-option variants below are thin wrappers around this,
/// so there is one loading path rather than two that can drift apart.
private struct BundledImageLoader<Content: View>: View {
    let fileName: String
    let maxPixelSize: Int
    let placeholderHeight: CGFloat
    @ViewBuilder let content: (UIImage) -> Content

    private enum LoadState {
        case loading
        case loaded(UIImage)
        case failed
    }

    @State private var state: LoadState = .loading

    var body: some View {
        // Every branch renders a real view, never an empty one. This matters:
        // a lifecycle modifier attached to a view that resolves to nothing never
        // fires, so an "empty until loaded" body would deadlock — nothing renders,
        // so the load never starts, so nothing ever renders.
        Group {
            switch state {
            case .loading:
                RoundedRectangle(cornerRadius: 16, style: .continuous)
                    .fill(MJTheme.deepForest.opacity(0.05))
                    .frame(height: placeholderHeight)
            case .loaded(let image):
                content(image)
            case .failed:
                // Nothing to show, but keep a zero-size view in the tree so the
                // task stays attached and can react to a later filename change.
                Color.clear.frame(width: 0, height: 0)
            }
        }
        .task(id: fileName) {
            if let cached = BundledImageResolver.cachedImage(named: fileName, maxPixelSize: maxPixelSize) {
                state = .loaded(cached)
                return
            }

            // Reset before loading: these views are recycled between questions
            // (options are identified by index), so keeping the old image would
            // briefly show the previous question's picture.
            state = .loading
            let loaded = await BundledImageResolver.loadImage(named: fileName, maxPixelSize: maxPixelSize)
            guard !Task.isCancelled else { return }
            state = loaded.map(LoadState.loaded) ?? .failed
        }
    }
}

/// Renders a question's bundled diagram/sign image above the answers.
///
/// A missing file degrades to nothing at all rather than a placeholder — the
/// question text always stands on its own, and most questions legitimately have
/// no image.
struct QuestionImageView: View {
    let fileName: String
    var maxHeight: CGFloat = 220

    var body: some View {
        BundledImageLoader(fileName: fileName, maxPixelSize: 1200, placeholderHeight: 140) { image in
            Image(uiImage: image)
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(maxWidth: .infinity)
                .frame(maxHeight: maxHeight)
                .clipShape(.rect(cornerRadius: 16))
                .accessibilityHidden(true)
        }
    }
}

/// Compact variant used inside answer option rows, where the image *is* the
/// answer (e.g. "which of these signs means...").
struct QuestionOptionImageView: View {
    let fileName: String
    var side: CGFloat = 66

    var body: some View {
        BundledImageLoader(fileName: fileName, maxPixelSize: 300, placeholderHeight: side) { image in
            Image(uiImage: image)
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(width: side, height: side)
                .accessibilityHidden(true)
        }
    }
}
